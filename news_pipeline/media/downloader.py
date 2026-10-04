from __future__ import annotations

from requests import RequestException

from news_pipeline.core.fetch import HttpFetcher
from news_pipeline.media.validator import MAX_IMAGE_BYTES, validate_image_bytes


def download_image(
    fetcher: HttpFetcher,
    url: str,
    *,
    allowed_domains: tuple[str, ...],
    allowed_url_prefixes: tuple[str, ...] = (),
    max_bytes: int = MAX_IMAGE_BYTES,
) -> tuple[bytes, str]:
    """Download one permitted image and validate both headers and image bytes."""
    response = fetcher.get(
        url,
        allowed_domains=allowed_domains,
        allowed_url_prefixes=allowed_url_prefixes,
        stream=True,
    )
    try:
        if getattr(response, "status_code", 200) != 200:
            raise ValueError(f"Image download expected HTTP 200, got {response.status_code}")
        content_type = response.headers.get("Content-Type", "")
        declared_size = response.headers.get("Content-Length")
        if declared_size:
            try:
                if int(declared_size) > max_bytes:
                    raise ValueError(f"Image size exceeds {max_bytes} bytes")
            except ValueError as exc:
                if str(exc).startswith("Image size"):
                    raise
                raise ValueError("Invalid image Content-Length") from exc

        chunks: list[bytes] = []
        total = 0
        try:
            try:
                iterator = response.iter_content(chunk_size=64 * 1024)
            except AttributeError:
                iterator = (response.content,)
            for chunk in iterator:
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"Image size exceeds {max_bytes} bytes")
                chunks.append(chunk)
        except RequestException as exc:
            raise ValueError("Image download stream failed") from exc
        payload = b"".join(chunks)
        validate_image_bytes(payload, content_type, max_bytes=max_bytes)
        return payload, content_type
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
