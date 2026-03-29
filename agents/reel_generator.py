"""
Reel Generator — Creates Instagram Reels (short videos) for Mangalya Matrimony.

Reel Types:
1. Slideshow     — 4-5 photos with text overlays, smooth transitions
2. Quote Reel    — Single photo with animated text appearing word by word
3. Tips Reel     — Numbered tips appearing one by one on photo backgrounds
4. Cultural Fact — "Did You Know?" with zoom effect on photo

Output: MP4 video (1080x1920 portrait, 15-30 seconds, 30fps)
"""

import io
import os
import sys
import random
import tempfile
import requests
import numpy as np
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

# Reel dimensions (9:16 portrait)
REEL_W = 1080
REEL_H = 1920


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


def _load_logo(max_height=80):
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        data = list(logo.getdata())
        new_data = [(255, 255, 255, 0) if (p[0] > 230 and p[1] > 230 and p[2] > 230) else p for p in data]
        logo.putdata(new_data)
        ratio = max_height / logo.height
        return logo.resize((int(logo.width * ratio), max_height), Image.LANCZOS)
    except:
        return None


def _fetch_photos(query, count=5):
    """Fetch multiple photos from Pexels."""
    photos = []
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_KEY},
        params={"query": query, "per_page": count + 5, "page": random.randint(1, 3), "orientation": "portrait"},
        timeout=15,
    )
    for photo in resp.json().get("photos", [])[:count]:
        try:
            url = photo["src"]["large2x"]
            img_resp = requests.get(url, timeout=20)
            img_resp.raise_for_status()
            img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
            photos.append(img)
        except:
            pass
    return photos


def _create_frame(bg_color=DARK):
    """Create a blank 9:16 frame."""
    return Image.new("RGB", (REEL_W, REEL_H), bg_color)


def _fit_photo_to_frame(photo, w=REEL_W, h=REEL_H):
    """Resize and crop photo to fit 9:16 frame."""
    pw, ph = photo.size
    target_ratio = w / h
    photo_ratio = pw / ph

    if photo_ratio > target_ratio:
        # Photo is wider — crop sides
        new_w = int(ph * target_ratio)
        left = (pw - new_w) // 2
        photo = photo.crop((left, 0, left + new_w, ph))
    else:
        # Photo is taller — crop top/bottom
        new_h = int(pw / target_ratio)
        top = (ph - new_h) // 2
        photo = photo.crop((0, top, pw, top + new_h))

    return photo.resize((w, h), Image.LANCZOS)


def _add_gradient(img, direction="bottom", color=(0, 0, 0), alpha=180, coverage=0.45):
    """Add gradient overlay to image."""
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size

    if direction == "bottom":
        start = int(h * (1 - coverage))
        for y in range(start, h):
            progress = (y - start) / (h - start)
            a = int(alpha * (progress ** 1.3))
            draw.rectangle([(0, y), (w, y + 1)], fill=(*color, a))
    elif direction == "top":
        end = int(h * coverage)
        for y in range(end):
            progress = 1 - y / end
            a = int(alpha * (progress ** 1.3))
            draw.rectangle([(0, y), (w, y + 1)], fill=(*color, a))

    return Image.alpha_composite(img, overlay).convert("RGB")


def _add_branding(img):
    """Add logo and URL to frame."""
    img = img.convert("RGBA")
    logo = _load_logo(55)
    if logo:
        pad = Image.new("RGBA", (logo.width + 16, logo.height + 10), (255, 255, 255, 200))
        x = (REEL_W - pad.width) // 2
        img.paste(pad, (x, REEL_H - 130), pad)
        img.paste(logo, (x + 8, REEL_H - 125), logo)

    draw = ImageDraw.Draw(img)
    font_url = _font(FONT_REGULAR, 24)
    url = "mangalyamatrimony.com"
    ux = _centered_x(draw, url, font_url, REEL_W)
    draw.text((ux, REEL_H - 60), url, font=font_url, fill=ORANGE)
    return img.convert("RGB")


def _ease_in_out(t):
    """Smooth easing function."""
    return t * t * (3 - 2 * t)


def _ken_burns(photo, progress, direction="zoom_in"):
    """Apply Ken Burns (slow zoom) effect to a photo."""
    w, h = photo.size
    if direction == "zoom_in":
        scale = 1.0 + 0.15 * _ease_in_out(progress)
    else:
        scale = 1.15 - 0.15 * _ease_in_out(progress)

    new_w = int(w * scale)
    new_h = int(h * scale)
    zoomed = photo.resize((new_w, new_h), Image.LANCZOS)

    # Crop center
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return zoomed.crop((left, top, left + w, top + h))


# ═══════════════════════════════════════════════════════════════════════════
# REEL 1: Slideshow — Multiple photos with text overlays
# ═══════════════════════════════════════════════════════════════════════════

def reel_slideshow(photo_query, texts, duration_per_slide=4, save_path=None):
    """
    Create a slideshow reel with Ken Burns effect on each photo.
    texts: list of strings, one per slide.
    """
    from moviepy import ImageClip, concatenate_videoclips, CompositeVideoClip

    photos = _fetch_photos(photo_query, count=len(texts))
    if len(photos) < len(texts):
        # Pad with duplicates
        while len(photos) < len(texts):
            photos.append(photos[random.randint(0, len(photos) - 1)])

    clips = []
    fps = 24
    total_frames = duration_per_slide * fps

    for idx, (photo, text) in enumerate(zip(photos, texts)):
        frames = []
        fitted = _fit_photo_to_frame(photo)
        direction = "zoom_in" if idx % 2 == 0 else "zoom_out"

        for frame_num in range(total_frames):
            progress = frame_num / total_frames

            # Ken Burns effect
            frame = _ken_burns(fitted, progress, direction)

            # Add gradient
            frame = _add_gradient(frame, "bottom", alpha=200, coverage=0.40)

            # Add text
            frame = frame.convert("RGBA")
            draw = ImageDraw.Draw(frame)

            # Orange top bar
            for i in range(5):
                p = i / 5
                r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * p)
                g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * p)
                b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * p)
                draw.rectangle([(0, i), (REEL_W, i + 1)], fill=(r, g, b))

            # Text with fade-in effect
            text_alpha = min(255, int(255 * min(1.0, progress * 3)))
            font_text = _font(FONT_BOLD, 56)
            lines = _wrap_text(text, font_text, REEL_W - 100, draw)
            y = REEL_H - 350
            for line in lines:
                lx = _centered_x(draw, line, font_text, REEL_W)
                draw.text((lx + 2, y + 2), line, font=font_text, fill=(0, 0, 0, text_alpha))
                draw.text((lx, y), line, font=font_text, fill=(255, 255, 255, text_alpha))
                y += 68

            # Branding on last frame
            frame = _add_branding(frame)

            frames.append(np.array(frame.convert("RGB")))

        # Create clip from frames
        clip = ImageClip(frames[0]).with_duration(duration_per_slide)
        # Use make_frame for animation
        def make_frame_func(frames_list, fps_val):
            def make_frame(t):
                idx = min(int(t * fps_val), len(frames_list) - 1)
                return frames_list[idx]
            return make_frame
        clip = clip.with_make_frame(make_frame_func(frames, fps))
        clips.append(clip)

    # Concatenate all clips
    final = concatenate_videoclips(clips, method="compose")

    # Save
    if save_path is None:
        save_path = str(PROJECT_ROOT / "reels" / "slideshow_reel.mp4")
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)

    final.write_videofile(
        str(save_path),
        fps=fps,
        codec="libx264",
        audio=False,
        preset="medium",
        logger=None,
    )
    return str(save_path)


# ═══════════════════════════════════════════════════════════════════════════
# REEL 2: Tips Reel — Tips appearing one by one
# ═══════════════════════════════════════════════════════════════════════════

def reel_tips(photo_query, title, tips, save_path=None):
    """
    Create a reel where tips appear one by one over a photo background.
    """
    from moviepy import ImageClip, concatenate_videoclips

    photos = _fetch_photos(photo_query, count=1)
    if not photos:
        return None

    bg_photo = _fit_photo_to_frame(photos[0])
    bg_photo = _add_gradient(bg_photo, "bottom", alpha=220, coverage=0.65)
    bg_photo = _add_gradient(bg_photo, "top", alpha=180, coverage=0.25)

    fps = 24
    clips = []

    # Title card (3 seconds)
    title_frames = []
    for f in range(3 * fps):
        progress = f / (3 * fps)
        frame = bg_photo.copy().convert("RGBA")
        draw = ImageDraw.Draw(frame)

        # Orange bars
        for i in range(6):
            p = i / 6
            r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * p)
            g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * p)
            b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * p)
            draw.rectangle([(0, i), (REEL_W, i + 1)], fill=(r, g, b))

        # Title
        font_title = _font(FONT_BOLD, 64)
        t_lines = _wrap_text(title, font_title, REEL_W - 100, draw)
        y = REEL_H // 2 - 100
        alpha = min(255, int(255 * min(1.0, progress * 4)))
        for line in t_lines:
            tx = _centered_x(draw, line, font_title, REEL_W)
            draw.text((tx + 2, y + 2), line, font=font_title, fill=(0, 0, 0, alpha))
            draw.text((tx, y), line, font=font_title, fill=(255, 255, 255, alpha))
            y += 78

        # Orange underline
        draw.rectangle([(REEL_W // 2 - 80, y + 10), (REEL_W // 2 + 80, y + 15)], fill=(*ORANGE, alpha))

        frame = _add_branding(frame)
        title_frames.append(np.array(frame.convert("RGB")))

    def make_frame_func(flist, fps_val):
        def mf(t):
            return flist[min(int(t * fps_val), len(flist) - 1)]
        return mf

    title_clip = ImageClip(title_frames[0]).with_duration(3)
    title_clip = title_clip.with_make_frame(make_frame_func(title_frames, fps))
    clips.append(title_clip)

    # Each tip (3 seconds each)
    for tip_idx, tip in enumerate(tips):
        tip_frames = []
        for f in range(3 * fps):
            progress = f / (3 * fps)
            frame = bg_photo.copy().convert("RGBA")
            draw = ImageDraw.Draw(frame)

            # Orange bars
            for i in range(6):
                p = i / 6
                r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * p)
                g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * p)
                b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * p)
                draw.rectangle([(0, i), (REEL_W, i + 1)], fill=(r, g, b))

            # Tip number circle
            alpha = min(255, int(255 * min(1.0, progress * 4)))
            cx, cy = REEL_W // 2, REEL_H // 2 - 180
            draw.ellipse([(cx - 50, cy - 50), (cx + 50, cy + 50)], fill=(*ORANGE, alpha))
            num_font = _font(FONT_BOLD, 52)
            num = str(tip_idx + 1)
            bbox = draw.textbbox((0, 0), num, font=num_font)
            nx = cx - (bbox[2] - bbox[0]) // 2
            draw.text((nx, cy - 28), num, font=num_font, fill=(255, 255, 255, alpha))

            # Tip text
            font_tip = _font(FONT_BOLD, 48)
            tip_lines = _wrap_text(tip, font_tip, REEL_W - 120, draw)
            y = REEL_H // 2 - 60
            for line in tip_lines:
                lx = _centered_x(draw, line, font_tip, REEL_W)
                draw.text((lx + 2, y + 2), line, font=font_tip, fill=(0, 0, 0, alpha))
                draw.text((lx, y), line, font=font_tip, fill=(255, 255, 255, alpha))
                y += 60

            frame = _add_branding(frame)
            tip_frames.append(np.array(frame.convert("RGB")))

        tip_clip = ImageClip(tip_frames[0]).with_duration(3)
        tip_clip = tip_clip.with_make_frame(make_frame_func(tip_frames, fps))
        clips.append(tip_clip)

    final = concatenate_videoclips(clips, method="compose")

    if save_path is None:
        save_path = str(PROJECT_ROOT / "reels" / "tips_reel.mp4")
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)

    final.write_videofile(str(save_path), fps=fps, codec="libx264", audio=False, preset="medium", logger=None)
    return str(save_path)


# ═══════════════════════════════════════════════════════════════════════════
# REEL 3: Quote Reel — Animated quote over photo
# ═══════════════════════════════════════════════════════════════════════════

def reel_quote(photo_query, quote, author="Mangalya Matrimony", save_path=None):
    """Create a reel with an animated quote appearing over a beautiful photo."""
    from moviepy import ImageClip

    photos = _fetch_photos(photo_query, count=1)
    if not photos:
        return None

    bg = _fit_photo_to_frame(photos[0])
    bg = _add_gradient(bg, "bottom", alpha=210, coverage=0.55)
    bg = _add_gradient(bg, "top", alpha=140, coverage=0.2)

    fps = 24
    duration = 8  # seconds
    total_frames = duration * fps
    frames = []

    words = quote.split()
    font_quote = _font(FONT_BOLD, 52)
    font_author = _font(FONT_ITALIC, 32)

    for f in range(total_frames):
        progress = f / total_frames
        frame = bg.copy().convert("RGBA")

        # Ken Burns
        frame_rgb = _ken_burns(frame.convert("RGB"), progress, "zoom_in")
        frame = frame_rgb.convert("RGBA")
        # Re-add gradient after zoom
        frame = _add_gradient(frame.convert("RGB"), "bottom", alpha=210, coverage=0.55).convert("RGBA")

        draw = ImageDraw.Draw(frame)

        # Orange top bar
        for i in range(5):
            p = i / 5
            r = int(ORANGE[0] + (RED[0] - ORANGE[0]) * p)
            g = int(ORANGE[1] + (RED[1] - ORANGE[1]) * p)
            b = int(ORANGE[2] + (RED[2] - ORANGE[2]) * p)
            draw.rectangle([(0, i), (REEL_W, i + 1)], fill=(r, g, b))

        # Reveal words progressively
        words_to_show = int(len(words) * min(1.0, progress * 1.8))
        visible_text = " ".join(words[:words_to_show])

        if visible_text:
            # Quote marks
            qm_font = _font(FONT_BOLD, 120)
            draw.text((80, REEL_H // 2 - 250), "\u201C", font=qm_font, fill=(*ORANGE, 180))

            lines = _wrap_text(visible_text, font_quote, REEL_W - 140, draw)
            y = REEL_H // 2 - 120
            for line in lines:
                lx = _centered_x(draw, line, font_quote, REEL_W)
                draw.text((lx + 2, y + 2), line, font=font_quote, fill=(0, 0, 0, 180))
                draw.text((lx, y), line, font=font_quote, fill=WHITE)
                y += 65

            # Author (appears after all words shown)
            if words_to_show >= len(words) and progress > 0.6:
                author_alpha = min(255, int(255 * (progress - 0.6) * 5))
                author_text = f"-- {author}"
                ax = _centered_x(draw, author_text, font_author, REEL_W)
                draw.text((ax, y + 30), author_text, font=font_author, fill=(*ORANGE, author_alpha))

        frame = _add_branding(frame)
        frames.append(np.array(frame.convert("RGB")))

    def make_frame(t):
        return frames[min(int(t * fps), len(frames) - 1)]

    clip = ImageClip(frames[0]).with_duration(duration).with_make_frame(make_frame)

    if save_path is None:
        save_path = str(PROJECT_ROOT / "reels" / "quote_reel.mp4")
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)

    clip.write_videofile(str(save_path), fps=fps, codec="libx264", audio=False, preset="medium", logger=None)
    return str(save_path)


# ═══════════════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    out_dir = PROJECT_ROOT / "reels"
    out_dir.mkdir(exist_ok=True)

    print("Generating Reels...\n")

    # 1. Quote Reel
    print("1. Generating Quote Reel...")
    reel_quote(
        "south indian bride gold jewelry portrait",
        "The strongest marriages are built on small honest conversations spoken with sincerity every single day",
        save_path=out_dir / "01_quote_reel.mp4",
    )
    print("[OK] Quote Reel (8 sec)")

    # 2. Tips Reel
    print("\n2. Generating Tips Reel...")
    reel_tips(
        "indian wedding couple romantic portrait",
        "5 Things to Discuss Before Marriage",
        [
            "Future goals and career dreams",
            "Family expectations",
            "Financial planning together",
            "Where to live",
            "Values and traditions",
        ],
        save_path=out_dir / "02_tips_reel.mp4",
    )
    print("[OK] Tips Reel (18 sec)")

    # 3. Slideshow Reel
    print("\n3. Generating Slideshow Reel...")
    reel_slideshow(
        "south indian wedding ceremony couple bride",
        [
            "Your Perfect Match Is Waiting",
            "Verified Profiles From Across South India",
            "Horoscope Matching & Family Values",
            "Register Free Today",
        ],
        save_path=out_dir / "03_slideshow_reel.mp4",
    )
    print("[OK] Slideshow Reel (16 sec)")

    print(f"\nAll reels saved to: {out_dir}")
