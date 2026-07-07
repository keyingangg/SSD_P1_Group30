"""Password policy helpers.

Implements the HaveIBeenPwned k-anonymity breach check (NFSR-AU-01). Uses only
the Python standard library so no extra dependency is required.
"""
import hashlib
from urllib.error import URLError
from urllib.request import Request, urlopen

HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/{prefix}"


def is_password_breached(password, *, timeout=3):
    """Return True if the password appears in the HaveIBeenPwned breach corpus.

    Only the first 5 characters of the SHA-1 hash are sent (k-anonymity); the
    full password and full hash never leave this process. Fails open (returns
    False) if the API is unreachable so registration is not blocked by a
    transient network error.
    """
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()  # nosec B324 — SHA-1 required by HIBP k-anonymity protocol
    prefix, suffix = sha1[:5], sha1[5:]

    try:
        request = Request(
            HIBP_RANGE_URL.format(prefix=prefix),
            headers={"User-Agent": "SecureBid-PasswordCheck"},
        )
        with urlopen(request, timeout=timeout) as response:  # nosec B310 — URL is a hardcoded HTTPS constant, not user input
            body = response.read().decode("utf-8")
    except (URLError, TimeoutError, OSError):
        # Fail open: do not block registration on a network failure.
        return False

    for line in body.splitlines():
        candidate, _, _count = line.partition(":")
        if candidate.strip() == suffix:
            return True
    return False
