"""Identifiers, URL gate, and path containment. Fail-closed.

Pure by default (no I/O). The only network-touching helper is
`resolve_host_addresses`, used by `assert_safe_url` to close the
DNS-rebinding SSRF gap; it can be disabled via `QA_BOT_RESOLVE_HOSTS=false`.
"""

from __future__ import annotations

import ipaddress
import re
import secrets
import socket
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


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_loopback or ip.is_private or ip.is_link_local
        or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    )


def resolve_host_addresses(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve a hostname to every address it maps to (A + AAAA).

    Raises ValueError if resolution fails — callers must fail closed.
    """
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    addrs: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        addr = info[4][0]
        stripped = addr.split("%")[0]  # IPv6 link-local zone id (e.g. fe80::1%eth0)
        try:
            ip = ipaddress.ip_address(stripped)
        except ValueError:
            continue
        if ip not in addrs:
            addrs.append(ip)
    if not addrs:
        raise ValueError(f"No addresses found for host '{host}'")
    return addrs


def hosts_check_enabled() -> bool:
    """DNS-resolution leg of the SSRF gate; on by default (fail-closed)."""
    from bot.settings import get_settings

    return get_settings().RESOLVE_HOSTS


def is_blocked_host(host: str) -> bool:
    """Lexical + IP-literal blocklist. Does NOT perform DNS lookups."""
    h = (host or "").strip().lower().rstrip(".").split(":")[0]
    if not h:
        return True
    if h in ("localhost", "0.0.0.0") or "." not in h:  # bare hostnames default to loopback risk
        return h == "localhost" or "." not in h
    if h.endswith((".local", ".internal", ".home.arpa")):
        return True
    try:
        return _ip_is_blocked(ipaddress.ip_address(h))
    except ValueError:
        return False


def assert_safe_url(raw: str, *, allow_private: bool = False) -> str:
    """Validate a URL against the SSRF gate. Fail-closed.

    Beyond the lexical/IP-literal checks, hostnames are resolved via DNS and
    EVERY returned address must be public — this closes the DNS-rebinding gap
    where an allowlisted-looking domain resolves to 127.0.0.1 / 169.254.169.254.
    Set QA_BOT_RESOLVE_HOSTS=false (or allow_private=True) to skip resolution.
    """
    clean = (raw or "").strip()
    if not clean.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    if len(clean) > 2048:
        raise ValueError("URL too long")
    parsed = urlparse(clean)
    if "@" in (parsed.netloc or ""):
        raise ValueError("URL userinfo is not allowed")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("URL host is missing")
    if is_blocked_host(host) and not allow_private:
        raise ValueError(
            f"URL host '{host}' is blocked (loopback/private/link-local). "
            "Set QA_BOT_ALLOW_PRIVATE_HOSTS=true for local dev."
        )
    if not allow_private and hosts_check_enabled():
        try:
            addrs = resolve_host_addresses(host)
        except ValueError as exc:
            raise ValueError(f"URL host '{host}' cannot be resolved safely: {exc}") from exc
        for ip in addrs:
            if _ip_is_blocked(ip):
                raise ValueError(
                    f"URL host '{host}' resolves to blocked address {ip} "
                    "(possible DNS rebinding to loopback/private space)."
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
