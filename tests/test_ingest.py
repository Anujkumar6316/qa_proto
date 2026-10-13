"""Regression: 'Book 12.xlsx' class — spaces, traversal, abs hints, SSRF."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.ids import assert_safe_url, safe_join, url_to_slug  # noqa: E402
from bot.ingest.files import ingest_upload, sanitize_basename  # noqa: E402
from bot.ingest.urls import assert_public_url, canonicalize_url  # noqa: E402


def test_space_filename_ingests_and_ref_is_relative(tmp_path: Path) -> None:
    out = ingest_upload(b"PK\x03\x04" + b"x" * 64, "Book 12.xlsx", tmp_path / "run1")
    assert out.filename == "Book_12.xlsx"
    assert out.ref == "uploads/Book_12.xlsx"
    assert "/home/" not in out.ref and not Path(out.ref).is_absolute()
    assert out.stored_path.read_bytes().startswith(b"PK\x03\x04")
    assert "spreadsheetml" in out.media_type


def test_absolute_hint_is_name_only_never_opened(tmp_path: Path) -> None:
    out = ingest_upload(b"a,b\n1,2\n", "/home/mindmap/Downloads/Book 12.xlsx", tmp_path / "run2")
    assert out.filename == "Book_12.xlsx"
    assert out.stored_path.parent.name == "uploads"
    assert out.media_type == "text/csv"


def test_traversal_hint_contained(tmp_path: Path) -> None:
    assert sanitize_basename("../../etc/passwd") == "passwd"
    out = ingest_upload(b"hi", "../../etc/passwd", tmp_path / "run3")
    assert out.stored_path.resolve().is_relative_to((tmp_path / "run3").resolve())
    assert out.ref == "uploads/passwd"


def test_safe_join_blocks_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes base"):
        safe_join(tmp_path, "..", "evil.txt")


def test_empty_and_oversize_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Empty upload"):
        ingest_upload(b"", "Book 12.xlsx", tmp_path / "run4")
    with pytest.raises(ValueError, match="too large"):
        ingest_upload(b"x" * 32, "f.bin", tmp_path / "run5", max_bytes=16)


def test_duplicate_names_do_not_collide(tmp_path: Path) -> None:
    run = tmp_path / "run6"
    first = ingest_upload(b"one", "Book 12.xlsx", run)
    second = ingest_upload(b"two", "Book 12.xlsx", run)
    assert first.filename == "Book_12.xlsx"
    assert second.filename == "Book_12_2.xlsx"
    assert second.stored_path.read_bytes() == b"two"


def test_url_gate_blocks_private_and_canonicalizes() -> None:
    assert canonicalize_url("https://Example.COM/a/?utm_x=1&x=2#frag") == "https://example.com/a?x=2"
    with pytest.raises(ValueError, match="blocked"):
        assert_safe_url("http://localhost:3000/x")
    with pytest.raises(ValueError, match="not canonicalizable"):
        assert_public_url("ftp://example.com/x")
    assert assert_public_url("http://127.0.0.1/x", allow_private=True).startswith("http://")


def test_slug_never_raises_and_is_stable() -> None:
    assert url_to_slug("https://example.com/pricing") == "example_com__pricing"
    assert url_to_slug("") == "home"
    assert url_to_slug("not a url") == "not_a_url"
