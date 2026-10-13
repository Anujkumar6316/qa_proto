"""URL intake — canonicalize + SSRF gate. Pure, no network."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from bot.ids import assert_safe_url

_TRACKING = frozenset({"fbclid", "gclid", "ref", "source"})


def canonicalize_url(url: str, base_url: str = "") -> str | None:
    try:
        full = urljoin(base_url, url) if base_url else (url or "")
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            return None
        netloc = parsed.netloc.lower()
        params = sorted(
            (k, v)
            for k, v in parse_qs(parsed.query).items()
            if not k.startswith("utm_") and k not in _TRACKING
        )
        query = urlencode(params, doseq=True)
        path = parsed.path.rstrip("/") or "/"
        return urlunparse((parsed.scheme.lower(), netloc, path, "", query, ""))
    except Exception:
        return None


def assert_public_url(raw: str, *, allow_private: bool = False) -> str:
    clean = canonicalize_url(raw or "")
    if not clean:
        raise ValueError("URL is not canonicalizable")
    return assert_safe_url(clean, allow_private=allow_private)
