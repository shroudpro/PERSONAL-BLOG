from __future__ import annotations

import hashlib
import io
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps

from news_pipeline.media.processor import OUTPUT_QUALITY, OUTPUT_SIZE


_FONT_PATHS = (
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc",
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "simhei.ttf",
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
)
_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _display_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return value[:10]
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_SHANGHAI)
    return parsed.astimezone(_SHANGHAI).strftime("%Y-%m-%d")


def _font(size: int, explicit_path: str | Path | None = None) -> ImageFont.FreeTypeFont:
    candidates = (Path(explicit_path),) if explicit_path else _FONT_PATHS
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    raise RuntimeError("未找到可用的中文字体；请安装或指定思源/微软雅黑字体")


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for character in text.strip():
        candidate = current + character
        if current and draw.textlength(candidate, font=font) > width:
            lines.append(current)
            current = character
            if len(lines) == max_lines:
                break
        else:
            current = candidate
    if len(lines) < max_lines and current:
        lines.append(current)
    if len(lines) == max_lines and "".join(lines) != text.strip():
        lines[-1] = lines[-1].rstrip("。 ，,；;：:") + "…"
    return lines


def render_fallback_cover(
    *,
    title: str,
    source_name: str,
    category: str,
    date: str,
    font_path: str | Path | None = None,
) -> bytes:
    width, height = OUTPUT_SIZE
    gradient = Image.linear_gradient("L").rotate(90).resize(OUTPUT_SIZE)
    background = ImageOps.colorize(gradient, black="#101a32", white="#4755a3").convert("RGBA")
    draw = ImageDraw.Draw(background, "RGBA")
    seed = hashlib.sha256(f"{source_name}|{category}".encode("utf-8")).digest()
    accent = (80 + seed[0] // 2, 100 + seed[1] // 2, 150 + seed[2] // 3, 72)
    draw.ellipse((width - 390, -190, width + 120, 320), fill=accent)
    draw.ellipse((width - 295, 90, width + 45, 430), outline=(255, 255, 255, 46), width=3)
    draw.rounded_rectangle((74, 66, 336, 122), radius=28, fill=(12, 20, 50, 175), outline=(255, 255, 255, 90), width=1)

    label_font = _font(25, font_path)
    source_font = _font(23, font_path)
    title_font = _font(48, font_path)
    meta_font = _font(22, font_path)
    draw.text((98, 79), "PERSONAL-BLOG  /  AI NEWS", font=label_font, fill="#f5f3fa")
    draw.text((76, 160), source_name[:52], font=source_font, fill="#cbd5ff")
    title_lines = _wrap_text(draw, title, title_font, width - 160, 3)
    y = 226
    for line in title_lines:
        draw.text((74, y), line, font=title_font, fill="#ffffff", stroke_width=1, stroke_fill="#ffffff")
        y += 66
    draw.rounded_rectangle((74, 620, 1206, 621), radius=1, fill=(255, 255, 255, 95))
    draw.text((76, 646), category[:30], font=meta_font, fill="#ffffff")
    draw.text((width - 380, 646), _display_date(date), font=meta_font, fill="#e0e5ff")
    output = io.BytesIO()
    background.convert("RGB").save(output, format="WEBP", quality=OUTPUT_QUALITY, method=6, exif=b"")
    return output.getvalue()
