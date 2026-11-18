from unittest.mock import patch, MagicMock
import pytest
from Core import rag_engine
from debunkit_app import app


def _resp(status=200, location=None):
    r = MagicMock(status_code=status)
    r.is_redirect = location is not None
    r.headers = {"Location": location} if location else {}
    return r


def test_redirect_to_internal_host_is_blocked_before_connecting():
    with patch("utils.validators.socket.getaddrinfo", return_value=[(0, 0, 0, "", ("93.184.216.34", 0))]), \
         patch("Core.rag_engine.requests.get", return_value=_resp(302, "http://169.254.169.254/latest/meta-data/")) as get:
        text, err = rag_engine.scrape_article("http://public.example/start")
    assert text is None and "Blocked unsafe" in err
    assert get.call_count == 1  # the internal hop was never requested


def test_security_headers_present():
    r = app.test_client().get("/api/health")
    assert r.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_proxyfix_mounted():
    from werkzeug.middleware.proxy_fix import ProxyFix
    assert isinstance(app.wsgi_app, ProxyFix)
