import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from debunkit_app import app as flask_app


class VercelPathFixMiddleware:
    """
    Vercel serverless rewrites route requests to /api/index, which sets
    PATH_INFO to '/api/index' inside the WSGI environment.
    This middleware extracts the true browser path from Vercel's headers
    so Flask routes ('/', '/scanner', '/api/stats', etc.) resolve correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        if environ.get("HTTP_X_DEBUG_ENV") == "1":
            start_response("200 OK", [("Content-Type", "application/json")])
            safe_env = {
                k: str(v) for k, v in environ.items()
                if not any(s in k.upper() for s in ["KEY", "SECRET", "PASS", "AUTH", "TOKEN", "COOKIE"])
            }
            return [json.dumps(safe_env, indent=2).encode("utf-8")]

        raw_uri = (
            environ.get("HTTP_X_FORWARDED_URI")
            or environ.get("HTTP_X_MATCHED_PATH")
            or environ.get("HTTP_X_NOW_ROUTE_MATCHES")
        )
        if raw_uri:
            path = raw_uri.split("?")[0]
            if path:
                environ["PATH_INFO"] = path
        elif environ.get("PATH_INFO") in ("/api/index", "/api/index.py", "/api"):
            environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


app = VercelPathFixMiddleware(flask_app)

