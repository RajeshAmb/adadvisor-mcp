"""
Lead Hunter Agent — Detects new signups and sends instant Telegram alerts.
Runs every 15 minutes via Task Scheduler.

How it works:
1. Queries Meta API for today's lead/registration counts per ad set
2. Compares with last known counts (stored in data/lead_counts.json)
3. If new leads detected → sends Telegram alert
4. Also sends daily summary at end of day
"""

from datetime import datetime
from base import BaseAgent
from telegram_bot import send_lead_alert, send_daily_summary, send_message


class LeadHunter(BaseAgent):
    name = "lead_hunter"

    # All active ad sets to monitor
    ADSETS = [
        {"adset_id": "120265125537550555", "name": "Telugu Parents 45-65", "lead_type": "lead"},
        {"adset_id": "120265125536690555", "name": "Telugu Women 23-33", "lead_type": "lead"},
        {"adset_id": "120265153511970555", "name": "AP Telangana Women 23-33 v2", "lead_type": "lead"},
        {"adset_id": "120265153509550555", "name": "Kerala Women 23-33", "lead_type": "lead"},
        {"adset_id": "120265153513430555", "name": "Tamil Nadu Women 23-33", "lead_type": "lead"},
        {"adset_id": "120265154082460555", "name": "Telugu Parents 38-58", "lead_type": "lead"},
    ]

    def __init__(self):
        super().__init__()
        self.counts_file = "lead_counts.json"

    def get_today_leads(self, adset_id, lead_type="lead"):
        """Get today's lead count for an ad set."""
        from facebook_business.adobjects.adset import AdSet
        self.init_meta()
        rows = AdSet(adset_id).get_insights(
            fields=["spend", "actions"],
            params={"date_preset": "today"},
        )
        if not rows:
            return 0, 0.0
        row = rows[0]
        leads = self._get_action_count(row.get("actions"), lead_type)
        spend = float(row.get("spend", 0))
        return leads, spend

    def run(self):
        self.log("=" * 50)
        self.log("LEAD HUNTER — Checking for new signups")

        today = datetime.now().strftime("%Y-%m-%d")
        last_counts = self.load_json(self.counts_file)

        # Reset counts if it's a new day
        if last_counts.get("date") != today:
            last_counts = {"date": today, "adsets": {}, "total_alerts_sent": 0}

        total_leads_today = 0
        total_spend_today = 0.0
        new_leads_found = False
        campaign_summaries = []

        for camp in self.ADSETS:
            aid = camp["adset_id"]
            try:
                leads, spend = self.get_today_leads(aid, camp["lead_type"])
            except Exception as e:
                self.log_error(f"Error checking {camp['name']}: {e}")
                continue

            prev_leads = last_counts.get("adsets", {}).get(aid, {}).get("leads", 0)
            new_count = leads - prev_leads

            total_leads_today += leads
            total_spend_today += spend

            campaign_summaries.append({
                "name": camp["name"],
                "leads": leads,
                "spend": spend,
                "cost_per_lead": round(spend / leads, 2) if leads > 0 else None,
                "status": "ACTIVE",
            })

            if new_count > 0:
                new_leads_found = True
                cpl = round(spend / leads, 2) if leads > 0 else 0
                self.log(f"NEW LEAD! {camp['name']}: +{new_count} (total: {leads})")

                send_lead_alert({
                    "campaign": camp["name"],
                    "adset": camp["name"],
                    "time": datetime.now().strftime("%I:%M %p"),
                    "total_today": leads,
                    "cost_per_lead": cpl,
                    "spend_today": f"{spend:.0f}",
                })

            # Update stored counts
            if "adsets" not in last_counts:
                last_counts["adsets"] = {}
            last_counts["adsets"][aid] = {"leads": leads, "spend": spend}

        last_counts["total_leads"] = total_leads_today
        last_counts["total_spend"] = total_spend_today
        self.save_json(self.counts_file, last_counts)

        if new_leads_found:
            self.log(f"Total today: {total_leads_today} leads, Rs.{total_spend_today:.0f} spent")
        else:
            self.log(f"No new leads. Total today: {total_leads_today} leads, Rs.{total_spend_today:.0f}")

        # Send daily summary at end of day (after 9 PM)
        hour = datetime.now().hour
        if hour >= 21 and not last_counts.get("summary_sent"):
            avg_cpl = round(total_spend_today / total_leads_today, 2) if total_leads_today > 0 else None
            send_daily_summary({
                "date": today,
                "campaigns": campaign_summaries,
                "total_leads": total_leads_today,
                "total_spend": total_spend_today,
                "avg_cpl": avg_cpl,
            })
            last_counts["summary_sent"] = True
            self.save_json(self.counts_file, last_counts)
            self.log("Daily summary sent to Telegram")

        self.log("Lead Hunter done.\n")


if __name__ == "__main__":
    LeadHunter().run()
