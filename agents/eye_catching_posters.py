"""
Eye-Catching Photo Posters for Mangalya Matrimony.
Uses real Pexels images + professional overlays + bold typography + logo.

Poster Types:
1. Full-Bleed Photo — Big photo, gradient overlay, bold text
2. Split Design — Photo on one side, text on other
3. Photo with Bottom Panel — Photo top 60%, branded text bottom
4. Quote on Photo — Full photo with centered overlay text
5. Testimonial Style — Couple photo with quote bubble
6. Bold Statement — Large bold text with small photo strip
"""

import io
import os
import random
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

PEXELS_KEY = os.getenv("PEXELS_API_KEY")
LOGO_PATH = r"C:\Users\ambav\Desktop\Matrimony\Logo.jpg"

# Brand colors
ORANGE = (245, 146, 27)
RED = (232, 66, 30)
DARK = (35, 35, 35)
WHITE = (255, 255, 255)
CREAM = (255, 248, 240)

FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REGULAR = r"C:\Windows\Fonts\arial.ttf"
FONT_ITALIC = r"C:\Windows\Fonts\ariali.ttf"

SIZE = 1080


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()


def _centered_x(draw, text, font, w):
    bbox = draw.textbbox((0, 0), text, font=font)
    return (w - (bbox[2] - bbox[0])) // 2


def _wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _load_logo(max_height=70):
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        data = list(logo.getdata())
        new_data = [(255, 255, 255, 0) if (p[0] > 230 and p[1] > 230 and p[2] > 230) else p for p in data]
        logo.putdata(new_data)
        ratio = max_height / logo.height
        return logo.resize((int(logo.width * ratio), max_height), Image.LANCZOS)
    except:
        return None


def _fetch_photo(query, orientation="square"):
    """Fetch a high-quality photo from Pexels."""
    for page in [random.randint(1, 3), 1]:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": 10, "page": page, "orientation": orientation},
            timeout=15,
        )
        photos = resp.json().get("photos", [])
        if photos:
            url = random.choice(photos)["src"]["large2x"]
            img_resp = requests.get(url, timeout=20)
            img_resp.raise_for_status()
            return Image.open(io.BytesIO(img_resp.content)).convert("RGBA")
    return None


def _draw_orange_corner_brackets(draw, x1, y1, x2, y2, arm=40, thickness=3):
    """Draw decorative L-shaped orange corner brackets around a rectangle."""
    c = ORANGE
    # Top-left
    draw.rectangle([(x1, y1), (x1 + arm, y1 + thickness)], fill=c)
    draw.rectangle([(x1, y1), (x1 + thickness, y1 + arm)], fill=c)
    # Top-right
    draw.rectangle([(x2 - arm, y1), (x2, y1 + thickness)], fill=c)
    draw.rectangle([(x2 - thickness, y1), (x2, y1 + arm)], fill=c)
    # Bottom-left
    draw.rectangle([(x1, y2 - thickness), (x1 + arm, y2)], fill=c)
    draw.rectangle([(x1, y2 - arm), (x1 + thickness, y2)], fill=c)
    # Bottom-right
    draw.rectangle([(x2 - arm, y2 - thickness), (x2, y2)], fill=c)
    draw.rectangle([(x2 - thickness, y2 - arm), (x2, y2)], fill=c)


def _paste_logo_on_white_pad(img, x, y, max_h=55):
    """Paste logo with white pad for visibility."""
    logo = _load_logo(max_h)
    if not logo:
        return
    pad = Image.new("RGBA", (logo.width + 20, logo.height + 10), (255, 255, 255, 210))
    img.paste(pad, (x - 10, y - 5), pad)
    img.paste(logo, (x, y), logo)


def _paste_logo_bottom_center(img, y_offset=30, max_h=60):
    """Paste logo centered at bottom."""
    logo = _load_logo(max_h)
    if not logo:
        return
    x = (img.width - logo.width) // 2
    y = img.height - logo.height - y_offset
    pad = Image.new("RGBA", (logo.width + 24, logo.height + 14), (255, 255, 255, 220))
    img.paste(pad, (x - 12, y - 7), pad)
    img.paste(logo, (x, y), logo)


def _draw_gradient_overlay(img, direction="bottom", color=(0, 0, 0), max_alpha=200, coverage=0.55):
    """Draw gradient overlay on image."""
    w, h = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if direction == "bottom":
        start_y = int(h * (1 - coverage))
        for y in range(start_y, h):
            progress = (y - start_y) / (h - start_y)
            alpha = int(max_alpha * (progress ** 1.3))
            draw.rectangle([(0, y), (w, y + 1)], fill=(*color, alpha))
    elif direction == "top":
        end_y = int(h * coverage)
        for y in range(0, end_y):
            progress = 1 - (y / end_y)
            alpha = int(max_alpha * (progress ** 1.3))
            draw.rectangle([(0, y), (w, y + 1)], fill=(*color, alpha))
    elif direction == "full":
        for y in range(h):
            draw.rectangle([(0, y), (w, y + 1)], fill=(*color, int(max_alpha * 0.5)))
    elif direction == "left":
        end_x = int(w * coverage)
        for x in range(0, end_x):
            progress = 1 - (x / end_x)
            alpha = int(max_alpha * (progress ** 1.2))
            draw.rectangle([(x, 0), (x + 1, h)], fill=(*color, alpha))

    return Image.alpha_composite(img, overlay)


# ═══════════════════════════════════════════════════════════════════════════
# POSTER 1: Full-Bleed Photo with Bottom Gradient + Bold Text
# ═══════════════════════════════════════════════════════════════════════════

def poster_full_bleed(photo_query, headline, subtext, save_path=None):
    """Full photo background with gradient overlay and bold text at bottom."""
    photo = _fetch_photo(photo_query)
    if not photo:
        return None

    # Crop to square
    img = photo.resize((SIZE, SIZE), Image.LANCZOS)

    # Slight warm color enhancement
    enhancer = ImageEnhance.Color(img.convert("RGB"))
    img = enhancer.enhance(1.15).convert("RGBA")

    # Dark gradient from bottom (taller coverage for more text room)
    img = _draw_gradient_overlay(img, "bottom", (20, 10, 5), max_alpha=230, coverage=0.7)

    draw = ImageDraw.Draw(img)

    # Headline — large bold white
    font_h = _font(FONT_BOLD, 64)
    h_lines = _wrap_text(headline, font_h, SIZE - 100, draw)
    y = SIZE - 120 - (len(h_lines) * 76) - 80

    # Thin orange line above headline for visual separation
    draw.rectangle([(SIZE // 2 - 80, y - 15), (SIZE // 2 + 80, y - 12)], fill=ORANGE)

    for line in h_lines:
        lx = _centered_x(draw, line, font_h, SIZE)
        draw.text((lx + 2, y + 2), line, font=font_h, fill=(0, 0, 0, 150))
        draw.text((lx, y), line, font=font_h, fill=WHITE)
        y += 76

    # Subtext — smaller orange
    font_s = _font(FONT_REGULAR, 28)
    s_lines = _wrap_text(subtext, font_s, SIZE - 120, draw)
    y += 15
    for line in s_lines:
        sx = _centered_x(draw, line, font_s, SIZE)
        draw.text((sx, y), line, font=font_s, fill=ORANGE)
        y += 38

    # URL
    font_url = _font(FONT_REGULAR, 22)
    ux = _centered_x(draw, "mangalyamatrimony.com", font_url, SIZE)
    draw.text((ux, SIZE - 45), "mangalyamatrimony.com", font=font_url, fill=(255, 255, 255, 180))

    # Logo top-left
    _paste_logo_on_white_pad(img, 25, 20, max_h=45)

    # Orange accent line
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (SIZE, 5)], fill=ORANGE)

    return _save(img, save_path)


# ═══════════════════════════════════════════════════════════════════════════
# POSTER 2: Split Design — Photo Left, Text Right
# ═══════════════════════════════════════════════════════════════════════════

def poster_split(photo_query, headline, body_text, save_path=None):
    """Photo on left half, branded text on right half."""
    photo = _fetch_photo(photo_query, "portrait")
    if not photo:
        return None

    img = Image.new("RGBA", (SIZE, SIZE), CREAM)

    # Photo on left 50%
    half_w = SIZE // 2
    photo_resized = photo.resize((half_w, SIZE), Image.LANCZOS)
    img.paste(photo_resized, (0, 0))

    # Subtle cream/warm tint on right panel
    warm_tint = Image.new("RGBA", (SIZE - half_w, SIZE), (255, 243, 224, 35))
    img.paste(Image.alpha_composite(
        img.crop((half_w, 0, SIZE, SIZE)),
        warm_tint
    ), (half_w, 0))

    # Orange divider line
    draw = ImageDraw.Draw(img)
    draw.rectangle([(half_w, 0), (half_w + 5, SIZE)], fill=ORANGE)

    # Right side — text area
    text_x = half_w + 40
    max_text_w = SIZE - text_x - 40

    # Orange accent bar at top
    draw.rectangle([(half_w + 5, 0), (SIZE, 55)], fill=ORANGE)

    # Logo on right panel
    _paste_logo_on_white_pad(img, half_w + 30, 70, max_h=50)
    draw = ImageDraw.Draw(img)

    # Headline
    font_h = _font(FONT_BOLD, 38)
    h_lines = _wrap_text(headline, font_h, max_text_w, draw)
    y = 160
    for line in h_lines:
        draw.text((text_x, y), line, font=font_h, fill=DARK)
        y += 50

    # Orange separator
    y += 15
    draw.rectangle([(text_x, y), (text_x + 100, y + 4)], fill=ORANGE)
    y += 30

    # Body text
    font_b = _font(FONT_REGULAR, 26)
    b_lines = _wrap_text(body_text, font_b, max_text_w, draw)
    for line in b_lines:
        draw.text((text_x, y), line, font=font_b, fill=(80, 80, 80))
        y += 38

    # Small decorative orange corner bracket at top-right of text area
    tr_x = SIZE - 30
    tr_y = 70
    bracket_arm = 30
    bracket_t = 3
    draw.rectangle([(tr_x - bracket_arm, tr_y), (tr_x, tr_y + bracket_t)], fill=ORANGE)
    draw.rectangle([(tr_x - bracket_t, tr_y), (tr_x, tr_y + bracket_arm)], fill=ORANGE)

    # URL at bottom right
    font_url = _font(FONT_REGULAR, 20)
    draw.text((text_x, SIZE - 50), "mangalyamatrimony.com", font=font_url, fill=ORANGE)

    return _save(img, save_path)


# ═══════════════════════════════════════════════════════════════════════════
# POSTER 3: Photo Top + Branded Panel Bottom
# ═══════════════════════════════════════════════════════════════════════════

def poster_photo_panel(photo_query, headline, subtext, save_path=None):
    """Photo takes top 60%, branded text panel at bottom."""
    photo = _fetch_photo(photo_query)
    if not photo:
        return None

    img = Image.new("RGBA", (SIZE, SIZE), WHITE)

    # Photo in top 65%
    photo_h = int(SIZE * 0.65)
    photo_resized = photo.resize((SIZE, photo_h), Image.LANCZOS)
    img.paste(photo_resized, (0, 0))

    # Subtle drop shadow between photo and panel
    draw = ImageDraw.Draw(img)
    for i in range(8):
        alpha = int(60 * (1 - i / 8))
        draw.rectangle([(0, photo_h + i), (SIZE, photo_h + i + 1)], fill=(0, 0, 0, alpha))

    # Orange gradient border between photo and panel
    for i in range(6):
        progress = i / 6
        r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * progress)
        g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * progress)
        b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * progress)
        draw.rectangle([(0, photo_h + 8 + i), (SIZE, photo_h + 8 + i + 1)], fill=(r, g, b))

    # Bottom panel
    panel_y = photo_h + 14
    draw.rectangle([(0, panel_y), (SIZE, SIZE)], fill=WHITE)

    # Calculate total text height for vertical centering in panel
    panel_height = SIZE - panel_y
    font_h = _font(FONT_BOLD, 44)
    h_lines = _wrap_text(headline, font_h, SIZE - 100, draw)
    font_s = _font(FONT_REGULAR, 26)
    s_lines = _wrap_text(subtext, font_s, SIZE - 100, draw)
    total_text_h = len(h_lines) * 55 + 5 + len(s_lines) * 36
    y = panel_y + max(10, (panel_height - total_text_h - 60) // 2)

    # Headline centered
    for line in h_lines:
        hx = _centered_x(draw, line, font_h, SIZE)
        draw.text((hx, y), line, font=font_h, fill=DARK)
        y += 55

    # Subtext
    y += 5
    for line in s_lines:
        sx = _centered_x(draw, line, font_s, SIZE)
        draw.text((sx, y), line, font=font_s, fill=(100, 100, 100))
        y += 36

    # Logo bottom center
    _paste_logo_bottom_center(img, y_offset=20, max_h=55)

    # URL
    draw = ImageDraw.Draw(img)
    font_url = _font(FONT_REGULAR, 18)
    ux = _centered_x(draw, "mangalyamatrimony.com", font_url, SIZE)
    draw.text((ux, SIZE - 22), "mangalyamatrimony.com", font=font_url, fill=ORANGE)

    # Logo top-left on photo
    _paste_logo_on_white_pad(img, 20, 15, max_h=40)

    return _save(img, save_path)


# ═══════════════════════════════════════════════════════════════════════════
# POSTER 4: Bold Statement — Large Text with Photo Strip
# ═══════════════════════════════════════════════════════════════════════════

def poster_bold_statement(photo_query, big_text, small_text, save_path=None):
    """Bold large text dominates, thin photo strip on side."""
    photo = _fetch_photo(photo_query, "portrait")
    if not photo:
        return None

    img = Image.new("RGBA", (SIZE, SIZE), WHITE)

    # Photo strip on left (28% width for more visual impact)
    strip_w = int(SIZE * 0.28)
    photo_strip = photo.resize((strip_w, SIZE), Image.LANCZOS)
    img.paste(photo_strip, (0, 0))

    # Subtle orange tint overlay on photo strip
    orange_overlay = Image.new("RGBA", (strip_w, SIZE), (*ORANGE, 40))
    img.paste(Image.alpha_composite(
        img.crop((0, 0, strip_w, SIZE)),
        orange_overlay
    ), (0, 0))

    # Orange divider
    draw = ImageDraw.Draw(img)
    draw.rectangle([(strip_w, 0), (strip_w + 5, SIZE)], fill=ORANGE)

    # Top orange bar on text area
    draw.rectangle([(strip_w + 5, 0), (SIZE, 6)], fill=ORANGE)

    # Big bold text
    text_x = strip_w + 45
    max_w = SIZE - text_x - 45
    font_big = _font(FONT_BOLD, 56)
    big_lines = _wrap_text(big_text, font_big, max_w, draw)
    y = 120
    for line in big_lines:
        draw.text((text_x + 2, y + 2), line, font=font_big, fill=(240, 140, 30, 40))
        draw.text((text_x, y), line, font=font_big, fill=DARK)
        y += 70

    # Orange accent line under big text
    y += 20
    draw.rectangle([(text_x, y), (text_x + 120, y + 5)], fill=ORANGE)
    y += 35

    # Small text
    font_small = _font(FONT_REGULAR, 28)
    s_lines = _wrap_text(small_text, font_small, max_w, draw)
    for line in s_lines:
        draw.text((text_x, y), line, font=font_small, fill=(80, 80, 80))
        y += 40

    # Logo bottom right
    _paste_logo_on_white_pad(img, SIZE - 200, SIZE - 70, max_h=50)

    # URL
    draw = ImageDraw.Draw(img)
    font_url = _font(FONT_REGULAR, 20)
    draw.text((text_x, SIZE - 50), "mangalyamatrimony.com", font=font_url, fill=ORANGE)

    return _save(img, save_path)


# ═══════════════════════════════════════════════════════════════════════════
# POSTER 5: Cinematic Wide — Photo with Orange Band
# ═══════════════════════════════════════════════════════════════════════════

def poster_cinematic(photo_query, headline, subtext, save_path=None):
    """Full photo with a semi-transparent orange band across the middle."""
    photo = _fetch_photo(photo_query)
    if not photo:
        return None

    img = photo.resize((SIZE, SIZE), Image.LANCZOS)

    # Slight blur for dreamy effect (less blur, more sharp)
    bg = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    img = Image.blend(img.convert("RGBA"), bg.convert("RGBA"), 0.3)

    # Dark vignette on edges
    img = _draw_gradient_overlay(img, "top", (0, 0, 0), max_alpha=120, coverage=0.3)
    img = _draw_gradient_overlay(img, "bottom", (0, 0, 0), max_alpha=150, coverage=0.3)

    # Semi-transparent orange band in center
    draw = ImageDraw.Draw(img)
    band_y = SIZE // 2 - 80
    band_h = 200
    band_overlay = Image.new("RGBA", (SIZE, band_h), (*ORANGE, 0))
    band_draw = ImageDraw.Draw(band_overlay)
    band_draw.rectangle([(0, 0), (SIZE, band_h)], fill=(*ORANGE, 180))
    img.paste(band_overlay, (0, band_y), band_overlay)

    draw = ImageDraw.Draw(img)

    # Headline on band
    font_h = _font(FONT_BOLD, 50)
    h_lines = _wrap_text(headline, font_h, SIZE - 100, draw)
    y = band_y + 25 if len(h_lines) <= 2 else band_y + 10
    for line in h_lines:
        hx = _centered_x(draw, line, font_h, SIZE)
        draw.text((hx + 2, y + 2), line, font=font_h, fill=(150, 60, 10))
        draw.text((hx, y), line, font=font_h, fill=WHITE)
        y += 60

    # Subtext below band
    font_s = _font(FONT_REGULAR, 26)
    s_lines = _wrap_text(subtext, font_s, SIZE - 140, draw)
    y = band_y + band_h + 20
    for line in s_lines:
        sx = _centered_x(draw, line, font_s, SIZE)
        draw.text((sx + 1, y + 1), line, font=font_s, fill=(0, 0, 0, 150))
        draw.text((sx, y), line, font=font_s, fill=WHITE)
        y += 36

    # Logo top-left
    _paste_logo_on_white_pad(img, 20, 15, max_h=45)

    # URL bottom-left
    draw = ImageDraw.Draw(img)
    font_url = _font(FONT_REGULAR, 22)
    draw.text((21, SIZE - 39), "mangalyamatrimony.com", font=font_url, fill=(0, 0, 0, 150))
    draw.text((20, SIZE - 40), "mangalyamatrimony.com", font=font_url, fill=WHITE)

    # Orange lines top and bottom
    draw.rectangle([(0, 0), (SIZE, 4)], fill=ORANGE)
    draw.rectangle([(0, SIZE - 4), (SIZE, SIZE)], fill=ORANGE)

    return _save(img, save_path)


# ═══════════════════════════════════════════════════════════════════════════
# POSTER 6: Blurred Background with Center Card
# ═══════════════════════════════════════════════════════════════════════════

def poster_center_card(photo_query, headline, body_text, save_path=None):
    """Blurred photo background with a white center card overlay."""
    photo = _fetch_photo(photo_query)
    if not photo:
        return None

    img = photo.resize((SIZE, SIZE), Image.LANCZOS)

    # Moderate blur background (keep some photo visible)
    img = img.filter(ImageFilter.GaussianBlur(radius=8))
    img = img.convert("RGBA")

    # Darken
    img = _draw_gradient_overlay(img, "full", (0, 0, 0), max_alpha=100)

    # White center card with rounded corners
    card_margin = 80
    card_w = SIZE - card_margin * 2
    card_h = int(SIZE * 0.65)
    card_y = (SIZE - card_h) // 2
    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 250))
    card_draw = ImageDraw.Draw(card)

    # Orange top border on card
    card_draw.rectangle([(0, 0), (card_w, 6)], fill=ORANGE)

    img.paste(card, (card_margin, card_y), card)

    draw = ImageDraw.Draw(img)

    # Orange corner brackets on the white card
    _draw_orange_corner_brackets(
        draw,
        card_margin + 12, card_y + 12,
        card_margin + card_w - 12, card_y + card_h - 12,
        arm=35, thickness=3
    )

    # Logo on card top center
    logo = _load_logo(max_height=60)
    if logo:
        lx = (SIZE - logo.width) // 2
        ly = card_y + 25
        img.paste(logo, (lx, ly), logo)

    draw = ImageDraw.Draw(img)

    # Headline
    font_h = _font(FONT_BOLD, 44)
    h_lines = _wrap_text(headline, font_h, card_w - 80, draw)
    y = card_y + 110
    for line in h_lines:
        hx = _centered_x(draw, line, font_h, SIZE)
        draw.text((hx, y), line, font=font_h, fill=DARK)
        y += 55

    # Orange separator
    y += 10
    draw.rectangle([(SIZE // 2 - 60, y), (SIZE // 2 + 60, y + 4)], fill=ORANGE)
    y += 30

    # Body text
    font_b = _font(FONT_REGULAR, 28)
    b_lines = _wrap_text(body_text, font_b, card_w - 80, draw)
    for line in b_lines:
        bx = _centered_x(draw, line, font_b, SIZE)
        draw.text((bx, y), line, font=font_b, fill=(80, 80, 80))
        y += 42

    # URL on card bottom
    font_url = _font(FONT_REGULAR, 20)
    ux = _centered_x(draw, "mangalyamatrimony.com", font_url, SIZE)
    draw.text((ux, card_y + card_h - 40), "mangalyamatrimony.com", font=font_url, fill=ORANGE)

    return _save(img, save_path)


# ═══════════════════════════════════════════════════════════════════════════

def _save(img, save_path):
    buf = io.BytesIO()
    img = img.convert("RGB")
    img.save(buf, format="JPEG", quality=95)
    data = buf.getvalue()
    if save_path:
        with open(save_path, "wb") as f:
            f.write(data)
    return data


# ═══════════════════════════════════════════════════════════════════════════
# Generate all demo posters
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    out = PROJECT_ROOT / "posters"
    out.mkdir(exist_ok=True)

    print("Generating eye-catching photo posters...\n")

    # 1. Full Bleed
    poster_full_bleed(
        "south indian bride gold jewelry silk saree closeup",
        "Your Perfect Match Is Waiting",
        "Join thousands of families who found love on Mangalya Matrimony",
        save_path=out / "eye_01_full_bleed.jpg",
    )
    print("[OK] 1. Full Bleed Photo")

    # 2. Split Design
    poster_split(
        "south indian bride silk saree jewelry",
        "Find Someone Who Understands Your Values",
        "Mangalya Matrimony connects you with verified profiles from Telugu, Malayalam, and Tamil families. Every match is built on trust, tradition, and compatibility.",
        save_path=out / "eye_02_split.jpg",
    )
    print("[OK] 2. Split Design")

    # 3. Photo + Panel
    poster_photo_panel(
        "hindu wedding ceremony mangalsutra",
        "Where Tradition Meets Tomorrow",
        "Verified profiles. Horoscope matching. Free registration. Built for South Indian families.",
        save_path=out / "eye_03_photo_panel.jpg",
    )
    print("[OK] 3. Photo Panel")

    # 4. Bold Statement
    poster_bold_statement(
        "indian mehndi bridal hands closeup",
        "Every Great Love Story Begins With A Single Step",
        "Take yours today. Mangalya Matrimony has helped thousands of families find their perfect match. Register free and start your journey.",
        save_path=out / "eye_04_bold_statement.jpg",
    )
    print("[OK] 4. Bold Statement")

    # 5. Cinematic Band
    poster_cinematic(
        "indian couple wedding garland jaimala",
        "Made For Each Other",
        "5000+ verified profiles from across South India",
        save_path=out / "eye_05_cinematic.jpg",
    )
    print("[OK] 5. Cinematic Band")

    # 6. Center Card
    poster_center_card(
        "indian wedding decoration marigold flowers",
        "Your Family Deserves The Best Match",
        "At Mangalya Matrimony, every profile is verified. Every match is meaningful. Join the families who trust us to find the perfect life partner.",
        save_path=out / "eye_06_center_card.jpg",
    )
    print("[OK] 6. Center Card")

    print(f"\nAll posters saved to: {out}")
