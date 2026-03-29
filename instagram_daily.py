#!/usr/bin/env python3
"""
Daily Instagram auto-poster for Mangalya Matrimony.
Rotates between multiple poster styles:
  - Even days: Eye-catching photo posters (6 templates)
  - Odd days: Branded photo overlay (classic style)
Picks today's content from instagram_posts.json, generates the poster,
uploads to imgbb, and posts to Instagram.
"""

import os
import io
import sys
import json
import base64
import random
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

# Add agents dir for poster generator
sys.path.insert(0, os.path.join(SCRIPT_DIR, "agents"))

INSTAGRAM_ID  = os.getenv("INSTAGRAM_ACCOUNT_ID")
PAGE_TOKEN    = os.getenv("INSTAGRAM_PAGE_TOKEN")
PEXELS_KEY    = os.getenv("PEXELS_API_KEY")
IMGBB_KEY     = os.getenv("IMGBB_API_KEY")
POSTS_FILE    = os.path.join(SCRIPT_DIR, "instagram_posts.json")
LOG_FILE      = os.path.join(SCRIPT_DIR, "instagram_log.txt")

FONT_TITLE = r"C:\Windows\Fonts\arialbd.ttf"
FONT_URL   = r"C:\Windows\Fonts\arial.ttf"

# ─── Content pools for poster generation ──────────────────────────────────

PHOTO_QUERIES = [
    "south indian bride gold jewelry silk saree",
    "hindu wedding ceremony couple garland",
    "indian mehndi bridal hands closeup henna",
    "indian couple wedding romantic portrait",
    "south indian wedding decoration marigold flowers",
    "indian bride getting ready mirror jewelry",
    "indian wedding couple laughing candid",
    "south indian temple wedding ceremony brass lamp",
    "indian wedding reception couple dance",
    "bridal silk saree red gold traditional",
    "indian couple holding hands wedding rings",
    "south indian wedding food banana leaf feast",
    "indian wedding mandap decoration floral",
    "bride groom indian wedding sunset portrait",
    "traditional indian wedding jewelry gold necklace",
]

POSTER_HEADLINES = [
    "Your Perfect Match Is Waiting",
    "Where Tradition Meets Tomorrow",
    "Made For Each Other",
    "Every Love Story Begins Here",
    "Find Someone Who Understands You",
    "Your Family Deserves The Best Match",
    "Begin Your Forever Today",
    "Love Starts With Trust",
    "The Right Match Changes Everything",
    "Your Journey To Love Starts Now",
]

POSTER_SUBTEXTS = [
    "Join thousands of families who found love on Mangalya Matrimony",
    "Verified profiles. Horoscope matching. Free registration.",
    "5000+ verified profiles from across South India",
    "Built for Telugu, Malayalam, and Tamil families",
    "Safe, verified, and trusted by families across India",
    "Register free and start your journey today",
    "Every profile personally verified for your peace of mind",
    "Connecting hearts across South India since day one",
]

BODY_TEXTS = [
    "Mangalya Matrimony connects you with verified profiles from Telugu, Malayalam, and Tamil families. Every match is built on trust, tradition, and compatibility.",
    "At Mangalya Matrimony, every profile is verified. Every match is meaningful. Join the families who trust us to find the perfect life partner.",
    "We believe the right match is not just about horoscopes and backgrounds. It is about finding someone who truly understands your values and dreams.",
    "Thousands of families across South India have found their perfect match on Mangalya. Your love story could be next.",
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ─── Image generation methods ────────────────────────────────────────────

def generate_eye_catching_poster(template_num=None):
    """Generate an eye-catching photo poster using one of 6 templates."""
    try:
        from eye_catching_posters import (
            poster_full_bleed, poster_split, poster_photo_panel,
            poster_bold_statement, poster_cinematic, poster_center_card,
        )
    except ImportError:
        log("WARNING: eye_catching_posters not available, falling back to classic")
        return None, None

    if template_num is None:
        template_num = random.randint(1, 6)

    query = random.choice(PHOTO_QUERIES)
    headline = random.choice(POSTER_HEADLINES)
    subtext = random.choice(POSTER_SUBTEXTS)
    body = random.choice(BODY_TEXTS)

    template_name = ""
    poster_bytes = None

    try:
        if template_num == 1:
            template_name = "Full Bleed"
            poster_bytes = poster_full_bleed(query, headline, subtext)
        elif template_num == 2:
            template_name = "Split Design"
            poster_bytes = poster_split(query, headline, body)
        elif template_num == 3:
            template_name = "Photo Panel"
            poster_bytes = poster_photo_panel(query, headline, subtext)
        elif template_num == 4:
            template_name = "Bold Statement"
            poster_bytes = poster_bold_statement(query, headline, body)
        elif template_num == 5:
            template_name = "Cinematic Band"
            poster_bytes = poster_cinematic(query, headline, subtext)
        elif template_num == 6:
            template_name = "Center Card"
            poster_bytes = poster_center_card(query, headline, body)
    except Exception as e:
        log(f"ERROR generating template {template_num}: {e}")
        return None, None

    return poster_bytes, template_name


def generate_branded_photo(pexels_query):
    """Generate a classic branded photo overlay (original style)."""
    image_bytes, source_url = get_pexels_image_bytes(pexels_query)
    if not image_bytes:
        return None, None
    branded = add_branding(image_bytes)
    return branded, source_url


def get_pexels_image_bytes(query):
    """Fetch image bytes from Pexels."""
    for page in [random.randint(1, 5), 1]:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": 10, "page": page, "orientation": "square"},
            timeout=15,
        )
        photos = resp.json().get("photos", [])
        if photos:
            url = random.choice(photos)["src"]["large2x"]
            img_resp = requests.get(url, timeout=20)
            img_resp.raise_for_status()
            return img_resp.content, url
    return None, None


def add_branding(image_bytes):
    """Add Mangalya Matrimony premium branding overlay to image."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    img = img.resize((1080, 1080), Image.LANCZOS)
    w, h = img.size

    ORANGE = (245, 146, 27)
    RED = (232, 66, 30)

    # Vignette
    vignette = Image.new("RGBA", img.size, (0, 0, 0, 0))
    vig_draw = ImageDraw.Draw(vignette)
    for i in range(120):
        a = int(80 * (1 - i / 120))
        vig_draw.rectangle([(0, i), (w, i + 1)], fill=(0, 0, 0, a))
        vig_draw.rectangle([(0, h - 1 - i), (w, h - i)], fill=(0, 0, 0, a))
    for i in range(100):
        a = int(50 * (1 - i / 100))
        vig_draw.rectangle([(i, 0), (i + 1, h)], fill=(0, 0, 0, a))
        vig_draw.rectangle([(w - 1 - i, 0), (w - i, h)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img, vignette)

    # Orange top bar
    top_strip = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ts_draw = ImageDraw.Draw(top_strip)
    for i in range(50):
        progress = i / 50
        r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * progress)
        g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * progress)
        b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * progress)
        ts_draw.rectangle([(0, i), (w, i + 1)], fill=(r, g, b, 230))
    img = Image.alpha_composite(img, top_strip)

    # Logo top-left
    try:
        logo_path = r"C:\Users\ambav\Desktop\Matrimony\Logo.jpg"
        logo = Image.open(logo_path).convert("RGBA")
        data = list(logo.getdata())
        new_data = [(255, 255, 255, 0) if (p[0] > 230 and p[1] > 230 and p[2] > 230) else p for p in data]
        logo.putdata(new_data)
        ratio = 40 / logo.height
        logo = logo.resize((int(logo.width * ratio), 40), Image.LANCZOS)
        pad = Image.new("RGBA", (logo.width + 16, logo.height + 8), (255, 255, 255, 210))
        img.paste(pad, (15, 7), pad)
        img.paste(logo, (23, 11), logo)
    except:
        pass

    # Bottom gradient overlay
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    overlay_h = int(h * 0.40)
    for i in range(overlay_h):
        progress = i / overlay_h
        alpha = int(220 * (progress ** 1.4))
        draw_ov.rectangle([(0, h - overlay_h + i), (w, h - overlay_h + i + 1)], fill=(0, 0, 0, alpha))
    draw_ov.rectangle([(60, h - overlay_h), (w - 60, h - overlay_h + 2)], fill=(*ORANGE, 160))
    img = Image.alpha_composite(img, overlay)

    # Orange corner brackets
    corners = Image.new("RGBA", img.size, (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(corners)
    arm, thick, margin = 40, 3, 24
    gc = (*ORANGE, 200)
    c_draw.rectangle([(margin, margin), (margin + arm, margin + thick)], fill=gc)
    c_draw.rectangle([(margin, margin), (margin + thick, margin + arm)], fill=gc)
    c_draw.rectangle([(w - margin - arm, margin), (w - margin, margin + thick)], fill=gc)
    c_draw.rectangle([(w - margin - thick, margin), (w - margin, margin + arm)], fill=gc)
    c_draw.rectangle([(margin, h - margin - thick), (margin + arm, h - margin)], fill=gc)
    c_draw.rectangle([(margin, h - margin - arm), (margin + thick, h - margin)], fill=gc)
    c_draw.rectangle([(w - margin - arm, h - margin - thick), (w - margin, h - margin)], fill=gc)
    c_draw.rectangle([(w - margin - thick, h - margin - arm), (w - margin, h - margin)], fill=gc)
    img = Image.alpha_composite(img, corners)

    # Text
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.truetype(FONT_TITLE, 60)
    font_tagline = ImageFont.truetype(FONT_URL, 30)
    font_url = ImageFont.truetype(FONT_URL, 24)

    title = "Mangalya Matrimony"
    tagline = "Your Perfect Match Awaits"
    url = "mangalyamatrimony.com"

    def centered_x(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return (w - (bbox[2] - bbox[0])) // 2

    title_y = h - overlay_h + int(overlay_h * 0.30)

    # Title in orange
    tx = centered_x(title, font_title)
    for dx, dy, sa in [(3, 3, 180), (1, 1, 100)]:
        draw.text((tx + dx, title_y + dy), title, font=font_title, fill=(0, 0, 0, sa))
    draw.text((tx, title_y), title, font=font_title, fill=ORANGE)

    # Tagline
    ty = title_y + 72
    tgx = centered_x(tagline, font_tagline)
    draw.text((tgx + 1, ty + 1), tagline, font=font_tagline, fill=(0, 0, 0, 150))
    draw.text((tgx, ty), tagline, font=font_tagline, fill=(255, 255, 255, 240))

    # Separator
    sep_y = ty + 40
    sep_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sep_overlay).rectangle(
        [((w - 100) // 2, sep_y), ((w + 100) // 2, sep_y + 2)], fill=(*ORANGE, 160)
    )
    img = Image.alpha_composite(img, sep_overlay)

    # URL
    draw = ImageDraw.Draw(img)
    uy = sep_y + 14
    ux = centered_x(url, font_url)
    draw.text((ux + 1, uy + 1), url, font=font_url, fill=(0, 0, 0, 130))
    draw.text((ux, uy), url, font=font_url, fill=(255, 255, 255, 200))

    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# ─── Upload & Post ────────────────────────────────────────────────────────

def upload_to_imgbb(image_bytes):
    """Upload image bytes to imgbb and return public URL."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_KEY, "image": b64},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["url"]


def post_to_instagram(caption, image_url):
    """Post image to Instagram via Graph API."""
    base = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ID}"

    r1 = requests.post(f"{base}/media", data={
        "image_url": image_url,
        "caption": caption,
        "access_token": PAGE_TOKEN,
    }, timeout=30)
    r1.raise_for_status()

    r2 = requests.post(f"{base}/media_publish", data={
        "creation_id": r1.json()["id"],
        "access_token": PAGE_TOKEN,
    }, timeout=30)
    r2.raise_for_status()
    return r2.json()["id"]


def get_today_post():
    with open(POSTS_FILE, encoding="utf-8") as f:
        posts = json.load(f)
    index = (datetime.now().timetuple().tm_yday - 1) % len(posts)
    return posts[index]


# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    log("=== Daily Instagram Post Started ===")
    try:
        post = get_today_post()
        log(f"Theme: {post['theme']} | Language: {post['language']}")

        day_of_year = datetime.now().timetuple().tm_yday
        use_eye_catching = (day_of_year % 2 == 0)  # Even days: eye-catching, Odd: branded

        if use_eye_catching:
            # Rotate through 6 templates based on day
            template_num = ((day_of_year // 2) % 6) + 1
            log(f"Style: Eye-catching poster (Template #{template_num})")

            poster_bytes, template_name = generate_eye_catching_poster(template_num)
            if poster_bytes:
                log(f"Generated: {template_name}")
            else:
                log("Eye-catching failed, falling back to branded photo")
                poster_bytes, source_url = generate_branded_photo(post["pexels_query"])
                if not poster_bytes:
                    log("ERROR: Could not generate any image")
                    return
                log(f"Branded photo from: {source_url}")
        else:
            log("Style: Branded photo overlay")
            poster_bytes, source_url = generate_branded_photo(post["pexels_query"])
            if not poster_bytes:
                log("ERROR: No image found on Pexels")
                return
            log(f"Pexels image: {source_url}")

        # Upload and post
        public_url = upload_to_imgbb(poster_bytes)
        log(f"Uploaded to imgbb: {public_url}")

        post_id = post_to_instagram(post["caption"], public_url)
        log(f"SUCCESS: Posted to Instagram. Post ID: {post_id}")

    except requests.HTTPError as e:
        log(f"HTTP ERROR: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        import traceback
        log(f"ERROR: {e}\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()
