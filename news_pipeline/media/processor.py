from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from news_pipeline.media.validator import MAX_IMAGE_PIXELS


OUTPUT_SIZE = (1280, 720)
OUTPUT_QUALITY = 85


def process_image_bytes(payload: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(payload)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError(f"Unsupported image format: {source.format}")
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise ValueError("Image exceeds the pixel limit")
            oriented = ImageOps.exif_transpose(source)
            rgba = oriented.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (245, 243, 250, 255))
            background.alpha_composite(rgba)
            fitted = ImageOps.fit(background.convert("RGB"), OUTPUT_SIZE, method=Image.Resampling.LANCZOS)
            output = io.BytesIO()
            fitted.save(output, format="WEBP", quality=OUTPUT_QUALITY, method=6, exif=b"")
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Could not decode image bytes") from exc
