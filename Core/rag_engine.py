import re
import time
import logging
import threading
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from config import config
from utils.validators import validate_url_input, ValidationError

logger = logging.getLogger(__name__)

_SEARCH_CACHE = {}
_CACHE_LOCK = threading.Lock()

def get_live_context(query):
    """Search the internet for live context with caching and parallel requests."""
    logger.info(f"RAG Engine: Processing query with {len(query)} characters")
    cache_key = query.strip().lower()
    ttl = getattr(config, "RAG_CACHE_TTL_SECONDS", 3600)
    now = time.time()

    with _CACHE_LOCK:
        if cache_key in _SEARCH_CACHE:
            cached_time, block, sources = _SEARCH_CACHE[cache_key]
            if now - cached_time < ttl:
                logger.info("[*] RAG CACHE HIT: Serving context from memory")
                return block, sources
            del _SEARCH_CACHE[cache_key]

    try:
        direct_query = " ".join(re.sub(r'\s+', ' ', query).strip().split()[:14])
        years = re.findall(r'\b20\d{2}\b', query)
        stop_words = {"The", "A", "An", "This", "That", "It", "In", "On", "If", "But", "And", "Or", "Is", "Are", "Was", "Were", "Has", "Have"}
        entities = [w for w in re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', query) if w not in stop_words]
        keywords = list(dict.fromkeys(entities + years + re.findall(
            r'\b(video|photo|image|rally|cruise|hantavirus|outbreak|dropped|poor|fielding|predicted|confirmed|inside|uk|london|stamford|street|simpsons)\b',
            query, re.I
        )))[:8]
        entity_query = " ".join(keywords)

        search_queries = []
        if direct_query:
            search_queries.extend([direct_query, f"{direct_query} fact check"])
        elif entity_query:
            search_queries.append(entity_query)
        search_queries = list(dict.fromkeys([q for q in search_queries if q]))[:2]

        if not search_queries:
            return "No extractable search terms found.", []

        def fetch_ddg(q):
            res = []
            try:
                with DDGS() as ddgs:
                    for method in (ddgs.news, ddgs.text):
                        try:
                            for r in method(q, max_results=4):
                                r["_query"] = q
                                res.append(r)
                        except Exception:
                            pass
            except Exception as err:
                logger.warning(f"DDG search worker failed for '{q}': {err}")
            return res

        all_results, seen_urls = [], set()
        with ThreadPoolExecutor(max_workers=len(search_queries)) as executor:
            for fut in as_completed({executor.submit(fetch_ddg, q): q for q in search_queries}):
                for res in fut.result():
                    url = res.get("url") or res.get("href") or "#"
                    if url != "#" and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(res)
                        if len(all_results) >= 8:
                            break

        if not all_results:
            return "No relevant web search results found for this query.", []

        context_block = "LIVE WEB SEARCH RESULTS:\n"
        sources = []
        for i, res in enumerate(all_results[:8], 1):
            title = res.get("title", "Unknown")
            body = (res.get("body") or res.get("snippet", ""))[:650]
            url = res.get("url") or res.get("href") or "#"
            if url != "#":
                sources.append({"title": title, "url": url})
            context_block += f"\n{i}. [{title}]\n   URL: {url}\n   Snippet: {body}\n   SearchQuery: {res.get('_query', '')}\n"

        with _CACHE_LOCK:
            _SEARCH_CACHE[cache_key] = (now, context_block, sources)
        return context_block, sources

    except Exception as e:
        logger.exception(f"Unexpected error in RAG engine: {e}")
        return "Live web context unavailable due to search error.", []

def get_article_context_from_search(url):
    """Fallback retrieval: search web for article title/context if direct scrape fails."""
    try:
        parsed = urlparse(url)
        slug = re.sub(r'[-_/.]+', ' ', parsed.path).strip()
        query = f"{parsed.netloc} {slug}".strip() if len(slug) >= 3 else url
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3)) or list(ddgs.text(url, max_results=3))
        if results:
            snippets = [f"{r.get('title', '')}. {r.get('body', '')}" for r in results if r.get('title') or r.get('body')]
            return " ".join(snippets), results
    except Exception as e:
        logger.warning(f"Fallback search context failed for {url}: {e}")
    return None, []

def scrape_article(url):
    """Scrape article content from URL with browser headers, 404 slash retries, and search fallback."""
    try:
        url = validate_url_input(url)
    except ValidationError as e:
        return None, f"Blocked unsafe URL: {e}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    resp = None
    try:
        resp = requests.get(url, headers=headers, timeout=config.SCRAPER_TIMEOUT, allow_redirects=True)
        validate_url_input(resp.url)
        if resp.status_code == 404:
            alt_url = url[:-1] if url.endswith('/') else url + '/'
            alt_resp = requests.get(alt_url, headers=headers, timeout=config.SCRAPER_TIMEOUT, allow_redirects=True)
            if alt_resp.status_code == 200:
                resp = alt_resp
    except ValidationError as e:
        return None, f"Blocked unsafe redirect target: {e}"
    except Exception as err:
        logger.warning(f"Initial fetch failed for {url}: {err}")

    if resp and resp.status_code == 200:
        try:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            paras = soup.find_all('p')
            text = " ".join(p.get_text() for p in paras) if paras else soup.get_text()
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text.split()) >= config.SCRAPER_MIN_WORDS:
                return text, None
        except Exception as e:
            logger.warning(f"Error parsing HTML: {e}")

    fallback_text, _ = get_article_context_from_search(url)
    if fallback_text and len(fallback_text.split()) >= config.SCRAPER_MIN_WORDS:
        return fallback_text, None

    status = f" HTTP {resp.status_code}" if resp is not None else ""
    return None, f"Failed to fetch URL.{status}"
