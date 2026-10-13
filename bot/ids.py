"""Identifiers, URL gate, and path containment. Fail-closed. No I/O."""

from __future__ import annotations

import ipaddress
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse

_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_RUN_ID_RE = re.compile(r"^[0-9a-f]{8,32}$")
_REF_RE = re.compile(r"^@e\d+$")


def new_run_id() -> str:
    return secrets.token_hex(8)


def validate_slug(value: str) -> str:
    clean = (value or "").strip()
    if not clean or ".." in clean or "/" in clean or "\\" in clean:
        raise ValueError("Invalid identifier (path traversal suspected)")
    if not _SLUG_RE.match(clean):
        raise ValueError("Invalid identifier format")
    return clean


def validate_run_id(value: str) -> str:
    clean = (value or "").strip().lower()
    if not _RUN_ID_RE.match(clean):
        raise ValueError("Invalid run_id format")
    return clean


def validate_ref(value: str) -> str:
    clean = (value or "").strip()
    if not _REF_RE.match(clean):
        raise ValueError(f"Invalid element ref '{value}' (expected @eN)")
    return clean


def url_to_slug(url: str) -> str:
    """Host + path slug. Never raises — falls back to 'home'."""
    try:
        parsed = urlparse(url or "")
    except Exception:
        return "home"
    raw_host = (parsed.netloc or "").lower()
    if "@" in raw_host:
        raw_host = raw_host.split("@", 1)[1]
    host_slug = re.sub(r"[^a-z0-9]+", "_", raw_host).strip("_")
    raw_path = (parsed.path or "").strip("/").replace("/", "_")
    path_slug = re.sub(r"[^a-z0-9_-]+", "_", raw_path, flags=re.IGNORECASE).strip("_") or "home"
    path_slug = (path_slug[:64].rstrip("_") or "home") if len(path_slug) > 64 else path_slug
    if not host_slug:
        return path_slug
    host_slug = host_slug[:64].rstrip("_") if len(host_slug) > 64 else host_slug
    return f"{host_slug}__{path_slug}"


def is_blocked_host(host: str) -> bool:
    h = (host or "").strip().lower().split(":")[0]
    if not h:
        return True
    if h in ("localhost", "0.0.0.0"):
        return True
    if h.endswith(".local") or h.endswith(".internal"):
        return True
    try:
        ip = ipaddress.ip_address(h)
        return bool(
            ip.is_loopback or ip.is_private or ip.is_link_local
            or ip.is_multicast or ip.is_reserved or ip.is_unspecified
        )
    except ValueError:
        return False


def assert_safe_url(raw: str, *, allow_private: bool = False) -> str:
    clean = (raw or "").strip()
    if not clean.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    if len(clean) > 2048:
        raise ValueError("URL too long")
    parsed = urlparse(clean)
    if "@" in (parsed.netloc or ""):
        raise ValueError("URL userinfo is not allowed")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL host is missing")
    if is_blocked_host(host) and not allow_private:
        raise ValueError(
            f"URL host '{host}' is blocked (loopback/private/link-local). "
            "Set QA_BOT_ALLOW_PRIVATE_HOSTS=true for local dev."
        )
    return clean


def safe_join(base: Path, *parts: str) -> Path:
    """Join + resolve, raise if the result escapes base. Fail-closed."""
    resolved_base = base.resolve()
    target = resolved_base.joinpath(*parts).resolve()
    if target != resolved_base and resolved_base not in target.parents:
        raise ValueError("Path escapes base directory")
    return target


def relative_ref(base: Path, target: Path) -> str:
    """Run-relative POSIX ref for API/Studio responses. Never leaks abs paths."""
    return str(target.resolve().relative_to(base.resolve()).as_posix())
