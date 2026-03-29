"""
Video Generator Agent — Full script-to-video-to-ad pipeline.

Pipeline:
  1. Claude API generates a video ad script (scenes, voiceover, overlays)
  2. Pictory AI renders the script into a video
  3. Video is uploaded to Meta as an ad creative
  4. Ad is created in PAUSED state for approval

Uses video_jobs table to track multi-step async pipeline.

Runs every 6-12 hours via Task Scheduler.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path

from base import BaseAgent
from telegram_bot import send_message as telegram_msg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import ads_manager
import campaign_templates as templates

try:
    import anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False

PICTORY_API_BASE = "https://api.pictory.ai/pictory/v1"
VIDEO_DIR = PROJECT_ROOT / "data" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)


class VideoGenerator(BaseAgent):
    name = "video_generator"

    MAX_VIDEOS_PER_RUN = 2
    MAX_VIDEOS_PER_WEEK = 5
    PICTORY_POLL_INTERVAL = 30  # seconds
    PICTORY_MAX_POLLS = 40      # 20 minutes max wait

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.pictory_api_key = os.getenv("PICTORY_API_KEY", "")
        self.pictory_user_id = os.getenv("PICTORY_USER_ID", "")

    # ── Step 1: Script Generation ─────────────────────────────────────────────

    def generate_script(self, community, theme="family values", language="English"):
        """Generate a 30-second video ad script using Claude."""
        if not HAS_CLAUDE or not self.api_key:
            return self.fallback_script(community, theme)

        client = anthropic.Anthropic(api_key=self.api_key)

        prompt = f"""Create a 30-second video ad script for Mangalya Matrimony (mangalyamatrimony.com).

Community: {community}
Theme: {theme}
Language: {language} (voiceover in this language, text overlays in English)

Requirements:
- 4-5 scenes, each 5-7 seconds
- Emotionally compelling — matrimony is a family decision
- Focus on trust, verification, and community specificity
- End with strong CTA: "Join Free Today"

Return as JSON:
{{
  "title": "Ad title",
  "duration_seconds": 30,
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 6,
      "visual_description": "What to show (for AI video generation)",
      "voiceover": "Voiceover text for this scene",
      "overlay_text": "Text overlay on screen",
      "transition": "fade|cut|slide"
    }}
  ],
  "music_mood": "uplifting|emotional|traditional",
  "cta_text": "Join Free Today",
  "cta_url": "mangalyamatrimony.com"
}}"""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
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
            self.log_error(f"Could not parse script JSON: {text[:200]}")
            return self.fallback_script(community, theme)

    def fallback_script(self, community, theme):
        """Fallback script if Claude is unavailable."""
        return {
            "title": f"Mangalya — Find Your {community} Match",
            "duration_seconds": 30,
            "scenes": [
                {
                    "scene_number": 1, "duration_seconds": 7,
                    "visual_description": "Happy South Indian family at home, warm lighting",
                    "voiceover": f"Finding the right match for your family is not easy.",
                    "overlay_text": "Every Family Deserves the Best Match",
                    "transition": "fade",
                },
                {
                    "scene_number": 2, "duration_seconds": 7,
                    "visual_description": "Young couple meeting, parents smiling in background",
                    "voiceover": f"Mangalya is built exclusively for {community} families.",
                    "overlay_text": f"Exclusively for {community} Families",
                    "transition": "slide",
                },
                {
                    "scene_number": 3, "duration_seconds": 8,
                    "visual_description": "Profile verification badge animation, trust symbols",
                    "voiceover": "Every profile is verified. Every match is meaningful.",
                    "overlay_text": "100% Verified Profiles",
                    "transition": "cut",
                },
                {
                    "scene_number": 4, "duration_seconds": 8,
                    "visual_description": "Wedding celebration, beautiful South Indian wedding",
                    "voiceover": "Join thousands of families who found their perfect match.",
                    "overlay_text": "Join Free Today — mangalyamatrimony.com",
                    "transition": "fade",
                },
            ],
            "music_mood": "emotional",
            "cta_text": "Join Free Today",
            "cta_url": "mangalyamatrimony.com",
        }

    # ── Step 2: Video Creation (Pictory AI) ───────────────────────────────────

    def create_video_pictory(self, script):
        """Send script to Pictory AI for video rendering. Returns job_id."""
        if not self.pictory_api_key:
            self.log("Pictory API not configured — skipping video creation")
            return None

        # Authenticate
        auth_resp = requests.post(
            f"{PICTORY_API_BASE}/oauth2/token",
            json={
                "client_id": self.pictory_api_key,
                "user_id": self.pictory_user_id,
            },
            timeout=30,
        )
        auth_resp.raise_for_status()
        token = auth_resp.json().get("access_token")

        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "X-Pictory-User-Id": self.pictory_user_id,
        }

        # Convert script to Pictory storyboard format
        storyboard_text = self.script_to_storyboard_text(script)

        # Create video from text (Text-to-Video)
        resp = requests.post(
            f"{PICTORY_API_BASE}/video/storyboard",
            headers=headers,
            json={
                "videoName": script.get("title", "Mangalya Ad"),
                "videoDescription": "Mangalya Matrimony advertisement",
                "language": "en",
                "scenes": [
                    {
                        "text": scene.get("voiceover", ""),
                        "voiceOver": True,
                    }
                    for scene in script.get("scenes", [])
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        job_id = resp.json().get("jobId") or resp.json().get("data", {}).get("jobId")

        self.log(f"Pictory job created: {job_id}")
        return job_id

    def poll_pictory_job(self, job_id):
        """Poll Pictory for job completion. Returns video URL or None."""
        if not self.pictory_api_key:
            return None

        # Re-authenticate
        auth_resp = requests.post(
            f"{PICTORY_API_BASE}/oauth2/token",
            json={
                "client_id": self.pictory_api_key,
                "user_id": self.pictory_user_id,
            },
            timeout=30,
        )
        auth_resp.raise_for_status()
        token = auth_resp.json().get("access_token")

        headers = {
            "Authorization": token,
            "X-Pictory-User-Id": self.pictory_user_id,
        }

        for i in range(self.PICTORY_MAX_POLLS):
            resp = requests.get(
                f"{PICTORY_API_BASE}/jobs/{job_id}",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status") or data.get("data", {}).get("status")

            if status == "completed":
                video_url = (
                    data.get("videoURL")
                    or data.get("data", {}).get("videoURL")
                )
                self.log(f"Pictory job {job_id} completed: {video_url}")
                return video_url
            elif status in ("failed", "error"):
                self.log_error(f"Pictory job {job_id} failed: {data}")
                return None

            self.log(f"Pictory job {job_id} status: {status} (poll {i+1}/{self.PICTORY_MAX_POLLS})")
            time.sleep(self.PICTORY_POLL_INTERVAL)

        self.log_error(f"Pictory job {job_id} timed out after {self.PICTORY_MAX_POLLS} polls")
        return None

    def download_video(self, url, filename):
        """Download video from URL to local file."""
        path = VIDEO_DIR / filename
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        self.log(f"Video downloaded: {path} ({path.stat().st_size / 1024:.0f} KB)")
        return str(path)

    def script_to_storyboard_text(self, script):
        """Convert script JSON to a readable storyboard text."""
        lines = [script.get("title", "Mangalya Ad"), ""]
        for scene in script.get("scenes", []):
            lines.append(f"Scene {scene['scene_number']} ({scene['duration_seconds']}s):")
            lines.append(f"  Visual: {scene['visual_description']}")
            lines.append(f"  VO: {scene['voiceover']}")
            if scene.get("overlay_text"):
                lines.append(f"  Text: {scene['overlay_text']}")
            lines.append("")
        return "\n".join(lines)

    # ── Step 3: Upload to Meta ────────────────────────────────────────────────

    def upload_video_to_meta(self, video_path):
        """Upload video to Meta Ad Account. Returns video_id."""
        self.init_meta()
        from facebook_business.adobjects.advideo import AdVideo
        from facebook_business.adobjects.adaccount import AdAccount
        import config

        account = AdAccount(config.AD_ACCOUNT_ID)
        video = account.create_ad_video(params={
            AdVideo.Field.name: f"Mangalya-Video-{datetime.now().strftime('%Y%m%d-%H%M')}",
            AdVideo.Field.filepath: video_path,
        })
        video_id = video.get("id")
        self.log(f"Video uploaded to Meta: {video_id}")
        return video_id

    def create_video_creative(self, video_id, ad_copy):
        """Create a Meta ad creative using a video."""
        from facebook_business.adobjects.adcreative import AdCreative
        from facebook_business.adobjects.adaccount import AdAccount
        import config
        import campaign_templates as tmpl

        account = AdAccount(config.AD_ACCOUNT_ID)
        creative = account.create_ad_creative(params={
            AdCreative.Field.name: f"Mangalya-VideoCreative-{datetime.now().strftime('%Y%m%d')}",
            AdCreative.Field.object_story_spec: {
                "page_id": tmpl.PAGE_ID,
                "video_data": {
                    "video_id": video_id,
                    "message": ad_copy.get("primary_text", "Find your perfect South Indian match"),
                    "title": ad_copy.get("headline", "Mangalya Matrimony"),
                    "link_description": ad_copy.get("description", "Join Free Today"),
                    "call_to_action": {
                        "type": "SIGN_UP",
                        "value": {"link": tmpl.WEBSITE},
                    },
                },
            },
        })
        creative_id = creative["id"]
        self.log(f"Video creative created: {creative_id}")
        return creative_id

    # ── Pipeline orchestration ────────────────────────────────────────────────

    def process_new_jobs(self):
        """Generate scripts and start video rendering for communities needing fresh content."""
        communities_needing_video = self.identify_communities_needing_video()
        created = 0

        for community_key in communities_needing_video[:self.MAX_VIDEOS_PER_RUN]:
            tmpl = templates.get_template(community_key)
            if not tmpl:
                continue

            theme = "family values" if "parents" in community_key else "modern matching"

            # Generate script
            self.log(f"Generating script for {community_key}...")
            script = self.generate_script(
                tmpl["community"], theme, tmpl.get("language", "English")
            )

            # Create job in DB
            job_id = self.db.create_video_job(
                community=community_key,
                theme=theme,
                script_json=json.dumps(script),
                provider="pictory",
            )
            self.log(f"Video job #{job_id} created for {community_key}")

            # Start Pictory rendering
            if self.pictory_api_key:
                try:
                    pictory_job_id = self.create_video_pictory(script)
                    if pictory_job_id:
                        self.db.update_video_job(
                            job_id,
                            status="rendering",
                            provider_job_id=pictory_job_id,
                        )
                except Exception as e:
                    self.log_error(f"Pictory job creation failed: {e}")
                    self.db.update_video_job(job_id, status="script_generated",
                                            error_message=str(e))
            else:
                self.log(f"Pictory not configured — job #{job_id} saved as script only")

            created += 1

        return created

    def process_rendering_jobs(self):
        """Check on jobs that are currently rendering."""
        rendering = self.db.get_video_jobs(status="rendering")
        completed = 0

        for job in rendering:
            pictory_job_id = job.get("provider_job_id")
            if not pictory_job_id:
                continue

            try:
                video_url = self.poll_pictory_job(pictory_job_id)
                if video_url:
                    filename = f"mangalya_{job['community']}_{job['id']}.mp4"
                    local_path = self.download_video(video_url, filename)
                    self.db.update_video_job(
                        job["id"],
                        status="rendered",
                        video_local_path=local_path,
                    )
                    completed += 1
                # If poll returns None but didn't fail, it's still rendering — leave it
            except Exception as e:
                self.log_error(f"Rendering check failed for job #{job['id']}: {e}")
                self.db.update_video_job(job["id"], error_message=str(e))

        return completed

    def process_rendered_jobs(self):
        """Upload rendered videos to Meta and create ads."""
        rendered = self.db.get_video_jobs(status="rendered")
        uploaded = 0

        for job in rendered:
            video_path = job.get("video_local_path")
            if not video_path or not Path(video_path).exists():
                self.db.update_video_job(job["id"], status="failed",
                                        error_message="Video file not found")
                continue

            try:
                # Upload to Meta
                video_id = self.upload_video_to_meta(video_path)
                self.db.update_video_job(job["id"], status="uploaded",
                                        meta_video_id=video_id)

                # Create creative
                script = json.loads(job.get("script_json", "{}"))
                ad_copy = {
                    "headline": script.get("title", "Mangalya Matrimony"),
                    "primary_text": script.get("scenes", [{}])[0].get("voiceover", ""),
                    "description": script.get("cta_text", "Join Free Today"),
                }
                creative_id = self.create_video_creative(video_id, ad_copy)
                self.db.update_video_job(job["id"], meta_creative_id=creative_id,
                                        status="ad_created")

                uploaded += 1

                # Notify
                telegram_msg(
                    f"<b>VIDEO AD READY</b>\n"
                    f"Community: {job['community']}\n"
                    f"Creative ID: {creative_id}\n"
                    f"Status: PAUSED — assign to an ad set to activate"
                )

            except Exception as e:
                self.log_error(f"Upload failed for job #{job['id']}: {e}")
                self.db.update_video_job(job["id"], status="failed",
                                        error_message=str(e))

        return uploaded

    def identify_communities_needing_video(self):
        """Identify which communities need fresh video content."""
        # Get communities that have active campaigns but no recent video jobs
        all_communities = templates.get_all_communities()
        recent_jobs = self.db.get_video_jobs(limit=50)

        # Communities with video jobs in the last 7 days
        recent_community_set = set()
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        for job in recent_jobs:
            if job.get("created_at", "") > cutoff:
                recent_community_set.add(job.get("community"))

        return [c for c in all_communities if c not in recent_community_set]

    def run(self):
        self.log("=" * 50)
        self.log("VIDEO GENERATOR — Processing video pipeline")

        # Step 1: Create new video jobs (script → render)
        new_count = self.process_new_jobs()
        self.log(f"New jobs created: {new_count}")

        # Step 2: Check rendering progress
        render_count = self.process_rendering_jobs()
        self.log(f"Renders completed: {render_count}")

        # Step 3: Upload completed videos to Meta
        upload_count = self.process_rendered_jobs()
        self.log(f"Videos uploaded: {upload_count}")

        # Summary
        all_jobs = self.db.get_video_jobs(limit=10)
        status_summary = {}
        for j in all_jobs:
            s = j.get("status", "unknown")
            status_summary[s] = status_summary.get(s, 0) + 1

        self.log(f"Job status summary: {status_summary}")

        if new_count > 0 or render_count > 0 or upload_count > 0:
            telegram_msg(
                f"<b>Video Generator</b>\n"
                f"New scripts: {new_count}\n"
                f"Renders done: {render_count}\n"
                f"Uploaded: {upload_count}\n"
                f"Pipeline: {status_summary}"
            )

        self.log("Video Generator done.\n")


# Need this import for identify_communities_needing_video
from datetime import timedelta

if __name__ == "__main__":
    VideoGenerator().run()
