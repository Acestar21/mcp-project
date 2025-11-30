import re
from urllib.parse import urlparse

# Blocked TLDs (common malicious domains)
BLOCKED_TLDS = {
    "zip", "mov", "xyz", "top", "club", "info",
    "cyou", "tech", "click", "work", "rest", "kim"
}

# URL shorteners (hides destination)
SHORTENERS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co",
    "is.gd", "cutt.ly", "shorturl.at"
}

# Dangerous file extensions
DANGEROUS_EXT = {
    ".exe", ".msi", ".apk", ".bat", ".cmd", ".ps1",
    ".js", ".jar", ".zip", ".rar", ".7z", ".dmg", ".pkg"
}


def validate_url(url: str) -> tuple[bool, str]:
    """
    Validates a URL before allowing the browser to open it.
    Returns (True, url) if safe, or (False, reason) if blocked.
    """

    url = url.strip()

    # Must be HTTPS (no plain http allowed)
    if not url.startswith("https://"):
        return False, "Only HTTPS URLs are allowed."

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Block URL shorteners
    if domain in SHORTENERS:
        return False, f"Blocked shortened URL: {domain}"

    # Block dangerous TLDs
    tld = domain.split(".")[-1]
    if tld in BLOCKED_TLDS:
        return False, f"Domain TLD '.{tld}' is not allowed."

    # Block long suspicious URLs
    if len(url) > 2048:
        return False, "URL too long (possible phishing or tracking link)."

    # Block dangerous downloads
    for ext in DANGEROUS_EXT:
        if parsed.path.lower().endswith(ext):
            return False, f"Blocked file download attempt: {ext}"

    # Detect suspicious Unicode (homograph attacks)
    if re.search(r"[^\x00-\x7F]", url):
        return False, "URL contains suspicious Unicode characters."

    return True, url
