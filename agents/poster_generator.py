"""
Poster Generator — Creates professional Instagram posters for Mangalya Matrimony.
Uses the actual Mangalya logo and brand colors (orange/red).

Templates:
1. Quote Card      — Inspirational quote on a designed background
2. Tip Post        — Marriage/relationship tips with numbered list
3. Cultural Fact   — "Did You Know?" regional wedding traditions
4. Festival        — Festival greeting with decorative elements
5. Feature Post    — Why Choose Mangalya? brand awareness

Brand Colors (from logo):
- Orange:     #F5921B (primary)
- Red:        #E8421E (accent)
- Dark:       #2D2D2D (text)
- Cream:      #FFF8F0 (warm background)
- White:      #FFFFFF
"""

import io
import os
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Brand colors (matching logo)
ORANGE = (245, 146, 27)
RED = (232, 66, 30)
DARK_ORANGE = (200, 100, 20)
CREAM = (255, 248, 240)
WARM_WHITE = (255, 252, 247)
DARK = (45, 45, 45)
WHITE = (255, 255, 255)
LIGHT_ORANGE = (255, 235, 210)
DEEP_RED = (160, 40, 20)

# Logo path
LOGO_PATH = r"C:\Users\ambav\Desktop\Matrimony\Logo.jpg"

# Fonts (Windows)
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REGULAR = r"C:\Windows\Fonts\arial.ttf"
FONT_ITALIC = r"C:\Windows\Fonts\ariali.ttf"

SIZE = 1080  # Instagram square


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()


def _centered_x(draw, text, font, canvas_w):
    bbox = draw.textbbox((0, 0), text, font=font)
    return (canvas_w - (bbox[2] - bbox[0])) // 2


def _load_logo(max_height=80):
    """Load and resize logo, removing white background."""
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        # Remove white/near-white background
        data = logo.getdata()
        new_data = []
        for item in data:
            # If pixel is white-ish (R>230, G>230, B>230), make transparent
            if item[0] > 230 and item[1] > 230 and item[2] > 230:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        logo.putdata(new_data)
        # Resize keeping aspect ratio
        ratio = max_height / logo.height
        new_w = int(logo.width * ratio)
        logo = logo.resize((new_w, max_height), Image.LANCZOS)
        return logo
    except Exception as e:
        print(f"Could not load logo: {e}")
        return None


def _draw_orange_corners(draw, w, h, inset=30, arm=50, thickness=3):
    """Draw decorative L-shaped orange corners."""
    c = ORANGE
    # Top-left
    draw.rectangle([(inset, inset), (inset + arm, inset + thickness)], fill=c)
    draw.rectangle([(inset, inset), (inset + thickness, inset + arm)], fill=c)
    # Top-right
    draw.rectangle([(w - inset - arm, inset), (w - inset, inset + thickness)], fill=c)
    draw.rectangle([(w - inset - thickness, inset), (w - inset, inset + arm)], fill=c)
    # Bottom-left
    draw.rectangle([(inset, h - inset - thickness), (inset + arm, h - inset)], fill=c)
    draw.rectangle([(inset, h - inset - arm), (inset + thickness, h - inset)], fill=c)
    # Bottom-right
    draw.rectangle([(w - inset - arm, h - inset - thickness), (w - inset, h - inset)], fill=c)
    draw.rectangle([(w - inset - thickness, h - inset - arm), (w - inset, h - inset)], fill=c)


def _draw_logo_footer(img, footer_bg=WHITE):
    """Draw bottom footer with actual logo image + URL."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    footer_h = 140
    y = h - footer_h

    # Footer background
    draw.rectangle([(0, y), (w, h)], fill=footer_bg)

    # Orange gradient line at top of footer
    for i in range(4):
        progress = i / 4
        r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * progress)
        g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * progress)
        b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * progress)
        draw.rectangle([(0, y + i), (w, y + i + 1)], fill=(r, g, b))

    # Paste logo centered
    logo = _load_logo(max_height=70)
    if logo:
        logo_x = (w - logo.width) // 2
        logo_y = y + 15
        img.paste(logo, (logo_x, logo_y), logo)

    # URL below logo
    draw = ImageDraw.Draw(img)  # Refresh draw after paste
    font_url = _font(FONT_REGULAR, 20)
    url_text = "mangalyamatrimony.com"
    url_x = _centered_x(draw, url_text, font_url, w)
    draw.text((url_x, y + 95), url_text, font=font_url, fill=DARK)


def _draw_logo_footer_dark(img):
    """Draw footer on dark background with logo."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    footer_h = 140
    y = h - footer_h

    # Dark footer
    draw.rectangle([(0, y), (w, h)], fill=(30, 20, 15))

    # Orange line
    for i in range(4):
        progress = i / 4
        r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * progress)
        g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * progress)
        b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * progress)
        draw.rectangle([(0, y + i), (w, y + i + 1)], fill=(r, g, b))

    # Logo on dark — load with white version or use as-is
    logo = _load_logo(max_height=70)
    if logo:
        # Create a white background pad behind logo for visibility on dark
        pad = Image.new("RGBA", (logo.width + 30, logo.height + 10), (255, 255, 255, 220))
        # Round the pad edges
        pad_draw = ImageDraw.Draw(pad)
        pad_x = (w - pad.width) // 2
        pad_y = y + 13
        img.paste(pad, (pad_x, pad_y), pad)
        logo_x = (w - logo.width) // 2
        logo_y = y + 18
        img.paste(logo, (logo_x, logo_y), logo)

    draw = ImageDraw.Draw(img)
    font_url = _font(FONT_REGULAR, 20)
    url_text = "mangalyamatrimony.com"
    url_x = _centered_x(draw, url_text, font_url, w)
    draw.text((url_x, y + 100), url_text, font=font_url, fill=ORANGE)


def _draw_top_bar(draw, w, height=50):
    """Draw orange-to-red gradient top bar."""
    for i in range(height):
        progress = i / height
        r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * progress)
        g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * progress)
        b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * progress)
        draw.rectangle([(0, i), (w, i + 1)], fill=(r, g, b))


def _wrap_text(text, font, max_width, draw):
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


# ─── Template 1: Quote Card ─────────────────────────────────────────────────

def generate_quote_card(quote, author="", save_path=None):
    """Inspirational quote on a warm cream background with orange accents."""
    img = Image.new("RGBA", (SIZE, SIZE), CREAM)
    draw = ImageDraw.Draw(img)

    # Top gradient bar
    _draw_top_bar(draw, SIZE, height=55)

    # Subtle background pattern — thin orange diagonal lines
    for i in range(-SIZE, SIZE * 2, 50):
        draw.line([(i, 70), (i + SIZE, SIZE - 160)], fill=(*LIGHT_ORANGE, 100), width=1)

    # Orange corners
    _draw_orange_corners(draw, SIZE, SIZE - 140, inset=45, arm=55, thickness=3)

    # Large orange quote mark
    font_quote_mark = _font(FONT_BOLD, 180)
    draw.text((70, 80), "\u201C", font=font_quote_mark, fill=(*ORANGE, 180))

    # Quote text
    font_quote = _font(FONT_BOLD, 44)
    lines = _wrap_text(quote, font_quote, SIZE - 180, draw)
    y = 280
    for line in lines:
        lx = _centered_x(draw, line, font_quote, SIZE)
        draw.text((lx + 1, y + 1), line, font=font_quote, fill=(150, 80, 30))
        draw.text((lx, y), line, font=font_quote, fill=DARK)
        y += 58

    # Author in orange
    if author:
        font_author = _font(FONT_ITALIC, 26)
        author_text = f"-- {author}"
        ax = _centered_x(draw, author_text, font_author, SIZE)
        draw.text((ax, y + 25), author_text, font=font_author, fill=ORANGE)

    # Orange separator line
    sep_y = y + (75 if author else 35)
    draw.rectangle([(SIZE // 2 - 60, sep_y), (SIZE // 2 + 60, sep_y + 3)], fill=ORANGE)

    # Logo footer
    img = img.convert("RGBA")
    _draw_logo_footer(img, footer_bg=WHITE)

    return _save(img, save_path, "quote_card")


# ─── Template 2: Tip Post ───────────────────────────────────────────────────

def generate_tip_post(title, tips, save_path=None):
    """Numbered tips with orange header and clean white body."""
    img = Image.new("RGBA", (SIZE, SIZE), WHITE)
    draw = ImageDraw.Draw(img)

    # Top section — orange-to-red gradient header
    header_h = 220
    for i in range(header_h):
        progress = i / header_h
        r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * progress)
        g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * progress)
        b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * progress)
        draw.rectangle([(0, i), (SIZE, i + 1)], fill=(r, g, b))

    # Thin white line at bottom of header
    draw.rectangle([(40, header_h - 3), (SIZE - 40, header_h - 1)], fill=(*WHITE, 120))

    # Logo small at top-left of header
    logo_small = _load_logo(max_height=35)
    if logo_small:
        # White pad for visibility
        pad = Image.new("RGBA", (logo_small.width + 16, logo_small.height + 8), (255, 255, 255, 200))
        img.paste(pad, (30, 15), pad)
        img.paste(logo_small, (38, 19), logo_small)
    draw = ImageDraw.Draw(img)

    # Title in header
    font_title = _font(FONT_BOLD, 46)
    title_lines = _wrap_text(title, font_title, SIZE - 120, draw)
    ty = 75 if len(title_lines) > 1 else 90
    for line in title_lines:
        tx = _centered_x(draw, line, font_title, SIZE)
        draw.text((tx + 2, ty + 2), line, font=font_title, fill=(180, 60, 20))
        draw.text((tx, ty), line, font=font_title, fill=WHITE)
        ty += 58

    # Tips with orange number circles
    font_num = _font(FONT_BOLD, 30)
    font_tip = _font(FONT_REGULAR, 30)
    y = header_h + 30
    available = SIZE - header_h - 170
    tip_spacing = max(50, available // max(len(tips), 1))

    for i, tip in enumerate(tips, 1):
        # Orange circle with number
        cx, cy = 75, y + 18
        draw.ellipse([(cx - 22, cy - 22), (cx + 22, cy + 22)], fill=ORANGE)
        num_text = str(i)
        bbox = draw.textbbox((0, 0), num_text, font=font_num)
        nx = cx - (bbox[2] - bbox[0]) // 2
        draw.text((nx, cy - 17), num_text, font=font_num, fill=WHITE)

        # Tip text
        tip_lines = _wrap_text(tip, font_tip, SIZE - 170, draw)
        tip_y = y
        for tl in tip_lines:
            draw.text((115, tip_y), tl, font=font_tip, fill=DARK)
            tip_y += 38
        y = tip_y + (tip_spacing - 38)

    # Subtle left orange accent line
    draw.rectangle([(0, header_h), (5, SIZE - 140)], fill=ORANGE)

    # Logo footer
    _draw_logo_footer(img)

    return _save(img, save_path, "tip_post")


# ─── Template 3: Cultural Fact ───────────────────────────────────────────────

def generate_cultural_fact(title, fact_text, region="South India", save_path=None):
    """'Did You Know?' cultural wedding tradition with warm design."""
    img = Image.new("RGBA", (SIZE, SIZE), CREAM)
    draw = ImageDraw.Draw(img)

    # Top gradient bar
    _draw_top_bar(draw, SIZE, height=45)

    # "DID YOU KNOW?" orange pill badge
    font_header = _font(FONT_BOLD, 26)
    header_text = "DID YOU KNOW?"
    badge_w = 300
    badge_h = 48
    bx = (SIZE - badge_w) // 2
    by = 75
    draw.rounded_rectangle([(bx, by), (bx + badge_w, by + badge_h)], radius=24, fill=ORANGE)
    hx = _centered_x(draw, header_text, font_header, SIZE)
    draw.text((hx, by + 10), header_text, font=font_header, fill=WHITE)

    # Title in dark
    font_title = _font(FONT_BOLD, 46)
    title_lines = _wrap_text(title, font_title, SIZE - 140, draw)
    ty = 165
    for line in title_lines:
        tx = _centered_x(draw, line, font_title, SIZE)
        draw.text((tx, ty), line, font=font_title, fill=DARK)
        ty += 58

    # Orange separator
    draw.rectangle([(SIZE // 2 - 80, ty + 10), (SIZE // 2 + 80, ty + 14)], fill=ORANGE)

    # Fact text
    font_fact = _font(FONT_REGULAR, 32)
    fact_lines = _wrap_text(fact_text, font_fact, SIZE - 140, draw)
    fy = ty + 45
    for line in fact_lines:
        fx = _centered_x(draw, line, font_fact, SIZE)
        draw.text((fx, fy), line, font=font_fact, fill=DARK)
        fy += 46

    # Region tag in orange italic
    font_region = _font(FONT_ITALIC, 24)
    region_text = f"-- {region} Wedding Tradition"
    rx = _centered_x(draw, region_text, font_region, SIZE)
    draw.text((rx, fy + 25), region_text, font=font_region, fill=ORANGE)

    # Orange corners
    _draw_orange_corners(draw, SIZE, SIZE - 140, inset=30, arm=50, thickness=2)

    # Logo footer
    _draw_logo_footer(img)

    return _save(img, save_path, "cultural_fact")


# ─── Template 4: Festival Greeting ──────────────────────────────────────────

def generate_festival_greeting(festival_name, greeting_text, year="2026", save_path=None):
    """Festival greeting on dark background with warm orange/red accents."""
    img = Image.new("RGBA", (SIZE, SIZE), (35, 25, 20))
    draw = ImageDraw.Draw(img)

    # Decorative radial glow from center
    cx, cy = SIZE // 2, SIZE // 2 - 60
    for r in range(420, 0, -6):
        intensity = int(35 * (r / 420))
        color = (ORANGE[0], min(255, ORANGE[1] + 20), ORANGE[2])
        dim = tuple(max(0, min(255, c - 180 + intensity)) for c in color)
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=dim, width=1)

    # Orange corners on dark
    _draw_orange_corners(draw, SIZE, SIZE, inset=25, arm=70, thickness=3)

    # Top decorative orange line with diamond
    draw.rectangle([(80, 75), (SIZE - 80, 78)], fill=ORANGE)
    dx = SIZE // 2
    draw.polygon([(dx, 64), (dx + 13, 76), (dx, 88), (dx - 13, 76)], fill=ORANGE)

    # Festival name in large orange-gold
    font_festival = _font(FONT_BOLD, 74)
    fx = _centered_x(draw, festival_name, font_festival, SIZE)
    draw.text((fx + 2, 122), festival_name, font=font_festival, fill=(50, 20, 10))
    draw.text((fx, 120), festival_name, font=font_festival, fill=ORANGE)

    # Year
    font_year = _font(FONT_REGULAR, 30)
    yx = _centered_x(draw, year, font_year, SIZE)
    draw.text((yx, 208), year, font=font_year, fill=WHITE)

    # Separator
    draw.rectangle([(SIZE // 2 - 100, 258), (SIZE // 2 + 100, 261)], fill=ORANGE)

    # Greeting text
    font_greeting = _font(FONT_REGULAR, 34)
    greeting_lines = _wrap_text(greeting_text, font_greeting, SIZE - 160, draw)
    gy = 290
    for line in greeting_lines:
        gx = _centered_x(draw, line, font_greeting, SIZE)
        draw.text((gx, gy), line, font=font_greeting, fill=CREAM)
        gy += 50

    # "With love" text in orange
    font_from = _font(FONT_ITALIC, 24)
    from_text = "With love, from the Mangalya family"
    frx = _centered_x(draw, from_text, font_from, SIZE)
    draw.text((frx, gy + 35), from_text, font=font_from, fill=ORANGE)

    # Bottom decorative line
    draw.rectangle([(80, SIZE - 170), (SIZE - 80, SIZE - 167)], fill=ORANGE)
    dx2 = SIZE // 2
    draw.polygon([(dx2, SIZE - 180), (dx2 + 13, SIZE - 169), (dx2, SIZE - 158), (dx2 - 13, SIZE - 169)], fill=ORANGE)

    # Dark footer with logo
    _draw_logo_footer_dark(img)

    return _save(img, save_path, "festival")


# ─── Template 5: Feature Highlight ──────────────────────────────────────────

def generate_feature_post(headline, features, save_path=None):
    """Feature showcase with orange gradient header."""
    img = Image.new("RGBA", (SIZE, SIZE), WHITE)
    draw = ImageDraw.Draw(img)

    # Orange-to-red gradient header
    top_h = 340
    for i in range(top_h):
        progress = i / top_h
        r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * progress * 0.7)
        g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * progress * 0.7)
        b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * progress * 0.7)
        draw.rectangle([(0, i), (SIZE, i + 1)], fill=(r, g, b))

    # Logo in header top-right area
    logo_sm = _load_logo(max_height=40)
    if logo_sm:
        pad = Image.new("RGBA", (logo_sm.width + 16, logo_sm.height + 8), (255, 255, 255, 200))
        img.paste(pad, (SIZE - logo_sm.width - 50, 18), pad)
        img.paste(logo_sm, (SIZE - logo_sm.width - 42, 22), logo_sm)
    draw = ImageDraw.Draw(img)

    # Headline
    font_headline = _font(FONT_BOLD, 50)
    h_lines = _wrap_text(headline, font_headline, SIZE - 120, draw)
    hy = 90 if len(h_lines) > 2 else 120
    for line in h_lines:
        hx = _centered_x(draw, line, font_headline, SIZE)
        draw.text((hx + 2, hy + 2), line, font=font_headline, fill=(180, 60, 20))
        draw.text((hx, hy), line, font=font_headline, fill=WHITE)
        hy += 62

    # White area with features
    y = top_h + 30
    font_feature = _font(FONT_REGULAR, 31)
    font_check = _font(FONT_BOLD, 28)
    available = SIZE - top_h - 170
    spacing = max(50, available // max(len(features), 1))

    for feature in features:
        # Orange check circle
        cx, cy = 75, y + 17
        draw.ellipse([(cx - 21, cy - 21), (cx + 21, cy + 21)], fill=ORANGE)
        # White checkmark
        draw.line([(cx - 8, cy), (cx - 2, cy + 8)], fill=WHITE, width=3)
        draw.line([(cx - 2, cy + 8), (cx + 10, cy - 6)], fill=WHITE, width=3)

        # Feature text
        f_lines = _wrap_text(feature, font_feature, SIZE - 170, draw)
        fy = y
        for fl in f_lines:
            draw.text((115, fy), fl, font=font_feature, fill=DARK)
            fy += 40
        y = fy + (spacing - 40)

    # Left accent bar
    draw.rectangle([(0, top_h), (5, SIZE - 140)], fill=ORANGE)

    # Orange corners on white area
    _draw_orange_corners(draw, SIZE, SIZE - 140, inset=20, arm=40, thickness=2)

    # Logo footer
    _draw_logo_footer(img)

    return _save(img, save_path, "feature")


# ─── Save helper ─────────────────────────────────────────────────────────────

def _save(img, save_path, prefix):
    """Save image and return bytes."""
    buf = io.BytesIO()
    img = img.convert("RGB")
    img.save(buf, format="JPEG", quality=95)
    image_bytes = buf.getvalue()

    if save_path:
        with open(save_path, "wb") as f:
            f.write(image_bytes)

    return image_bytes


# ─── Demo: Generate all templates ───────────────────────────────────────────

if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent.parent / "posters"
    output_dir.mkdir(exist_ok=True)

    print("Generating poster templates with Mangalya logo...\n")

    # 1. Quote Card
    generate_quote_card(
        "The strongest marriages are built on small, honest conversations spoken with sincerity every single day.",
        author="Mangalya Matrimony",
        save_path=output_dir / "01_quote_card.jpg",
    )
    print("[OK] Quote Card")

    # 2. Tip Post
    generate_tip_post(
        "5 Things to Discuss Before Marriage",
        [
            "Future goals and career aspirations",
            "Family expectations and responsibilities",
            "Financial planning and savings",
            "Where to live and lifestyle choices",
            "Values, traditions, and beliefs",
        ],
        save_path=output_dir / "02_tip_post.jpg",
    )
    print("[OK] Tip Post")

    # 3. Cultural Fact
    generate_cultural_fact(
        "Jeelakarra Bellam",
        "In Telugu weddings, the bride and groom place cumin and jaggery on each other's head. Cumin is bitter, jaggery is sweet -- symbolizing the promise to share life's joys and sorrows together.",
        region="Telugu",
        save_path=output_dir / "03_cultural_fact.jpg",
    )
    print("[OK] Cultural Fact")

    # 4. Festival Greeting
    generate_festival_greeting(
        "Happy Ugadi",
        "May this new year bring you love, prosperity, and the perfect life partner. Wishing joy and togetherness to you and your family.",
        year="2026",
        save_path=output_dir / "04_festival_ugadi.jpg",
    )
    print("[OK] Festival Greeting")

    # 5. Feature Post
    generate_feature_post(
        "Why Families Trust Mangalya Matrimony",
        [
            "Every profile is personally verified",
            "Built for Telugu and Malayali families",
            "Horoscope compatibility matching",
            "Your privacy is always protected",
            "Completely free to register",
        ],
        save_path=output_dir / "05_feature_post.jpg",
    )
    print("[OK] Feature Post")

    print(f"\nAll posters saved to: {output_dir}")
