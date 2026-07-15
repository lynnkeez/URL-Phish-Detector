"""
PhishGuard - Dataset Generator
Generates a realistic synthetic dataset of legitimate and phishing URLs.
In a real deployment you'd replace this with PhiUSIIL / OpenPhish data.
"""

import random
import csv
import os

random.seed(42)

# ── Legitimate URL building blocks ─────────────────────────────────────────
LEGIT_DOMAINS = [
    'google', 'amazon', 'microsoft', 'apple', 'github', 'stackoverflow',
    'wikipedia', 'reddit', 'twitter', 'linkedin', 'netflix', 'spotify',
    'dropbox', 'adobe', 'oracle', 'ibm', 'salesforce', 'zoom', 'slack',
    'stripe', 'twilio', 'cloudflare', 'digitalocean', 'heroku', 'vercel',
    'medium', 'dev', 'hashnode', 'npmjs', 'pypi', 'docker', 'kubernetes',
    'bbc', 'cnn', 'reuters', 'nytimes', 'theguardian', 'techcrunch',
]

LEGIT_TLDS = ['.com', '.org', '.net', '.io', '.gov', '.edu', '.co.uk']

LEGIT_PATHS = [
    '', '/', '/home', '/about', '/contact', '/products', '/services',
    '/blog', '/news', '/docs', '/api', '/login', '/signup', '/pricing',
    '/features', '/support', '/help', '/faq', '/careers', '/press',
    '/search?q=python', '/search?q=machine+learning', '/page/1',
    '/articles/how-to-get-started', '/docs/v2/reference',
]

# ── Phishing URL building blocks ───────────────────────────────────────────
PHISH_BRANDS = [
    'paypal', 'apple', 'amazon', 'google', 'microsoft', 'facebook',
    'netflix', 'instagram', 'twitter', 'chase', 'wellsfargo', 'barclays',
]

PHISH_KEYWORDS = [
    'secure', 'login', 'signin', 'verify', 'update', 'confirm', 'account',
    'banking', 'wallet', 'password', 'credential', 'alert', 'suspended',
]

PHISH_TLDS = [
    '.xyz', '.tk', '.ml', '.ga', '.cf', '.gq', '.top', '.club',
    '.online', '.site', '.website', '.info', '.biz',
]

PHISH_PATHS = [
    '/login.php', '/signin.php', '/verify.php', '/update.php',
    '/confirm.php', '/account/suspend', '/secure/login',
    '/auth/verify?token=abc123&user=victim@email.com',
    '/wp-admin/includes/verify.php',
    '/index.php?cmd=login&session=abcdef123456',
]

RANDOM_STRINGS = [
    'xk92mf', 'a8b3c1', 'zq7lp2', 'mn4rt6', 'jf8sk2', 'pw3xv9',
    '1a2b3c', 'qr5ty8', 'lmno42', 'vwxyz1',
]


def _random_ip():
    return f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def generate_legit_url():
    scheme = random.choice(['https', 'https', 'https', 'http'])  # mostly https
    domain = random.choice(LEGIT_DOMAINS)
    tld    = random.choice(LEGIT_TLDS)
    path   = random.choice(LEGIT_PATHS)
    subdomain = random.choice(['www', 'www', 'www', '', 'blog', 'docs', 'api', 'mail'])
    if subdomain:
        host = f"{subdomain}.{domain}{tld}"
    else:
        host = f"{domain}{tld}"
    return f"{scheme}://{host}{path}"


def generate_phish_url():
    strategy = random.randint(1, 6)

    if strategy == 1:
        # brand-keyword-randomstring.suspicious-tld/phish-path
        brand   = random.choice(PHISH_BRANDS)
        kw      = random.choice(PHISH_KEYWORDS)
        rand    = random.choice(RANDOM_STRINGS)
        tld     = random.choice(PHISH_TLDS)
        path    = random.choice(PHISH_PATHS)
        return f"http://{brand}-{kw}-{rand}{tld}{path}"

    elif strategy == 2:
        # brand as subdomain of random domain
        brand   = random.choice(PHISH_BRANDS)
        kw      = random.choice(PHISH_KEYWORDS)
        rand    = random.choice(RANDOM_STRINGS)
        tld     = random.choice(PHISH_TLDS)
        path    = random.choice(PHISH_PATHS)
        return f"http://{brand}.{kw}-{rand}{tld}{path}"

    elif strategy == 3:
        # IP address directly
        ip      = _random_ip()
        path    = random.choice(PHISH_PATHS)
        return f"http://{ip}{path}"

    elif strategy == 4:
        # very long confusing URL with @ symbol
        brand   = random.choice(PHISH_BRANDS)
        legit   = random.choice(LEGIT_DOMAINS)
        tld     = random.choice(PHISH_TLDS)
        path    = random.choice(PHISH_PATHS)
        return f"http://{legit}.com@{brand}-{random.choice(RANDOM_STRINGS)}{tld}{path}"

    elif strategy == 5:
        # hex encoding / obfuscation
        rand    = random.choice(RANDOM_STRINGS)
        kw      = random.choice(PHISH_KEYWORDS)
        tld     = random.choice(PHISH_TLDS)
        return f"http://{kw}-{rand}{tld}/redirect?url=http%3A%2F%2F{random.choice(PHISH_BRANDS)}.fake{tld}"

    else:
        # deep subdomain chain
        brand   = random.choice(PHISH_BRANDS)
        kw1     = random.choice(PHISH_KEYWORDS)
        kw2     = random.choice(PHISH_KEYWORDS)
        rand    = random.choice(RANDOM_STRINGS)
        tld     = random.choice(PHISH_TLDS)
        path    = random.choice(PHISH_PATHS)
        return f"http://{brand}.{kw1}.{kw2}.{rand}{tld}{path}"


def generate_dataset(n_legit=3000, n_phish=3000, output_path='data/urls.csv'):
    """Generate and save the dataset as a CSV file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rows = []
    for _ in range(n_legit):
        rows.append({'url': generate_legit_url(), 'label': 0})
    for _ in range(n_phish):
        rows.append({'url': generate_phish_url(), 'label': 1})

    random.shuffle(rows)

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'label'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✓] Dataset saved → {output_path}  ({n_legit} legit + {n_phish} phish = {n_legit+n_phish} total)")
    return output_path


if __name__ == '__main__':
    generate_dataset()
