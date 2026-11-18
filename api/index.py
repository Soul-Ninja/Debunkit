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
    (x-forwarded-uri, x-matched-path, or x-now-route-matches) so Flask
    routes ('/', '/scanner', '/api/stats', etc.) resolve correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
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
