import os
import sys
import urllib.parse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from debunkit_app import app as flask_app


class VercelPathFixMiddleware:
    """
    Vercel serverless rewrites route requests to /api/index?__vercel_path=/<path>.
    This middleware extracts the true browser path from the query string or headers
    and restores PATH_INFO and QUERY_STRING so Flask routes resolve correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING", "")
        if "__vercel_path=" in query_string:
            params = urllib.parse.parse_qs(query_string, keep_blank_values=True)
            if "__vercel_path" in params:
                raw_path = params.pop("__vercel_path")[0]
                if not raw_path.startswith("/"):
                    raw_path = "/" + raw_path
                while "//" in raw_path:
                    raw_path = raw_path.replace("//", "/")
                if not raw_path:
                    raw_path = "/"
                environ["PATH_INFO"] = raw_path
                # Reconstruct QUERY_STRING without the routing helper parameter
                environ["QUERY_STRING"] = urllib.parse.urlencode(params, doseq=True)
        elif environ.get("PATH_INFO") in ("/api/index", "/api/index.py", "/api"):
            environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


app = VercelPathFixMiddleware(flask_app)


