from __future__ import annotations

import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BG      = (10, 12, 20)
PANEL   = (18, 22, 38)
ACCENT  = (111, 76, 255)
ACCENT2 = (64, 196, 255)
WHITE   = (255, 255, 255)
MUTED   = (140, 150, 175)
RULE    = (40, 48, 72)

W, H        = 1050, 600
MARGIN      = 56
PHOTO_SIZE  = 168
PHOTO_X     = W - MARGIN - PHOTO_SIZE
PHOTO_Y     = (H - PHOTO_SIZE) // 2


def _find_font(bold: bool) -> str | None:
    suffix = "-Bold" if bold else ""
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/freefont/FreeSans{'Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/noto/NotoSans-{'Bold' if bold else 'Regular'}.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def _font(size: int, bold: bool = False):
    path = _find_font(bold)
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _circle_crop(img: Image.Image, size: int) -> Image.Image:
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return out


def _initials_avatar(name: str, size: int) -> Image.Image:
    parts = name.split()
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, size, size), fill=ACCENT)
    draw.ellipse((size // 3, size // 3, size, size), fill=(*ACCENT2, 180))
    font = _font(size // 3, bold=True)
    bbox = draw.textbbox((0, 0), initials, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) // 2, (size - th) // 2 - 4), initials, font=font, fill=WHITE)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return out


def _draw_text_fitted(draw, text, x, y, max_w, font, fill):
    while True:
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_w or len(text) <= 1:
            break
        text = text[:-2] + "..."
    draw.text((x, y), text, font=font, fill=fill)
    return y + (bbox[3] - bbox[1])


def _gradient_rect(draw, x0, y0, x1, y1, color_left, color_right):
    width = x1 - x0
    for i in range(width):
        t = i / max(width - 1, 1)
        r = int(color_left[0] + t * (color_right[0] - color_left[0]))
        g = int(color_left[1] + t * (color_right[1] - color_left[1]))
        b = int(color_left[2] + t * (color_right[2] - color_left[2]))
        draw.line([(x0 + i, y0), (x0 + i, y1)], fill=(r, g, b))


def generate_business_card(data: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img, "RGBA")

    draw.rounded_rectangle(
        [(MARGIN // 2, MARGIN // 2), (W - MARGIN // 2, H - MARGIN // 2)],
        radius=24, fill=PANEL,
    )

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for r_offset, alpha in [(260, 18), (180, 30), (100, 50)]:
        glow_draw.ellipse(
            (MARGIN - r_offset, MARGIN // 2 - r_offset,
             MARGIN + r_offset, MARGIN // 2 + r_offset),
            fill=(*ACCENT, alpha),
        )
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    _gradient_rect(draw, MARGIN // 2, MARGIN // 2, W - MARGIN // 2, MARGIN // 2 + 4,
                   ACCENT, ACCENT2)

    draw.rectangle(
        [(MARGIN // 2, MARGIN // 2), (MARGIN // 2 + 4, H - MARGIN // 2)],
        fill=ACCENT,
    )

    sep_x = PHOTO_X - 50
    draw.rectangle([(sep_x, MARGIN + 20), (sep_x + 1, H - MARGIN - 20)], fill=RULE)

    photo_bytes = data.get("photo")
    name_str = data.get("name", "U")
    if photo_bytes:
        avatar = _circle_crop(Image.open(io.BytesIO(photo_bytes)), PHOTO_SIZE)
    else:
        avatar = _initials_avatar(name_str, PHOTO_SIZE)

    ring_size = PHOTO_SIZE + 16
    ring = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, ring_size, ring_size), fill=(*ACCENT, 160))
    img.paste(ring.convert("RGB"), (PHOTO_X - 8, PHOTO_Y - 8), ring)

    border_size = PHOTO_SIZE + 6
    border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
    ImageDraw.Draw(border).ellipse((0, 0, border_size, border_size), fill=(*WHITE, 220))
    img.paste(border.convert("RGB"), (PHOTO_X - 3, PHOTO_Y - 3), border)

    img.paste(avatar.convert("RGB"), (PHOTO_X, PHOTO_Y), avatar)
    draw = ImageDraw.Draw(img, "RGBA")

    text_x = MARGIN + 20
    text_max_w = sep_x - text_x - 20
    y = MARGIN + 30

    company = data.get("company", "")
    if company:
        font_co = _font(18)
        _gradient_rect(draw, text_x, y + 4, text_x + 6, y + 22, ACCENT, ACCENT2)
        draw.text((text_x + 14, y), company.upper(), font=font_co, fill=(*ACCENT2, 220))
        y += 38

    font_name = _font(52, bold=True)
    _draw_text_fitted(draw, name_str, text_x, y, text_max_w, font_name, WHITE)
    y += 68

    title = data.get("title", "")
    if title:
        font_title = _font(26)
        _draw_text_fitted(draw, title, text_x, y, text_max_w, font_title, MUTED)
        y += 42

    _gradient_rect(draw, text_x, y, text_x + 220, y + 2, ACCENT, ACCENT2)
    y += 22

    font_info = _font(20)
    font_label = _font(16)

    def _row(icon, value):
        nonlocal y
        if not value:
            return
        draw.rounded_rectangle([(text_x, y + 2), (text_x + 24, y + 22)],
                                radius=4, fill=(*ACCENT, 120))
        draw.text((text_x + 4, y + 1), icon, font=_font(14, bold=True), fill=WHITE)
        _draw_text_fitted(draw, value, text_x + 32, y, text_max_w - 32, font_info, WHITE)
        y += 32

    _row("T", data.get("phone", ""))
    _row("@", data.get("email", ""))
    _row("W", data.get("website", ""))

    social_raw = data.get("social") or ""
    social_lines = [l.strip() for l in social_raw.splitlines() if l.strip()][:3]
    if social_lines:
        y += 6
        for line in social_lines:
            draw.text((text_x + 2, y), ">", font=_font(18, bold=True), fill=(*ACCENT2, 200))
            _draw_text_fitted(draw, line, text_x + 18, y, text_max_w - 18, font_label, MUTED)
            y += 26

    font_wm = _font(14)
    wm = "Business Card Bot"
    bbox = draw.textbbox((0, 0), wm, font=font_wm)
    draw.text(
        (W - MARGIN // 2 - (bbox[2] - bbox[0]) - 10, H - MARGIN // 2 - 28),
        wm, font=font_wm, fill=(*MUTED, 80),
    )

    return img.convert("RGB")
