"""
Auto-optimizer for Mangalya campaigns.
Run daily: python optimize.py (scheduled at 9 AM via Task Scheduler)

Rules:
  - CTR < 0.5%                         → pause ad
  - Cost/Signup > Rs.150               → reduce budget by 25%
  - Cost/Signup < Rs.50 & signups >= 3 → increase budget by 25%
  - CTR >= 1% & signups >= 5           → increase budget by 50%
"""
from dotenv import load_dotenv
load_dotenv()

import config
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adset import AdSet

FacebookAdsApi.init(config.APP_ID, config.APP_SECRET, config.ACCESS_TOKEN)

ADSETS = [
    {"adset_id": "120265125537550555", "name": "Telugu Parents 45-65 (Lead)"},
    {"adset_id": "120265125536690555", "name": "Telugu Women 23-33 (Lead)"},
    {"adset_id": "120265153511970555", "name": "AP Telangana Women 23-33 (Lead v2)"},
    {"adset_id": "120265153509550555", "name": "Kerala Women 23-33 (Lead)"},
    {"adset_id": "120265153513430555", "name": "Tamil Nadu Women 23-33 (Lead)"},
    {"adset_id": "120265154082460555", "name": "Telugu Parents Campaign 38-58 (Lead)"},
]

FIELDS = ["impressions", "clicks", "spend", "ctr", "actions"]

MIN_CTR              = 0.5
MAX_COST_PER_LEAD    = 100
GOOD_COST_PER_LEAD   = 40
MIN_LEADS_TO_SCALE   = 3


def get_leads(actions):
    if not actions:
        return 0
    for a in actions:
        if a.get("action_type") == "lead":
            return int(a.get("value", 0))
    return 0


def adjust_budget(adset_id, current_paise, factor, reason):
    new_budget = max(int(current_paise * factor), 10000)
    AdSet(adset_id).api_update(params={"daily_budget": new_budget})
    print(f"    Budget: Rs.{current_paise//100}/day → Rs.{new_budget//100}/day ({reason})")


def optimize(camp):
    print(f"\n  [{camp['name']}]")

    adset = AdSet(camp["adset_id"])
    adset.api_get(fields=["daily_budget", "status"])
    current_budget = int(adset["daily_budget"])

    rows = adset.get_insights(fields=FIELDS, params={"date_preset": "last_3d"})
    if not rows:
        print("    No data yet — skipping.")
        return

    row         = rows[0]
    impressions = int(row.get("impressions", 0))
    spend       = float(row.get("spend", 0))
    ctr         = float(row.get("ctr", 0))
    leads       = get_leads(row.get("actions"))
    cpl         = spend / leads if leads > 0 else None

    print(f"    Impressions: {impressions} | CTR: {ctr:.2f}% | Spend: Rs.{spend:.2f} | Leads: {leads} | Cost/Lead: {'Rs.'+str(round(cpl,2)) if cpl else 'N/A'}")

    if impressions == 0:
        print("    ACTION: No impressions — check ad approval status.")
        return

    if ctr < MIN_CTR:
        adset.api_update(params={"status": "PAUSED"})
        print(f"    ACTION: PAUSED — CTR {ctr:.2f}% below {MIN_CTR}%. Review creative.")
        return

    if cpl and cpl > MAX_COST_PER_LEAD:
        adjust_budget(camp["adset_id"], current_budget, 0.75, f"Cost/Lead Rs.{cpl:.0f} too high")
        return

    if cpl and cpl < GOOD_COST_PER_LEAD and leads >= MIN_LEADS_TO_SCALE:
        factor = 1.5 if (ctr >= 1.0 and leads >= 5) else 1.25
        adjust_budget(camp["adset_id"], current_budget, factor, f"Cost/Lead Rs.{cpl:.0f} — scaling up")
        return

    print("    No changes — performance within acceptable range.")


if __name__ == "__main__":
    print("=" * 50)
    print("  MANGALYA ADS AUTO-OPTIMIZER")
    print("=" * 50)
    for camp in ADSETS:
        optimize(camp)
    print("\nDone.")
