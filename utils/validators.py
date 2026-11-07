import socket
import ipaddress
from urllib.parse import urlparse
from config import config

class ValidationError(ValueError):
    """Custom validation error."""
    pass

def validate_text_input(text):
    """Validate text input for analysis."""
    if not isinstance(text, str):
        raise ValidationError("Input must be a string")
    text = text.strip()
    if not text:
        raise ValidationError("Input cannot be empty")
    if len(text) > config.MAX_TEXT_LENGTH:
        raise ValidationError(f"Input exceeds maximum length of {config.MAX_TEXT_LENGTH} characters")
    if len(text) < config.MIN_TEXT_LENGTH:
        raise ValidationError(f"Input must be at least {config.MIN_TEXT_LENGTH} characters long")
    if any(c in text for c in "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f"):
        raise ValidationError("Input contains invalid control characters")
    return " ".join(text.split())

def _is_ip_unsafe(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_multicast or ip.is_reserved or ip.is_unspecified)
    except ValueError:
        return False

def is_private_or_local_hostname(hostname):
    """Block local/private/internal hostnames and IPs to prevent SSRF."""
    if not hostname:
        return True
    host = hostname.strip().lower().rstrip(".")
    if host in {"localhost", "0.0.0.0", "127.0.0.1", "::1"} or host.endswith((".localhost", ".local")):
        return True
    if _is_ip_unsafe(host):
        return True
    try:
        for res in socket.getaddrinfo(host, None):
            if _is_ip_unsafe(res[4][0]):
                return True
    except socket.gaierror:
        return True
    return False

def validate_url_input(url):
    """Validate URL input for scraping and block SSRF-risk targets."""
    if not isinstance(url, str):
        raise ValidationError("URL must be a string")
    url = url.strip()
    if not url:
        raise ValidationError("URL cannot be empty")
    if len(url) > config.MAX_URL_LENGTH:
        raise ValidationError(f"URL exceeds maximum length of {config.MAX_URL_LENGTH} characters")
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValidationError("URL must use http or https")
        if not parsed.netloc or not parsed.hostname:
            raise ValidationError("URL must include a valid domain")
        if parsed.username or parsed.password:
            raise ValidationError("URL must not contain username or password")
        if is_private_or_local_hostname(parsed.hostname):
            raise ValidationError("Private, local, or internal URLs are not allowed")
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Invalid URL: {e}")
    return url

def validate_headline(headline):
    """Validate headline input."""
    return validate_text_input(headline)
