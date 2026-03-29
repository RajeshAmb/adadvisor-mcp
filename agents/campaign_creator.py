"""
Campaign Creator Agent — Auto-creates new campaigns based on winning patterns.

When the AI Brain identifies a winning ad set (good CTR + low CPL), this agent
replicates the winning formula for other communities/audiences.

Safety:
  - All campaigns created in PAUSED state
  - Max 2 new campaigns per run
  - Min 7 days between campaigns for same community
  - Telegram notification for manual approval before activation

Runs daily or every 12 hours via Task Scheduler.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

from base import BaseAgent
from telegram_bot import send_message as telegram_msg

# Import from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import ads_manager
import campaign_templates as templates

try:
    from content_creator import ContentCreator
    HAS_CONTENT = True
except ImportError:
    HAS_CONTENT = False


class CampaignCreator(BaseAgent):
    name = "campaign_creator"

    MAX_CAMPAIGNS_PER_RUN = 2
    MIN_CTR_THRESHOLD = 1.0       # % — ad set must have at least this CTR
    MAX_CPL_THRESHOLD = 60.0      # Rs — cost per lead must be below this
    MIN_LEADS_THRESHOLD = 5       # Minimum leads to qualify as "winning"
    MIN_DAYS_BETWEEN_CREATES = 7  # Don't create for same community within 7 days

    def __init__(self):
        super().__init__()
        self.creation_log = "campaign_creations.json"

    def find_winning_adsets(self):
        """Find ad sets that are performing well enough to replicate."""
        self.log("Scanning for winning ad sets (last 7 days)...")
        all_perf = self.get_all_adsets_performance("last_7d")
        winners = []

        for p in all_perf:
            ctr = p.get("ctr", 0)
            cpl = p.get("cost_per_lead")
            leads = p.get("leads", 0)

            if (ctr >= self.MIN_CTR_THRESHOLD
                    and cpl is not None
                    and cpl <= self.MAX_CPL_THRESHOLD
                    and leads >= self.MIN_LEADS_THRESHOLD):
                winners.append(p)
                self.log(
                    f"  WINNER: {p['name']} — CTR: {ctr:.2f}%, "
                    f"CPL: Rs.{cpl:.0f}, Leads: {leads}"
                )

        if not winners:
            self.log("No winning ad sets found — nothing to replicate")

        return winners

    def get_communities_without_active_campaigns(self):
        """Find community templates that don't have active campaigns."""
        all_perf = self.get_all_adsets_performance("last_3d")
        active_names = {p["name"].lower() for p in all_perf}

        available = {}
        for key, tmpl in templates.COMMUNITY_TEMPLATES.items():
            display = tmpl["display_name"].lower()
            # Check if any active ad set name contains this template's display name
            has_active = any(display in name for name in active_names)
            if not has_active:
                # Check creation cooldown
                if not self.is_recently_created(key):
                    available[key] = tmpl

        return available

    def is_recently_created(self, community_key):
        """Check if we created a campaign for this community within cooldown period."""
        log = self.load_json(self.creation_log)
        creations = log.get("creations", [])

        cutoff = (datetime.now() - timedelta(days=self.MIN_DAYS_BETWEEN_CREATES)).isoformat()
        for entry in creations:
            if entry.get("community_key") == community_key and entry.get("created_at", "") > cutoff:
                return True
        return False

    def generate_ad_copy(self, community, language):
        """Generate ad copy using Content Creator agent."""
        if not HAS_CONTENT:
            return self.fallback_copy(community)

        creator = ContentCreator()
        try:
            copies = creator.generate_ad_copy(
                target_audience=f"{community} community — parents and young adults seeking matrimony",
                language=language,
                theme="safe and verified profiles",
            )
            if copies and len(copies) > 0:
                return copies[0]  # Use first variation
        except Exception as e:
            self.log_error(f"Content generation failed: {e}")

        return self.fallback_copy(community)

    def fallback_copy(self, community):
        """Fallback ad copy if Claude API unavailable."""
        return {
            "headline": f"Find Verified {community} Matches",
            "primary_text": (
                f"Mangalya Matrimony — exclusively for {community} families. "
                "Every profile verified. Join free today!"
            ),
            "description": f"Trusted by {community} families",
            "cta": "SIGN_UP",
        }

    def create_campaign_pipeline(self, community_key, winning_adset=None):
        """Full pipeline: create campaign → ad set → creative → ad (all PAUSED)."""
        tmpl = templates.get_template(community_key)
        if not tmpl:
            self.log_error(f"No template for community: {community_key}")
            return None

        timestamp = datetime.now().strftime("%m%d")
        campaign_name = f"Mangalya-{tmpl['community']}-Auto-{timestamp}"

        self.log(f"Creating campaign: {campaign_name}")

        try:
            # Step 1: Create campaign (PAUSED)
            campaign = ads_manager.create_campaign(
                name=campaign_name,
                objective="OUTCOME_LEADS",
                status="PAUSED",
            )
            campaign_id = campaign["id"]
            self.log(f"  Campaign created: {campaign_id}")

            # Step 2: Create ad set with targeting (PAUSED)
            adset_name = f"{tmpl['display_name']} (Auto)"
            adset = ads_manager.create_adset(
                campaign_id=campaign_id,
                name=adset_name,
                daily_budget_cents=tmpl["default_budget_paise"],
                billing_event="IMPRESSIONS",
                optimization_goal="LEAD_GENERATION",
                targeting=tmpl["targeting"],
                status="PAUSED",
            )
            adset_id = adset["id"]
            self.log(f"  Ad set created: {adset_id} — {adset_name}")

            # Step 3: Generate ad copy
            copy = self.generate_ad_copy(tmpl["community"], tmpl.get("language", "English"))
            self.log(f"  Ad copy: {copy.get('headline', 'N/A')}")

            # Step 4: Create creative (reuse existing image or use default)
            creative = ads_manager.create_creative(
                name=f"{campaign_name}-creative",
                page_id=templates.PAGE_ID,
                image_hash=self.get_best_image_hash(),
                message=copy.get("primary_text", ""),
                link=templates.WEBSITE,
                headline=copy.get("headline", ""),
            )
            creative_id = creative["id"]
            self.log(f"  Creative created: {creative_id}")

            # Step 5: Create ad (PAUSED)
            ad = ads_manager.create_ad(
                adset_id=adset_id,
                creative_id=creative_id,
                name=f"{campaign_name}-ad",
                status="PAUSED",
            )
            ad_id = ad["id"]
            self.log(f"  Ad created: {ad_id}")

            # Log to database
            self.db.add_brain_decision(
                action_type="create_campaign",
                adset_id=adset_id,
                adset_name=adset_name,
                reason=f"Auto-created from winning pattern. Community: {tmpl['community']}",
                analysis_json=json.dumps({
                    "campaign_id": campaign_id,
                    "adset_id": adset_id,
                    "ad_id": ad_id,
                    "creative_id": creative_id,
                    "community_key": community_key,
                    "source_winner": winning_adset.get("name") if winning_adset else None,
                }),
            )

            # Log creation for cooldown tracking
            self.log_creation(community_key, campaign_id, adset_id, ad_id)

            # Store in campaigns/ad_sets tables
            self.db.upsert_campaign(campaign_id, campaign_name, "OUTCOME_LEADS", "PAUSED", "auto")
            self.db.upsert_adset(
                adset_id, campaign_id, adset_name,
                tmpl["default_budget_paise"], "PAUSED",
                json.dumps(tmpl["targeting"]),
            )

            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "adset_id": adset_id,
                "adset_name": adset_name,
                "ad_id": ad_id,
                "community": tmpl["community"],
                "budget": f"Rs.{tmpl['default_budget_paise'] // 100}/day",
            }

        except Exception as e:
            self.log_error(f"Campaign creation failed for {community_key}: {e}")
            return None

    def get_best_image_hash(self):
        """Get the image hash from the most recent successful ad, or a default."""
        # Try to get from existing creatives
        try:
            account = self.init_meta()
            creatives = account.get_ad_creatives(fields=["name", "image_hash"])
            for c in creatives:
                if c.get("image_hash"):
                    return c["image_hash"]
        except Exception:
            pass
        # Fallback — user must have at least one image uploaded
        return ""

    def log_creation(self, community_key, campaign_id, adset_id, ad_id):
        """Log campaign creation for cooldown tracking."""
        log = self.load_json(self.creation_log)
        if "creations" not in log:
            log["creations"] = []
        log["creations"].append({
            "community_key": community_key,
            "campaign_id": campaign_id,
            "adset_id": adset_id,
            "ad_id": ad_id,
            "created_at": datetime.now().isoformat(),
        })
        # Keep last 50 entries
        log["creations"] = log["creations"][-50:]
        self.save_json(self.creation_log, log)

    def run(self):
        self.log("=" * 50)
        self.log("CAMPAIGN CREATOR — Scanning for replication opportunities")

        # Step 1: Find winning ad sets
        winners = self.find_winning_adsets()
        if not winners:
            self.log("No winners found — exiting")
            self.log("Campaign Creator done.\n")
            return

        # Step 2: Find communities that need campaigns
        available = self.get_communities_without_active_campaigns()
        if not available:
            self.log("All communities already have active campaigns — nothing to create")
            self.log("Campaign Creator done.\n")
            return

        self.log(f"Available communities for new campaigns: {list(available.keys())}")

        # Step 3: Create campaigns (max 2 per run)
        created = []
        for community_key in list(available.keys())[:self.MAX_CAMPAIGNS_PER_RUN]:
            result = self.create_campaign_pipeline(
                community_key,
                winning_adset=winners[0],
            )
            if result:
                created.append(result)

        # Step 4: Notify via Telegram
        if created:
            lines = ["<b>CAMPAIGN CREATOR</b>\n"]
            for c in created:
                lines.append(
                    f"<b>{c['campaign_name']}</b>\n"
                    f"  Community: {c['community']}\n"
                    f"  Budget: {c['budget']}\n"
                    f"  Ad Set: {c['adset_name']}\n"
                    f"  Status: PAUSED (awaiting approval)\n"
                )
            lines.append(
                "\nTo activate, use Meta Ads Manager or the MCP tools:\n"
                "<code>resume_campaign(campaign_id)</code>"
            )
            telegram_msg("\n".join(lines))

            self.log(f"Created {len(created)} new campaigns (PAUSED)")
        else:
            self.log("No campaigns created this run")

        self.log("Campaign Creator done.\n")


if __name__ == "__main__":
    CampaignCreator().run()
