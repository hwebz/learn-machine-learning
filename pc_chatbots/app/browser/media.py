from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import uuid4

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGES = 8
MEDIA_FILENAME = re.compile(r"[0-9a-f]{32}\.(?:png|jpg|webp|gif)\Z")
IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}


def image_extension(data: bytes) -> str:
    """Accept raster signatures only; never serve HTML or SVG as generated media."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:6] in {b"GIF87a", b"GIF89a"}:
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    raise ValueError("Generated image is not a supported raster image")


def save_image(data: bytes, content_type: str, directory: Path) -> str:
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Generated image is empty or exceeds the 20 MiB limit")
    extension = image_extension(data)
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime != IMAGE_TYPES[extension]:
        raise ValueError("Generated image content type does not match its bytes")
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    temporary = directory / f".{filename}.tmp"
    try:
        with temporary.open("xb") as output:
            output.write(data)
        os.replace(temporary, directory / filename)
    finally:
        temporary.unlink(missing_ok=True)
    return filename


def resolve_image(directory: Path, filename: str) -> tuple[Path, str]:
    if not MEDIA_FILENAME.fullmatch(filename):
        raise FileNotFoundError(filename)
    root = directory.resolve()
    path = root / filename
    if path.is_symlink() or not path.is_file() or path.resolve().parent != root:
        raise FileNotFoundError(filename)
    extension = path.suffix[1:]
    with path.open("rb") as source:
        if image_extension(source.read(16)) != extension:
            raise ValueError("Stored media is not a matching raster image")
    return path, IMAGE_TYPES[extension]
