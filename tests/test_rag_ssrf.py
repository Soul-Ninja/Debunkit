import socket
import pytest
from unittest.mock import patch, MagicMock
from Core.rag_engine import _safe_get, PinnedIPAdapter
from utils.validators import ValidationError
import requests.adapters


def test_hostname_resolving_to_private_ip_blocked():
    """Verify that a hostname resolving to private IP is blocked from fetching."""
    with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 80))]):
        with pytest.raises(ValidationError) as excinfo:
            _safe_get("http://rebind-to-private.example.com/news", headers={})
        assert "private or unsafe IP" in str(excinfo.value) or "Private, local, or internal" in str(excinfo.value)


def test_oversized_response_body_blocked():
    """Verify that responses exceeding 2 MB are aborted with a ValidationError."""
    fake_resp = MagicMock()
    fake_resp.is_redirect = False
    fake_resp.iter_content.return_value = [b"X" * (1024 * 1024)] * 3  # 3 MB

    with patch("Core.rag_engine._resolve_and_validate_host", return_value="93.184.215.14"), \
         patch("requests.Session.get", return_value=fake_resp):
        with pytest.raises(ValidationError) as excinfo:
            _safe_get("http://example.com/oversized-page", headers={})
        assert "exceeds maximum size limit" in str(excinfo.value)


def test_pinned_ip_adapter_preserves_sni_and_pins_ip():
    """Verify that PinnedIPAdapter sets the pinned IP on connections while keeping SNI."""
    adapter = PinnedIPAdapter("93.184.215.14", "example.com")
    mock_conn = MagicMock()
    mock_pool = MagicMock()
    mock_pool._new_conn.return_value = mock_conn

    with patch.object(requests.adapters.HTTPAdapter, "get_connection_with_tls_context", return_value=mock_pool):
        mock_req = MagicMock()
        mock_req.url = "https://example.com/article"
        conn = adapter.get_connection_with_tls_context(mock_req, verify=True)
        new_c = conn._new_conn()
        assert new_c._dns_host == "93.184.215.14"
        assert new_c.server_hostname == "example.com"
