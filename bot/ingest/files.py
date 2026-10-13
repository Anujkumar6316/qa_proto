"""Upload intake — bytes in, run-relative ref out. Never opens a host path."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from bot.ids import relative_ref, safe_join

_SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_BASENAME_LEN = 128

_MAGIC: tuple[tuple[bytes, str, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"PK\x03\x04", "application/zip", ".zip"),
    (b"%PDF", "application/pdf", ".pdf"),
    (b"\x1f\x8b", "application/gzip", ".gz"),
    (b"GIF87a", "image/gif", ".gif"),
    (b"GIF89a", "image/gif", ".gif"),
)


@dataclass(frozen=True)
class IngestedFile:
    stored_path: Path
    ref: str
    filename: str
    size_bytes: int
    media_type: str
    sha256: str


def sanitize_basename(hint: str, fallback: str = "upload.bin") -> str:
    name = Path(hint or "").name.strip()
    if not name or name in (".", ".."):
        name = fallback
    name = name.replace(" ", "_")
    name = _SAFE_CHARS_RE.sub("_", name).strip("._")
    if not name:
        name = fallback
    if len(name) > _MAX_BASENAME_LEN:
        stem, dot, ext = name.rpartition(".")
        ext = f".{ext}" if dot else ""
        keep = _MAX_BASENAME_LEN - len(ext)
        name = (stem[:keep] or "upload") + ext
    if name in (".", ".."):
        name = fallback
    return name

def sniff_media(data: bytes, filename: str) -> str:
    for magic, media, _ext in _MAGIC:
        if data.startswith(magic):
            if media == "application/zip":
                lower = filename.lower()
                if lower.endswith((".xlsx", ".xlsm", ".xltx")):
                    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if lower.endswith(".docx"):
                    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            return media
    try:
        head = bytes(data[:4096]).decode("utf-8-sig").lstrip()
    except UnicodeDecodeError:
        return "application/octet-stream"
    if head.startswith(("{", "[")):
        return "application/json"
    if ("," in head[:2000] or "\t" in head[:2000]) and ("\n" in head or "\r" in head):
        return "text/csv"
    if head:
        return "text/plain"
    return "application/octet-stream"


def _unique_path(uploads_dir: Path, basename: str) -> Path:
    candidate = uploads_dir / basename
    if not candidate.exists():
        return candidate
    stem, dot, ext = basename.rpartition(".")
    if not dot:
        stem, ext = basename, ""
    else:
        ext = f".{ext}"
    for i in range(2, 1000):
        alt = uploads_dir / f"{stem}_{i}{ext}"
        if not alt.exists():
            return alt
    raise ValueError("Too many colliding uploads with the same name")


def ingest_upload(data: bytes, filename_hint: str, run_dir: Path, *, max_bytes: int = 10485760) -> IngestedFile:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes (read the file before calling ingest)")
    if not isinstance(filename_hint, str):
        raise TypeError("filename_hint must be str")
    if isinstance(run_dir, str):
        run_dir = Path(run_dir)
    if not isinstance(run_dir, Path):
        raise TypeError("run_dir must be a Path")
    payload = bytes(data)
    if not payload:
        raise ValueError("Empty upload rejected")
    if len(payload) > max_bytes:
        raise ValueError(f"Upload too large ({len(payload)} > {max_bytes} bytes)")
    run_dir.mkdir(parents=True, exist_ok=True)
    resolved_run = run_dir.resolve()
    uploads_dir = safe_join(resolved_run, "uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    basename = sanitize_basename(filename_hint)
    dest = _unique_path(uploads_dir, basename)
    dest = safe_join(resolved_run, "uploads", dest.name)
    digest = hashlib.sha256(payload).hexdigest()
    dest.write_bytes(payload)
    media = sniff_media(payload, basename)
    ref = relative_ref(resolved_run, dest)
    return IngestedFile(stored_path=dest, ref=ref, filename=dest.name,
                        size_bytes=len(payload), media_type=media, sha256=digest)
