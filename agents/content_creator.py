"""
Content Creator Agent — AI-generates ad copy and Instagram content.

Uses Claude API to create:
- Multiple ad copy variations for A/B testing
- Instagram post captions in multiple languages
- Headlines and CTAs optimized for matrimony signups

Runs daily or on-demand.
"""

import os
import json
from datetime import datetime
from base import BaseAgent
from telegram_bot import send_message

try:
    import anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False


class ContentCreator(BaseAgent):
    name = "content_creator"

    LANGUAGES = ["English", "Telugu", "Malayalam", "Tamil", "Kannada"]

    THEMES = [
        "finding true love", "trusting parents in matchmaking",
        "success stories", "safe and verified profiles",
        "free registration", "community-specific matching",
        "horoscope compatibility", "modern meets traditional",
        "wedding season", "family values",
    ]

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.content_file = "generated_content.json"

    def generate_ad_copy(self, target_audience, language="English", theme=None):
        """Generate ad copy variations using Claude."""
        if not HAS_CLAUDE or not self.api_key:
            return self.fallback_ad_copy(target_audience, language)

        client = anthropic.Anthropic(api_key=self.api_key)

        prompt = f"""Generate 3 Meta ad copy variations for Mangalya Matrimony (mangalyamatrimony.com).

Target Audience: {target_audience}
Language: {language} (write the ad in this language, with English transliteration if not English)
Theme: {theme or 'general matrimony signup'}
Website: mangalyamatrimony.com

Requirements:
- Each variation needs: headline (max 40 chars), primary_text (max 125 chars), description (max 30 chars)
- Focus on driving FREE registration/signup
- Emotional, relatable, culturally appropriate
- Include a clear CTA
- If regional language, keep it natural and warm

Return as JSON array:
[
  {{
    "headline": "...",
    "primary_text": "...",
    "description": "...",
    "cta": "SIGN_UP",
    "style": "emotional|practical|social_proof"
  }}
]"""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        text = message.content[0].text
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except json.JSONDecodeError:
            self.log_error(f"Could not parse ad copy response")
            return self.fallback_ad_copy(target_audience, language)

    def generate_instagram_caption(self, theme, language="English"):
        """Generate Instagram post caption."""
        if not HAS_CLAUDE or not self.api_key:
            return self.fallback_instagram_caption(theme)

        client = anthropic.Anthropic(api_key=self.api_key)

        prompt = f"""Write an Instagram post caption for Mangalyam Matrimony (@mangalyamatrimony).

Theme: {theme}
Language: {language}
Tone: Warm, hopeful, culturally resonant

Requirements:
- 3-5 lines of engaging caption text
- Include a CTA (visit mangalyamatrimony.com or register free)
- Add 15-20 relevant hashtags
- If not English, write naturally in that language

Return as JSON:
{{
  "caption": "...",
  "hashtags": "#tag1 #tag2 ...",
  "pexels_query": "search term for matching image"
}}"""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        text = message.content[0].text
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return self.fallback_instagram_caption(theme)

    def fallback_ad_copy(self, target_audience, language):
        """Pre-written ad copy when Claude API unavailable."""
        return [
            {
                "headline": "Find Your Perfect Match Free",
                "primary_text": "Join thousands of verified profiles on Mangalya Matrimony. Register free today!",
                "description": "Free Registration Now",
                "cta": "SIGN_UP",
                "style": "practical",
            },
            {
                "headline": "Your Life Partner Awaits",
                "primary_text": "Trusted by families across India. Safe, verified matrimony profiles. Start your journey.",
                "description": "Register Free Today",
                "cta": "SIGN_UP",
                "style": "emotional",
            },
            {
                "headline": "1000+ Happy Matches",
                "primary_text": "Find your soulmate on Mangalya Matrimony. Verified profiles, horoscope matching, free signup!",
                "description": "Join Free Now",
                "cta": "SIGN_UP",
                "style": "social_proof",
            },
        ]

    def fallback_instagram_caption(self, theme):
        """Pre-written Instagram caption."""
        return {
            "caption": f"Every love story begins with a single step. Take yours today with Mangalyam Matrimony.\n\nRegister free at mangalyamatrimony.com",
            "hashtags": "#MangalyamMatrimony #Matrimony #IndianWedding #FindYourMatch #Marriage #LoveStory #TeluguMatrimony #MalayalamMatrimony #FreeRegistration #VerifiedProfiles",
            "pexels_query": "indian wedding couple",
        }

    def run(self):
        self.log("=" * 50)
        self.log("CONTENT CREATOR — Generating fresh content")

        today = datetime.now().strftime("%Y-%m-%d")
        all_content = self.load_json(self.content_file)
        if today not in all_content:
            all_content[today] = {}

        # Generate ad copy for each target audience
        audiences = [
            ("Telugu Women 23-33, AP/Telangana", "Telugu"),
            ("Malayalam Women 23-33, Kerala", "Malayalam"),
            ("Tamil Women 23-33, Tamil Nadu", "Tamil"),
            ("Parents 40-60, finding match for children", "English"),
        ]

        for audience, lang in audiences:
            self.log(f"Generating ad copy: {audience} ({lang})")
            try:
                copies = self.generate_ad_copy(audience, lang)
                all_content[today][f"ad_copy_{lang.lower()}"] = copies
                self.log(f"  Generated {len(copies)} variations")
            except Exception as e:
                self.log_error(f"  Error: {e}")

        # Generate Instagram caption
        import random
        theme = random.choice(self.THEMES)
        lang = random.choice(self.LANGUAGES)
        self.log(f"Generating Instagram caption: {theme} ({lang})")
        try:
            caption = self.generate_instagram_caption(theme, lang)
            all_content[today]["instagram"] = caption
            self.log(f"  Caption generated ({len(caption.get('caption', ''))} chars)")
        except Exception as e:
            self.log_error(f"  Error: {e}")

        self.save_json(self.content_file, all_content)

        # Notify via Telegram
        total_copies = sum(
            len(v) for k, v in all_content[today].items()
            if k.startswith("ad_copy") and isinstance(v, list)
        )
        send_message(
            f"✍️ <b>Content Creator</b>\n\n"
            f"Generated {total_copies} ad copy variations\n"
            f"+ 1 Instagram caption ({lang})\n\n"
            f"Theme: {theme}\n"
            f"View in dashboard or data/generated_content.json"
        )

        self.log("Content Creator done.\n")


if __name__ == "__main__":
    ContentCreator().run()
