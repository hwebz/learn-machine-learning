from __future__ import annotations

from pathlib import Path

import pytest

from app.browser.media import image_extension, resolve_image, save_image

PNG = b"\x89PNG\r\n\x1a\n" + b"rest" * 4
JPEG = b"\xff\xd8\xff\xe0" + b"rest" * 4
GIF = b"GIF89a" + b"rest" * 4
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"rest" * 4


def test_image_extension_accepts_raster_signatures() -> None:
    assert image_extension(PNG) == "png"
    assert image_extension(JPEG) == "jpg"
    assert image_extension(GIF) == "gif"
    assert image_extension(WEBP) == "webp"
    with pytest.raises(ValueError):
        image_extension(b"<html>")


def test_save_image_rejects_type_mismatch(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        save_image(PNG, "image/jpeg", tmp_path)
    with pytest.raises(ValueError):
        save_image(b"", "image/png", tmp_path)


def test_save_image_stores_unique_files(tmp_path: Path) -> None:
    first = save_image(PNG, "image/png", tmp_path)
    second = save_image(PNG, "image/png", tmp_path)
    assert first != second and first.endswith(".png")
    assert (tmp_path / first).read_bytes() == PNG
    assert list(tmp_path.glob(".*")) == []


def test_resolve_image_roundtrip(tmp_path: Path) -> None:
    filename = save_image(JPEG, "image/jpeg", tmp_path)
    path, media_type = resolve_image(tmp_path, filename)
    assert media_type == "image/jpeg" and path.read_bytes() == JPEG


def test_resolve_image_rejects_bad_names(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_image(tmp_path, "../secret.png")
    with pytest.raises(FileNotFoundError):
        resolve_image(tmp_path, "abc.png")
    with pytest.raises(FileNotFoundError):
        resolve_image(tmp_path, f"{'a' * 32}.png")
    (tmp_path / f"{'b' * 32}.png").write_text("<svg/>")
    with pytest.raises(ValueError):
        resolve_image(tmp_path, f"{'b' * 32}.png")
