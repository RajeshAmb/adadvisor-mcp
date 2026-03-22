"""
Performance report for all Mangalya campaigns
Run: python report.py
"""
from dotenv import load_dotenv
load_dotenv()

import config
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adset import AdSet

FacebookAdsApi.init(config.APP_ID, config.APP_SECRET, config.ACCESS_TOKEN)

ADSETS = [
    {
        "id": "120265117466040555",
        "name": "Mangalya-Telugu-01",
        "targeting": "South India · Female · 23-33 · 9AM-10PM",
    },
]

FIELDS = ["impressions", "reach", "clicks", "spend", "ctr", "cpc", "actions"]

DATE_PRESET = "last_7d"   # today | yesterday | last_7d | last_30d


def get_action(actions, action_type):
    if not actions:
        return 0
    for a in actions:
        if a.get("action_type") == action_type:
            return int(a.get("value", 0))
    return 0


def print_row(label, targeting, row):
    signups = get_action(row.get("actions"), "complete_registration")
    spend   = float(row.get("spend", 0))
    cost_per_signup = f"Rs.{spend/signups:.2f}" if signups > 0 else "N/A"

    print(f"""
  {label}
  {targeting}
  ─────────────────────────────
  Impressions  : {row.get('impressions', 0)}
  Reach        : {row.get('reach', 0)}
  Clicks       : {row.get('clicks', 0)}
  CTR          : {row.get('ctr', 0)}%
  Spend        : Rs.{spend:.2f}
  CPC          : Rs.{float(row.get('cpc', 0)):.2f}
  Signups      : {signups}
  Cost/Signup  : {cost_per_signup}
""")


if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"  MANGALYA ADS REPORT  ({DATE_PRESET})")
    print(f"{'='*50}")

    for adset in ADSETS:
        rows = AdSet(adset["id"]).get_insights(
            fields=FIELDS,
            params={"date_preset": DATE_PRESET}
        )
        if rows:
            print_row(adset["name"], adset["targeting"], rows[0])
        else:
            print(f"\n  {adset['name']} ({adset['targeting']})")
            print("  No data yet for this period.\n")
