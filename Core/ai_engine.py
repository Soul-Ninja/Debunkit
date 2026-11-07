import json
import urllib.request
import urllib.error
import datetime
import logging
import re
from urllib.parse import urlparse

from config import config
from .rag_engine import get_live_context
from .nlp_engine import local_analyze

logger = logging.getLogger(__name__)

VALID_VERDICTS = {"SUPPORTED", "REFUTED", "INSUFFICIENT EVIDENCE", "MISLEADING", "LOW CREDIBILITY"}
VERDICT_ALIASES = {
    "REAL": "SUPPORTED", "TRUE": "SUPPORTED", "CONFIRMED": "SUPPORTED",
    "FAKE": "REFUTED", "FALSE": "REFUTED", "DEBUNKED": "REFUTED",
    "UNCERTAIN": "INSUFFICIENT EVIDENCE", "UNKNOWN": "INSUFFICIENT EVIDENCE",
    "UNVERIFIED": "INSUFFICIENT EVIDENCE", "SUSPICIOUS": "LOW CREDIBILITY"
}

CREDIBLE_NEWS_SOURCES = [
    "reuters", "associated press", "ap news", "bbc", "cnn", "nyt", "times",
    "guardian", "washington post", "fox news", "nbcnews", "abcnews", "espn",
    "bbc sport", "ndtv", "times of india", "hindu", "deccan", "scroll",
    "theprint", "news18", "india today", "aaj tak", "the hindu", "hindustan times",
    "indian express", "cricbuzz", "espncricinfo"
]

CREDIBLE_SOURCE_DOMAINS = [
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "thehindu.com",
    "hindustantimes.com", "indianexpress.com", "indiatoday.in", "ndtv.com",
    "timesofindia.indiatimes.com", "news18.com", "theprint.in", "scroll.in",
    "deccanherald.com", "espncricinfo.com", "espn.com", "cricbuzz.com"
]

CREDIBLE_INSTITUTIONS = [
    "stanford", "harvard", "mit", "yale", "berkeley", "oxford", "cambridge",
    "google", "microsoft", "apple", "nasa", "fed", "world bank", "un", "iit",
    "delhi university", "mumbai university"
]

SPORTS_KEYWORDS = [
    "cricket", "match", "game", "score", "won", "lost", "defeated", "beat",
    "ipl", "world cup", "t20", "test", "odi", "tournament", "championship",
    "football", "baseball", "basketball", "tennis", "hockey", "rugby",
    "player", "coach", "fielding", "batting", "bowling"
]

HIGH_RISK_TERMS = [
    "death", "dead", "died", "murder", "arrest", "arrested", "jailed",
    "resigned", "resignation", "election", "minister", "president",
    "prime minister", "stock", "share price", "bankruptcy", "fraud",
    "war", "attack", "terror", "disease", "virus", "vaccine", "cure",
    "medicine", "treatment", "miracle cure", "hantavirus"
]

def normalize_verdict(verdict):
    """Convert old/simple model labels into professional fact-check labels."""
    if not verdict:
        return "INSUFFICIENT EVIDENCE"
    v = VERDICT_ALIASES.get(str(verdict).strip().upper(), str(verdict).strip().upper())
    return v if v in VALID_VERDICTS else "INSUFFICIENT EVIDENCE"

def clamp_confidence(value, default=50):
    """Keep confidence inside a safe 0-100 integer range."""
    try:
        return max(0, min(int(float(value)), 100))
    except (TypeError, ValueError):
        return default

def extract_domain(url):
    """Extract hostname from a URL."""
    try:
        return (urlparse(url).hostname or "").lower() if url else ""
    except Exception:
        return ""

def is_credible_source_url(url):
    """Check whether a submitted URL belongs to a known credible source domain."""
    d = extract_domain(url)
    return any(d == td or d.endswith("." + td) for td in CREDIBLE_SOURCE_DOMAINS) if d else False

def is_credible_source_block(block):
    """Quick credibility check based on source names/domains."""
    b = block.lower()
    return any(t in b for t in CREDIBLE_NEWS_SOURCES + CREDIBLE_INSTITUTIONS + CREDIBLE_SOURCE_DOMAINS)

def has_high_risk_terms(text):
    """Check if text contains high-risk terms."""
    t = text.lower()
    return any(term in t for term in HIGH_RISK_TERMS)

def has_causal_claim(text):
    """Check if text contains cause/reason wording."""
    t = text.lower()
    patterns = ["because", "due to", "as a result of", "caused by", "dropped because",
                "removed because", "fired because", "banned because", "rejected because"]
    return any(p in t for p in patterns)

def merge_sources(submitted_url, source_links):
    """Add submitted URL and merge live-search sources without duplicates."""
    merged, seen = [], set()
    if submitted_url:
        merged.append({"title": "Submitted article", "url": submitted_url})
        seen.add(submitted_url)
    for src in (source_links or []):
        url = src.get("url")
        if url and url not in seen:
            merged.append({"title": src.get("title", "Source"), "url": url})
            seen.add(url)
    return merged[:8]

def extract_key_claims(text):
    """Extract main claim signals/entities from text for source matching."""
    action_terms = re.findall(
        r"\b(won|lost|defeated|beat|announced|released|confirmed|achieved|reached|"
        r"resigned|died|dead|arrested|jailed|fired|removed|appointed|selected|"
        r"elected|banned|launched|introduced|approved|rejected|cancelled|canceled|"
        r"keynote|speaker|deliver|delivered|claims|said|reports|reported|"
        r"swats|doubts|backs|supports|criticises|criticizes|questions|"
        r"dropped|removed|misrepresented|miscaptioned|predicted|warned)\b", text, re.I)
    return {
        "names": re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text),
        "dates": re.findall(r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}?,?\s+\d{4}\b", text, re.I),
        "years": re.findall(r"\b20\d{2}\b", text),
        "numbers": re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", text),
        "key_phrases": list(dict.fromkeys(t.lower() for t in action_terms))
    }

def _extract_source_blocks(live_context):
    """Extract individual source blocks from the context string."""
    pat = re.compile(r"\n\d+\.\s\[(.*?)\]\n\s*URL:\s*(.*?)\n\s*Snippet:\s*(.*?)(?=\n\d+\.|\Z)", re.S | re.I)
    return [m.group(0).lower() for m in pat.finditer(live_context)]

def check_source_confirmation(live_context, claims, text):
    """Conservative source check returning (verdict_type, score)."""
    blocks = _extract_source_blocks(live_context)
    if not blocks:
        return "insufficient", 0

    matched, refuting, score = 0, 0, 0
    names = [n.lower() for n in claims.get("names", [])[:3]]
    phrases = [p.lower() for p in claims.get("key_phrases", [])]
    dates = [d.lower() for d in claims.get("dates", [])[:2]]
    years = claims.get("years", [])[:2]
    numbers = claims.get("numbers", [])[:2]

    refutation_patterns = [
        r"\bdenied\b", r"\brefuted\b", r"\bdebunked\b", r"\bfalse\b", r"\bincorrect\b",
        r"\bwrong\b", r"\bno evidence\b", r"\bnot true\b", r"\bdid not\b", r"\bdoes not\b",
        r"\bhas not\b", r"\bno confirmation\b", r"\bmisleading\b", r"\bmisrepresented\b",
        r"\bmiscaptioned\b", r"\bold video\b", r"\bold footage\b"
    ]

    for b in blocks:
        has_name = any(n in b for n in names) if names else False
        has_phrase = any(p in b for p in phrases) if phrases else False
        detail_hits = sum([any(d in b for d in dates), any(y in b for y in years), any(num in b for num in numbers)])
        is_credible = is_credible_source_block(b)
        refutes = any(re.search(pat, b) for pat in refutation_patterns)

        if refutes and (has_name or has_phrase or detail_hits):
            refuting += 1
            score += 5 if is_credible else 4
            continue
        if has_name and has_phrase:
            matched += 1
            score += 3 + (1 if detail_hits else 0) + (1 if is_credible else 0)

    if refuting >= 1:
        return "refuted", score
    if matched >= 2 or (matched == 1 and score >= 5 and len(blocks) <= 2):
        return "supported", score
    return "insufficient", score

def detect_factcheck_override(live_context, claim_text):
    """Detect when a fact-check source clearly corrects or refutes the claim."""
    blocks = _extract_source_blocks(live_context)
    if not blocks:
        return None

    terms = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", claim_text.lower())
             if w.lower() not in {"the", "and", "for", "with", "from", "that", "this", "were", "was", "are", "has", "have"}]
    fc_markers = ["fact check", "fact-check", "reuters.com/fact-check", "snopes", "politifact", "full fact", "afp fact check", "boomlive", "alt news", "logically facts"]
    mis_markers = ["misleading", "missing context", "miscaptioned", "misrepresented", "old video", "old footage", "old image", "not from", "not in uk", "taken out of context"]
    ref_markers = ["false", "did not", "does not", "not true", "no evidence", "fabricated", "fake", "altered", "ai-generated", "contrary to", "no record"]

    for b in blocks:
        if not any(m in b for m in fc_markers):
            continue
        if sum(1 for t in terms if t in b) < 2:
            continue
        if any(m in b for m in ref_markers):
            return {
                "verdict": "REFUTED", "confidence": 85,
                "reason": "A fact-check source directly contradicts the central claim.",
                "fact_check": "A fact-check result contains refuting language such as 'did not', 'false', or 'no evidence'.",
                "red_flags": ["Fact-check source contradicts the claim"]
            }
        if any(m in b for m in mis_markers):
            return {
                "verdict": "MISLEADING", "confidence": 82,
                "reason": "A fact-check source says the claim is missing context or misrepresents the situation.",
                "fact_check": "A fact-check result indicates that the claim uses old, miscaptioned, or incomplete context.",
                "red_flags": ["Fact-check source reports missing context"]
            }
    return None

def detect_claim_type(text):
    """Detect claim category."""
    t = text.lower()
    if any(k in t for k in SPORTS_KEYWORDS):
        return "sports"
    if re.search(r"\b(?:cure|treatment|disease|virus|vaccine|health|medicine|hantavirus)\b", t):
        return "health"
    if re.search(r"\b(?:election|government|president|minister|parliament|politician)\b", t):
        return "political"
    return "general"

def _build_instructions(claim_type, input_type, source_url, submitted_url_is_credible, high_risk_claim, confirmation_status, confirmation_score):
    """Assemble domain, URL, and source status prompt rules."""
    domains = {
        "sports": "SPORTS: Credible sports outlets are reliable for routine reporting. Player names + team context = meaningful evidence. Causal claims need direct proof for reason.",
        "health": "HEALTH: Require medical/scientific sources (WHO, CDC, peer-reviewed). Prioritize fact-check corrections.",
        "political": "POLITICAL: Major outlets and official statements are required for election, arrest, law claims.",
        "general": "GENERAL: Credible news sources reliable for routine reporting. Extraordinary claims need stronger evidence."
    }
    url_rule = (
        f"URL MODE: Submitted URL {source_url} (Credible: {submitted_url_is_credible}, High-risk: {high_risk_claim}). "
        "Treat submitted text as PRIMARY EVIDENCE. If credible and routine, SUPPORTED is acceptable without snippet repetition."
        if (input_type == "url" and source_url) else
        "TEXT/HEADLINE MODE: Submitted plain text. Use live web search as main evidence. Topic overlap alone is not enough."
    )
    src_rule = (
        f"SOURCE STATUS: Supporting evidence score {confirmation_score}. SUPPORTED valid if central action matches."
        if confirmation_status == "supported" else
        f"SOURCE STATUS: Refuting evidence score {confirmation_score}. If sources deny or add context, choose REFUTED or MISLEADING."
        if confirmation_status == "refuted" else
        "SOURCE STATUS: Live snippets unclear. For text mode, prefer INSUFFICIENT EVIDENCE."
    )
    return domains.get(claim_type, domains["general"]), url_rule, src_rule

def ai_analyze(text, input_type="text", source_url=None, source_text=None, retry_count=0, max_retries=2):
    """Analyze claim using Cohere AI API with source-aware evaluation."""
    if not config.COHERE_API_KEY or config.COHERE_API_KEY.startswith("YOUR_"):
        return None

    try:
        live_context, source_links = get_live_context(text)
    except Exception as e:
        logger.error(f"Failed to get live context: {e}")
        return None

    claims = extract_key_claims(text)
    confirmation_status, confirmation_score = check_source_confirmation(live_context, claims, text)
    factcheck_override = detect_factcheck_override(live_context, text)
    claim_type = detect_claim_type(text)
    submitted_url_is_credible = is_credible_source_url(source_url)
    high_risk_claim = has_high_risk_terms(text)
    causal_claim = has_causal_claim(text)

    dom_inst, url_inst, src_inst = _build_instructions(
        claim_type, input_type, source_url, submitted_url_is_credible, high_risk_claim, confirmation_status, confirmation_score
    )

    system_prompt = f"""You are an expert fact-checker analyzing claims against submitted evidence and live web search results.
Date: {datetime.datetime.now().strftime("%B %d, %Y")}. Mode: {input_type}.
CLAIM: {text}
LIVE SEARCH: {live_context}
RULES:
{dom_inst}
{url_inst}
{src_inst}
FACT-CHECK: If fact-check sources report missing context or false, prioritize that over general news.
VERDICTS: SUPPORTED, REFUTED, INSUFFICIENT EVIDENCE, MISLEADING, LOW CREDIBILITY.
Respond ONLY with valid JSON:
{{"verdict": "VERDICT", "confidence": <0-100>, "reason": "<one sentence>", "fact_check": "<summary>", "red_flags": [], "recommendations": []}}"""

    payload = json.dumps({
        "model": config.COHERE_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Analyze this claim based on the evidence provided above."}
        ],
        "response_format": {"type": "json_object"}, "temperature": 0.0, "max_tokens": 700
    }).encode("utf-8")

    req = urllib.request.Request(
        config.COHERE_URL, data=payload, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.COHERE_API_KEY}", "X-Client-Name": "debunkit"}
    )

    try:
        with urllib.request.urlopen(req, timeout=config.COHERE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        raw = data["message"]["content"][0]["text"].strip()
        try:
            res = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S) or re.search(r"(\{.*\})", raw, re.S)
            if not m:
                raise
            res = json.loads(m.group(1).strip())

        res["verdict"] = normalize_verdict(res.get("verdict"))
        res["confidence"] = clamp_confidence(res.get("confidence"), default=55)
        res["sources"] = merge_sources(source_url, source_links)

        if factcheck_override:
            res.update({k: factcheck_override[k] for k in ["verdict", "confidence", "reason", "fact_check"]})
            old_flags = res.get("red_flags") if isinstance(res.get("red_flags"), list) else []
            res["red_flags"] = list(dict.fromkeys(factcheck_override["red_flags"] + old_flags))[:6]
            return res

        if confirmation_status == "supported" and res["verdict"] == "SUPPORTED":
            res["confidence"] = min(res["confidence"] + 8, 95)
        elif confirmation_status == "refuted" and res["verdict"] in {"REFUTED", "MISLEADING"}:
            res["confidence"] = min(res["confidence"] + 8, 95)

        if input_type != "url" and confirmation_status == "insufficient" and res["verdict"] == "SUPPORTED":
            res["confidence"] = min(res["confidence"], 70)
            res["fact_check"] = (str(res.get("fact_check", "")) + " Source matcher did not find explicit confirmation; treat as tentative.").strip()

        if input_type != "url" and causal_claim and confirmation_status != "supported" and res["verdict"] == "SUPPORTED":
            res["verdict"] = "INSUFFICIENT EVIDENCE"
            res["confidence"] = min(res["confidence"], 55)
            res["reason"] = "Sources mention the topic, but do not confirm the specific reason or cause stated."
            res["fact_check"] = "Same-topic sources are not enough for causal claims. Direct proof for reason required."
            flags = res.get("red_flags") if isinstance(res.get("red_flags"), list) else []
            res["red_flags"] = list(dict.fromkeys(["Specific cause/reason not directly supported"] + flags))[:6]

        if (input_type == "url" and source_url and submitted_url_is_credible and not high_risk_claim
                and claim_type in {"sports", "general"} and confirmation_status != "refuted"
                and res["verdict"] == "INSUFFICIENT EVIDENCE" and res["confidence"] <= 65):
            res["verdict"] = "SUPPORTED"
            res["confidence"] = max(res["confidence"], 74)
            res["reason"] = "Submitted article was retrieved from a recognized news source and directly reports the routine claim."
            res["fact_check"] = "The article provides primary support. External corroboration limited but no contradiction found."
            flags = res.get("red_flags") if isinstance(res.get("red_flags"), list) else []
            res["red_flags"] = [f for f in flags if not any(k in str(f).lower() for k in ["snippet", "hyperlink", "missing exact"])]

        return res

    except Exception as e:
        logger.warning(f"AI analysis attempt {retry_count + 1} failed: {e}")
        if retry_count < max_retries and not (isinstance(e, urllib.error.HTTPError) and e.code == 401):
            return ai_analyze(text, input_type, source_url, source_text, retry_count + 1, max_retries)
        return None

def hybrid_analyze(text, input_type="text", source_url=None, source_text=None):
    """Perform analysis with AI priority, fallback to local NLP."""
    ai = ai_analyze(text, input_type=input_type, source_url=source_url, source_text=source_text)
    if ai:
        return {
            "verdict": normalize_verdict(ai.get("verdict")),
            "confidence": clamp_confidence(ai.get("confidence"), default=55),
            "reason": ai.get("reason", ""), "fact_check": ai.get("fact_check", ""),
            "red_flags": (ai.get("red_flags") or [])[:6], "recommendations": ai.get("recommendations", []),
            "sources": ai.get("sources", []), "mode": "ai"
        }

    local = local_analyze(text)
    net, claim_flags, credible_hits = local["net_score"], local["claim_flags"], local["credible_hits"]
    fake_thresh = getattr(config, "FAKE_THRESHOLD_LOCAL", 35)
    min_hits = getattr(config, "MIN_CREDIBLE_HITS", 2)

    if net >= fake_thresh or (claim_flags and credible_hits < min_hits):
        verdict, confidence = "LOW CREDIBILITY", min(50 + net // 2, 85)
        reason = claim_flags[0] if claim_flags else "Multiple misinformation-risk patterns were detected."
    elif credible_hits >= min_hits:
        verdict, confidence = "INSUFFICIENT EVIDENCE", min(45 + credible_hits * 5, 65)
        reason = "Some credibility signals were found, but live source verification was unavailable."
    else:
        verdict, confidence = "INSUFFICIENT EVIDENCE", 50
        reason = "AI/source verification was unavailable, so the claim cannot be confirmed."

    fallback_sources = [{"title": "Submitted article", "url": source_url}] if (input_type == "url" and source_url) else []
    return {
        "verdict": verdict, "confidence": confidence, "reason": reason,
        "fact_check": "AI analysis unavailable — using local pattern analysis only.",
        "red_flags": local["red_flags"],
        "recommendations": ["Connect to internet for more accurate AI-powered fact-checking"],
        "sources": fallback_sources, "mode": "local_fallback"
    }
