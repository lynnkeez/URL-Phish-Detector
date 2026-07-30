"""Shared, URL-only feature pipeline for PhishGuard.

These features are intentionally limited to the submitted URL.  The same
function is used to create the training matrix and to make live predictions;
no webpage content, DNS lookup, or network request is required.
"""

from collections import Counter
import ipaddress
import math
import re
from urllib.parse import urlparse

LEGITIMATE_TLDS = {"com", "org", "net", "edu", "gov", "io", "co", "uk", "de", "ke"}
SUSPICIOUS_TLDS = {"zip", "mov", "top", "xyz", "click", "gq", "tk", "ml", "cf", "work"}
PHISHING_KEYWORDS = {
    "login", "signin", "sign-in", "verify", "secure", "account", "update",
    "banking", "password", "credential", "confirm", "wallet", "billing",
    "invoice", "support", "alert", "suspended", "unlock",
}
BRAND_NAMES = {
    "paypal", "apple", "amazon", "google", "microsoft", "facebook", "netflix",
    "instagram", "linkedin", "dropbox", "chase", "wellsfargo", "barclays", "hsbc",
}


MAX_URL_LENGTH = 255


def normalise_url(url: str, enforce_length: bool = True) -> str:
    """Return a browser-style URL with a scheme, or raise ValueError."""
    value = (url or "").strip()
    if not value or (enforce_length and len(value) > MAX_URL_LENGTH) or any(c.isspace() for c in value):
        raise ValueError(f"Enter a valid URL no longer than {MAX_URL_LENGTH} characters.")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        value = "http://" + value
    parsed = urlparse(value)
    try:
        hostname = parsed.hostname
        parsed.port  # Validates malformed port syntax.
    except ValueError as exc:
        raise ValueError("Enter a valid http or https URL.") from exc
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise ValueError("Enter a valid http or https URL.")
    return value


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    frequencies = Counter(value)
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in frequencies.values())


def _is_ip(hostname: str) -> int:
    try:
        ipaddress.ip_address(hostname)
        return 1
    except ValueError:
        return 0


def extract_features(url: str, enforce_length: bool = True) -> dict:
    """Extract a stable, numeric feature dictionary from one URL.

    ``enforce_length=False`` is reserved for historical training data, where
    long URLs are valid observations even though the web form rejects them.
    """
    normalised = normalise_url(url, enforce_length=enforce_length)
    parsed = urlparse(normalised)
    hostname = (parsed.hostname or "").lower()
    host_parts = hostname.split(".")
    tld = host_parts[-1] if len(host_parts) > 1 else ""
    domain = host_parts[-2] if len(host_parts) > 1 else hostname
    subdomains = host_parts[:-2] if len(host_parts) > 2 else []
    path_query = f"{parsed.path}?{parsed.query}".lower()
    lower_url = normalised.lower()
    keyword_count = sum(keyword in lower_url for keyword in PHISHING_KEYWORDS)
    brand_in_subdomain = any(brand in ".".join(subdomains) for brand in BRAND_NAMES)

    return {
        "url_length": len(normalised),
        "url_entropy": round(_entropy(normalised), 4),
        "hostname_length": len(hostname),
        "domain_length": len(domain),
        "domain_entropy": round(_entropy(domain), 4),
        "tld_length": len(tld),
        "subdomain_count": len(subdomains),
        "path_length": len(parsed.path),
        "path_depth": parsed.path.count("/"),
        "query_length": len(parsed.query),
        "digit_ratio": round(sum(c.isdigit() for c in normalised) / len(normalised), 4),
        "special_char_count": sum(c in "-_.~!*()@%" for c in normalised),
        "dot_count": normalised.count("."),
        "hyphen_count": normalised.count("-"),
        "slash_count": normalised.count("/"),
        "has_https": int(parsed.scheme == "https"),
        "ip_address": _is_ip(hostname),
        "has_port": int(parsed.port is not None),
        "has_at_symbol": int("@" in normalised),
        "has_encoded_char": int("%" in normalised),
        "has_double_slash_path": int("//" in parsed.path),
        "has_query": int(bool(parsed.query)),
        "has_fragment": int(bool(parsed.fragment)),
        "file_extension": int(bool(re.search(r"\.(php|asp|aspx|jsp|cgi|exe|html?)$", parsed.path.lower()))),
        "hyphen_in_domain": int("-" in domain),
        "digit_in_domain": int(any(c.isdigit() for c in domain)),
        "legitimate_tld": int(tld in LEGITIMATE_TLDS),
        "suspicious_tld": int(tld in SUSPICIOUS_TLDS),
        "phishing_keyword_count": keyword_count,
        "brand_in_subdomain": int(brand_in_subdomain),
        "brand_in_path_or_query": int(any(brand in path_query for brand in BRAND_NAMES)),
    }


FEATURE_NAMES = list(extract_features("https://example.com").keys())
