"""
PhishGuard - Feature Extractor
Extracts 30 URL-based features for ML classification.
No external API calls needed — all features derived from URL structure.
"""

import re
import math
from urllib.parse import urlparse
from collections import Counter

# Common legitimate TLDs
LEGITIMATE_TLDS = {'.com', '.org', '.net', '.edu', '.gov', '.io', '.co'}

# Suspicious keywords often found in phishing URLs
PHISHING_KEYWORDS = [
    'login', 'signin', 'sign-in', 'verify', 'secure', 'account', 'update',
    'banking', 'paypal', 'apple', 'amazon', 'google', 'microsoft', 'facebook',
    'password', 'credential', 'confirm', 'wallet', 'billing', 'invoice',
    'support', 'helpdesk', 'alert', 'suspended', 'limited', 'unlock'
]

# Well-known brand names targeted by phishers
BRAND_NAMES = [
    'paypal', 'apple', 'amazon', 'google', 'microsoft', 'facebook',
    'netflix', 'instagram', 'twitter', 'linkedin', 'dropbox', 'chase',
    'wellsfargo', 'bankofamerica', 'citibank', 'barclays', 'hsbc'
]


def _entropy(string: str) -> float:
    """Shannon entropy of a string (measures randomness)."""
    if not string:
        return 0.0
    freq = Counter(string)
    length = len(string)
    return -sum((c / length) * math.log2(c / length) for c in freq.values())


def extract_features(url: str) -> dict:
    """
    Extract 30 features from a URL.
    Returns a dict with feature names and values.
    """
    features = {}

    # ── Parse URL ──────────────────────────────────────────────────────────
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    try:
        parsed = urlparse(url)
    except Exception:
        # Return all-zero features for unparseable URLs
        return {f'f{i}': 0 for i in range(30)}

    scheme   = parsed.scheme or ''
    netloc   = parsed.netloc or ''
    path     = parsed.path or ''
    query    = parsed.query or ''
    fragment = parsed.fragment or ''
    full_url = url.lower()

    # Strip port from netloc for hostname
    hostname = netloc.split(':')[0].lower()
    # Remove www. prefix
    domain = re.sub(r'^www\.', '', hostname)

    # Subdomain analysis
    parts = domain.split('.')
    tld      = '.' + parts[-1] if len(parts) > 1 else ''
    sld      = parts[-2] if len(parts) > 1 else ''
    subdomains = parts[:-2] if len(parts) > 2 else []

    # ── URL-level features ─────────────────────────────────────────────────
    features['url_length']          = len(url)
    features['url_entropy']         = round(_entropy(url), 4)
    features['digit_ratio']         = sum(c.isdigit() for c in url) / max(len(url), 1)
    features['special_char_count']  = sum(c in '-_.~!*()@%' for c in url)
    features['dot_count']           = url.count('.')
    features['hyphen_count']        = url.count('-')
    features['slash_count']         = url.count('/')
    features['at_symbol']           = int('@' in url)
    features['double_slash']        = int('//' in path)
    features['hex_encoding']        = int('%' in url)

    # ── Scheme / protocol features ─────────────────────────────────────────
    features['has_https']           = int(scheme == 'https')
    features['has_http']            = int(scheme == 'http')

    # ── Hostname / domain features ─────────────────────────────────────────
    features['hostname_length']     = len(hostname)
    features['subdomain_count']     = len(subdomains)
    features['subdomain_length']    = sum(len(s) for s in subdomains)
    features['domain_length']       = len(sld)
    features['domain_entropy']      = round(_entropy(sld), 4)
    features['ip_address']          = int(bool(
        re.match(r'^\d{1,3}(\.\d{1,3}){3}$', hostname)
    ))
    features['legitimate_tld']      = int(tld in LEGITIMATE_TLDS)
    features['tld_length']          = len(tld)
    features['hyphen_in_domain']    = int('-' in sld)
    features['digit_in_domain']     = int(any(c.isdigit() for c in sld))

    # ── Path features ──────────────────────────────────────────────────────
    features['path_length']         = len(path)
    features['path_depth']          = path.count('/')
    features['file_extension']      = int(bool(
        re.search(r'\.(php|asp|aspx|jsp|cgi|exe|html|htm)$', path.lower())
    ))

    # ── Query / fragment features ──────────────────────────────────────────
    features['has_query']           = int(bool(query))
    features['query_length']        = len(query)
    features['has_fragment']        = int(bool(fragment))

    # ── Semantic / keyword features ────────────────────────────────────────
    features['phishing_keyword']    = int(any(kw in full_url for kw in PHISHING_KEYWORDS))
    features['brand_in_subdomain']  = int(any(
        brand in '.'.join(subdomains).lower() for brand in BRAND_NAMES
    ))

    return features


def features_to_vector(features: dict) -> list:
    """Return feature values as an ordered list (consistent column order)."""
    return list(features.values())


FEATURE_NAMES = list(extract_features('http://example.com').keys())


if __name__ == '__main__':
    # Quick sanity check
    test_urls = [
        'https://www.google.com/search?q=python',
        'http://paypal-secure-login.suspicious-site.xyz/update/verify.php?user=123',
        'http://192.168.1.1/admin',
        'https://github.com/features',
    ]
    for u in test_urls:
        f = extract_features(u)
        print(f"\n{u[:60]}")
        print({k: v for k, v in f.items() if v != 0})
