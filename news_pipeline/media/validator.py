from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from posixpath import normpath
from urllib.parse import unquote, urlsplit

import yaml
from PIL import Image, UnidentifiedImageError

from news_pipeline.core.normalize import normalize_url
from news_pipeline.media.models import ImageCandidate, ImagePermission


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}


@dataclass(frozen=True)
class ImageDetails:
    format: str
    width: int
    height: int


def _https_url(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a URL")
    normalized = normalize_url(value)
    if urlsplit(normalized).scheme != "https":
        raise ValueError(f"{field_name} must use HTTPS")
    return normalized


def load_image_permissions(path: str | Path) -> tuple[ImagePermission, ...]:
    config_path = Path(path)
    if not config_path.exists():
        return ()
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not read image reuse permissions: {config_path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("approved_assets", []), list):
        raise ValueError("image reuse config must contain an approved_assets list")

    permissions: list[ImagePermission] = []
    for index, entry in enumerate(payload.get("approved_assets", []), start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"approved_assets[{index}] must be a mapping")
        source_id = entry.get("source_id")
        reuse_basis = entry.get("reuse_basis")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError(f"approved_assets[{index}].source_id is required")
        if not isinstance(reuse_basis, str) or not reuse_basis.strip():
            raise ValueError(f"approved_assets[{index}].reuse_basis is required")
        source_page = _https_url(entry.get("source_page"), f"approved_assets[{index}].source_page")
        evidence_url = _https_url(entry.get("evidence_url"), f"approved_assets[{index}].evidence_url")
        raw_prefix = entry.get("asset_url_prefix")
        if not isinstance(raw_prefix, str):
            raise ValueError(f"approved_assets[{index}].asset_url_prefix is required")
        prefix = urlsplit(raw_prefix)
        if prefix.scheme != "https" or not prefix.hostname or prefix.query or prefix.fragment:
            raise ValueError(f"approved_assets[{index}].asset_url_prefix must be an HTTPS URL prefix")
        if prefix.username is not None or prefix.password is not None:
            raise ValueError(f"approved_assets[{index}].asset_url_prefix cannot contain credentials")
        normalized_prefix = f"https://{prefix.netloc.casefold()}{prefix.path or '/'}"
        permissions.append(
            ImagePermission(source_id.strip(), source_page, normalized_prefix, reuse_basis.strip(), evidence_url)
        )
    return tuple(permissions)


def _prefix_matches(url: str, prefix: str) -> bool:
    candidate = urlsplit(url)
    allowed = urlsplit(prefix)
    if candidate.scheme != "https" or candidate.hostname != allowed.hostname or candidate.port != allowed.port:
        return False
    candidate_path = normpath(unquote(candidate.path))
    prefix_path = normpath(unquote(allowed.path))
    return candidate_path == prefix_path or candidate_path.startswith(prefix_path.rstrip("/") + "/")


def permission_for(
    candidate: ImageCandidate,
    source_id: str,
    permissions: tuple[ImagePermission, ...] | list[ImagePermission],
) -> ImagePermission | None:
    try:
        candidate_page = normalize_url(candidate.source_page)
        candidate_url = normalize_url(candidate.url)
    except ValueError:
        return None
    for permission in permissions:
        if (
            permission.source_id == source_id
            and normalize_url(permission.source_page) == candidate_page
            and _prefix_matches(candidate_url, permission.asset_url_prefix)
        ):
            return permission
    return None


def validate_image_bytes(
    payload: bytes,
    content_type: str,
    *,
    max_bytes: int = MAX_IMAGE_BYTES,
) -> ImageDetails:
    mime_type = content_type.split(";", 1)[0].strip().casefold()
    if mime_type not in _CONTENT_TYPES:
        raise ValueError(f"Unsupported image Content-Type: {content_type}")
    if not payload or len(payload) > max_bytes:
        raise ValueError(f"Image size must be between 1 and {max_bytes} bytes")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image_format = image.format
            width, height = image.size
            if image_format not in _PIL_FORMATS:
                raise ValueError(f"Unsupported image format: {image_format}")
            if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions are invalid or exceed the pixel limit")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Response body is not a valid raster image") from exc
    expected_format = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}[mime_type]
    if image_format != expected_format:
        raise ValueError("Image bytes do not match Content-Type")
    return ImageDetails(image_format, width, height)
