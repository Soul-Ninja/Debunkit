import os
import re
import secrets
import hmac
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from flask import Flask, request, jsonify, render_template, redirect, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from config import config
from Core.database import (
    db, init_db, save_review, get_recent_reviews,
    save_analysis, get_analysis_history, get_analysis_by_id,
    search_analyses, get_statistics, Analysis
)
from Core.user_model import User
from Core.ai_engine import hybrid_analyze
from Core.rag_engine import scrape_article
from utils.validators import validate_text_input, validate_url_input, ValidationError

# ===== LOGGING & APP INITIALIZATION =====
log_dir = os.path.dirname(config.LOG_FILE)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(config.LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="Template", static_folder="Static")
app.config.from_object(config)

# ===== CSRF PROTECTION =====
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_SESSION_KEY = "_csrf_token"

def generate_csrf_token():
    if CSRF_SESSION_KEY not in session:
        session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    return session[CSRF_SESSION_KEY]

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token)

@app.before_request
def csrf_protect():
    if app.config.get("TESTING") or not app.config.get("WTF_CSRF_ENABLED", True):
        return
    if request.method not in UNSAFE_METHODS:
        return
    session_token = session.get(CSRF_SESSION_KEY)
    request_token = (
        request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
        or request.form.get("csrf_token")
    )
    if not session_token or not request_token or not hmac.compare_digest(session_token, request_token):
        logger.warning(f"CSRF blocked: method={request.method}, path={request.path}, ip={request.remote_addr}")
        return jsonify({"error": "Invalid or missing CSRF token"}), 403

# ===== HELPERS =====
def validate_password_strength(password):
    if not password:
        return False, "Password is required"
    if len(password) < config.MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters long"
    if not re.match(config.PASSWORD_COMPLEXITY_REGEX, password):
        return False, "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character"
    return True, None

def is_cached_analysis_fresh(analysis, input_type):
    if not analysis or not analysis.timestamp:
        return False
    hours = getattr(config, "CACHE_MAX_AGE_HOURS_URL", 6) if input_type == "url" else getattr(config, "CACHE_MAX_AGE_HOURS_TEXT", 24)
    ts = analysis.timestamp.replace(tzinfo=timezone.utc) if analysis.timestamp.tzinfo is None else analysis.timestamp
    return (datetime.now(timezone.utc) - ts) <= timedelta(hours=hours)

def _mask_email(email):
    if not email or "@" not in email:
        return "invalid-email"
    name, domain = email.split("@", 1)
    return f"{name[:2]}***@{domain}" if len(name) >= 2 else f"***@{domain}"

# ===== EXTENSIONS =====
init_db(app)
CORS(app, origins=config.CORS_ORIGINS)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.RATELIMIT_DEFAULT],
    storage_uri=getattr(config, "RATELIMIT_STORAGE_URI", "memory://")
)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/") or request.is_json or "application/json" in request.headers.get("Accept", ""):
        return jsonify({"error": "Authentication required", "authenticated": False}), 401
    return redirect("/login")

# ===== FRONTEND VIEWS =====
@app.route("/")
def index():
    return render_template("landing.html")

@app.route("/scanner")
def scanner():
    return render_template("index.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("index.html")

@app.route("/history")
@app.route("/analytics")
def spa_views():
    return render_template("index.html")

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)

@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", user=current_user)

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def register():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        if not username or len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        if not email or "@" not in email:
            return jsonify({"error": "Invalid email address"}), 400
        is_valid, err = validate_password_strength(password)
        if not is_valid:
            return jsonify({"error": err}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already taken"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already registered"}), 400
        user = User(username=username, email=email)
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
            logger.info(f"New user registered: {username}")
            return jsonify({"status": "success", "message": "Account created! Please log in."}), 201
        except Exception as e:
            logger.error(f"Registration error: {e}")
            db.session.rollback()
            return jsonify({"error": "Registration failed"}), 500
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip()
        password = data.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt from {request.remote_addr} for {_mask_email(email)}")
            return jsonify({"error": "Invalid email or password"}), 401
        login_user(user, remember=data.get("remember", False))
        logger.info(f"User logged in: {user.username}")
        return jsonify({"status": "success", "redirect": "/dashboard"}), 200
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logger.info(f"User logged out: {current_user.username}")
    logout_user()
    return jsonify({"status": "success", "redirect": "/"}), 200

# ===== API VIEWS =====
def analyze_limit():
    return config.RATELIMIT_DEFAULT if current_user.is_authenticated else "100 per day"

@app.route("/analyze", methods=["POST"])
@limiter.limit(analyze_limit)
def analyze():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        raw_input, input_type = data.get("text", ""), data.get("type", "text")
        try:
            valid_input = validate_url_input(raw_input) if input_type == "url" else validate_text_input(raw_input)
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

        logger.info(f"Processing {input_type} request from {request.remote_addr} (user: {current_user.username if current_user.is_authenticated else 'guest'})")

        if current_user.is_authenticated:
            cached = Analysis.query.filter_by(text_analyzed=valid_input[:5000], user_id=current_user.id).order_by(Analysis.timestamp.desc()).first()
            if cached and is_cached_analysis_fresh(cached, input_type):
                logger.info("[*] FRESH CACHE HIT! Serving recent cached result.")
                res = cached.to_dict()
                res["reason"] = (res.get("reason") or "") + " (Served from recent cache)"
                res["cache_status"] = "fresh"
                return jsonify(res), 200

        if input_type == "url":
            scraped_text, error_msg = scrape_article(valid_input)
            if scraped_text:
                text_to_analyze = scraped_text[:config.SCRAPER_MAX_CHARS]
            else:
                parsed = urlparse(valid_input)
                slug = re.sub(r'[-_/.]+', ' ', parsed.path).strip()
                text_to_analyze = f"Article from {parsed.netloc}: {slug or valid_input}"
                logger.info(f"URL scrape note: {error_msg}. Evaluating URL source topic: {text_to_analyze}")
        else:
            text_to_analyze = valid_input

        result = hybrid_analyze(
            text_to_analyze,
            input_type=input_type,
            source_url=valid_input if input_type == "url" else None,
            source_text=text_to_analyze if input_type == "url" else None
        )

        if current_user.is_authenticated:
            saved = save_analysis(
                text=valid_input, verdict=result.get("verdict"), confidence=result.get("confidence"),
                reason=result.get("reason"), fact_check=result.get("fact_check"), red_flags=result.get("red_flags"),
                sources=result.get("sources"), mode=result.get("mode"), user=current_user, request=request
            )
            result["analysis_id"] = saved.id if saved else None
        else:
            result["analysis_id"] = None
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in /analyze: {e}")
        return jsonify({"error": "Analysis failed"}), 500

@app.route("/api/history", methods=["GET"])
def api_history():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False, "total": 0, "limit": 0, "offset": 0, "analyses": [], "error": "Authentication required to view analysis history"}), 401
    try:
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = int(request.args.get("offset", 0))
        history = get_analysis_history(user=current_user, limit=limit, offset=offset)
        return jsonify({"authenticated": True, "total": len(history), "limit": limit, "offset": offset, "analyses": history}), 200
    except Exception as e:
        logger.error(f"Error in /api/history: {e}")
        return jsonify({"error": "Failed to fetch history"}), 500

@app.route("/api/analysis/<int:analysis_id>", methods=["GET"])
@login_required
def api_analysis_detail(analysis_id):
    try:
        analysis = get_analysis_by_id(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404
        if analysis["user_id"] != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        return jsonify(analysis), 200
    except Exception as e:
        logger.error(f"Error in /api/analysis/{analysis_id}: {e}")
        return jsonify({"error": "Failed to fetch analysis"}), 500

@app.route("/api/search", methods=["GET"])
@login_required
@limiter.limit("20 per minute")
def api_search():
    try:
        query = request.args.get("q", "").strip()
        if not query or len(query) < 2:
            return jsonify({"error": "Search query must be at least 2 characters"}), 400
        limit = min(int(request.args.get("limit", 50)), 100)
        results = search_analyses(query, user=current_user, limit=limit)
        return jsonify({"query": query, "total": len(results), "results": results}), 200
    except Exception as e:
        logger.error(f"Error in /api/search: {e}")
        return jsonify({"error": "Search failed"}), 500

@app.route("/api/stats", methods=["GET"])
def api_stats():
    try:
        user = current_user if (request.args.get("scope") == "user" and current_user.is_authenticated) else None
        return jsonify(get_statistics(user=user)), 200
    except Exception as e:
        logger.error(f"Error in /api/stats: {e}")
        return jsonify({"error": "Failed to fetch statistics"}), 500

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "mode": "debug" if app.debug else "production"}), 200

@app.route("/api/clear-database", methods=["POST"])
@limiter.limit("5 per minute")
def clear_database():
    try:
        if current_user.is_authenticated:
            count = Analysis.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
            logger.warning(f"Database cleared for user {current_user.username}: {count} analyses deleted")
        else:
            try:
                count = Analysis.query.filter(Analysis.user_id.is_(None)).delete()
                db.session.commit()
            except Exception:
                db.session.rollback()
                count = 0
            logger.info("Guest / session database cleared")
        return jsonify({"status": "success", "message": "Database cleared successfully", "deleted": count}), 200
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to clear database"}), 500

@app.route("/api/user/profile", methods=["GET", "PUT"])
@login_required
def api_user_profile():
    if request.method == "GET":
        return jsonify(current_user.to_dict()), 200
    try:
        data = request.get_json(silent=True) or {}
        if "username" in data:
            new_user = data["username"].strip()
            if len(new_user) < 3:
                return jsonify({"error": "Username must be at least 3 characters"}), 400
            existing = User.query.filter_by(username=new_user).first()
            if existing and existing.id != current_user.id:
                return jsonify({"error": "Username already taken"}), 400
            current_user.username = new_user

        if "email" in data:
            new_email = data["email"].strip()
            if "@" not in new_email:
                return jsonify({"error": "Invalid email address"}), 400
            existing = User.query.filter_by(email=new_email).first()
            if existing and existing.id != current_user.id:
                return jsonify({"error": "Email already registered"}), 400
            current_user.email = new_email

        db.session.commit()
        logger.info(f"Profile updated for user: {current_user.username}")
        return jsonify({"status": "success", "message": "Profile updated successfully"}), 200
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to update profile"}), 500

@app.route("/api/user/settings", methods=["PUT"])
@login_required
def api_user_settings():
    try:
        data = request.get_json(silent=True) or {}
        if "theme" in data:
            if data["theme"] not in ["dark", "light", "system"]:
                return jsonify({"error": "Invalid theme value"}), 400
            current_user.theme = data["theme"]

        if "email_notifications" in data:
            current_user.email_notifications = bool(data["email_notifications"])

        if data.get("new_password"):
            cur_pwd, new_pwd = data.get("current_password", ""), data.get("new_password", "")
            if not cur_pwd:
                return jsonify({"error": "Current password is required"}), 400
            if not current_user.check_password(cur_pwd):
                return jsonify({"error": "Current password is incorrect"}), 401
            is_valid, err = validate_password_strength(new_pwd)
            if not is_valid:
                return jsonify({"error": err}), 400
            if current_user.check_password(new_pwd):
                return jsonify({"error": "New password must be different from current password"}), 400
            current_user.set_password(new_pwd)

        db.session.commit()
        logger.info(f"Settings updated for user: {current_user.username}")
        return jsonify({"status": "success", "message": "Settings saved"}), 200
    except Exception as e:
        logger.error(f"Settings update error: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to update settings"}), 500

@app.route("/api/user/delete", methods=["DELETE"])
@login_required
def api_delete_account():
    try:
        user = current_user._get_current_object()
        Analysis.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        logger.warning(f"Account deleted: {user.username}")
        logout_user()
        return jsonify({"status": "success", "message": "Account deleted"}), 200
    except Exception as e:
        logger.error(f"Account deletion error: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to delete account"}), 500

@app.route("/api/reviews", methods=["GET", "POST"])
@limiter.limit("10/minute", methods=["POST"])
def api_reviews():
    if request.method == "POST":
        try:
            data = request.get_json(silent=True) or request.form
            author = (data.get("author") or data.get("author_name") or "").strip()
            role = (data.get("role") or data.get("author_role") or "Truth Seeker").strip()
            rating = int(data.get("rating", 5))
            content = (data.get("content") or "").strip()
            avatar = data.get("avatar", "⭐")
            if not author or not content:
                return jsonify({"error": "Author name and review content are required"}), 400
            if len(content) < 5 or len(content) > 500:
                return jsonify({"error": "Review must be between 5 and 500 characters"}), 400
            review = save_review(author, role, rating, content, avatar)
            if not review:
                return jsonify({"error": "Failed to save review"}), 500
            logger.info(f"New community review submitted by {author} ({rating} stars)")
            return jsonify({"status": "success", "message": "Review submitted successfully!", "review": review.to_dict()}), 201
        except Exception as e:
            logger.error(f"Error submitting review: {e}")
            return jsonify({"error": "Failed to submit review"}), 500

    try:
        reviews = get_recent_reviews(limit=12)
        return jsonify({"status": "success", "reviews": [r.to_dict() for r in reviews]}), 200
    except Exception as e:
        logger.error(f"Error fetching reviews: {e}")
        return jsonify({"status": "error", "reviews": []}), 500

# ===== ERROR HANDLERS =====
@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded from {request.remote_addr}")
    msg = "Rate limit exceeded. Please wait and try again." if current_user.is_authenticated else "Guest limit reached. Please log in to continue."
    return jsonify({"error": msg}), 429

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting Debunk.IT server...")
    app.run(host="127.0.0.1", port=5000, debug=app.debug)
