#!/usr/bin/env python3
"""Meta Ads MCP Server for Mangalya Matrimony"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

import config
from mcp.server.fastmcp import FastMCP
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet

mcp = FastMCP("Meta Ads – Mangalya Matrimony")


def _init():
    FacebookAdsApi.init(config.APP_ID, config.APP_SECRET, config.ACCESS_TOKEN)
    return AdAccount(config.AD_ACCOUNT_ID)


def _get_action(actions, action_type):
    if not actions:
        return 0
    for a in actions:
        if a.get("action_type") == action_type:
            return int(a.get("value", 0))
    return 0


@mcp.tool()
def get_campaigns() -> str:
    """List all campaigns in the Mangalya ad account with their ID, status, and objective."""
    account = _init()
    campaigns = account.get_campaigns(fields=[
        Campaign.Field.id,
        Campaign.Field.name,
        Campaign.Field.status,
        Campaign.Field.objective,
    ])
    lines = []
    for c in campaigns:
        lines.append(f"[{c['status']}] {c['id']} — {c['name']} ({c['objective']})")
    return "\n".join(lines) if lines else "No campaigns found."


@mcp.tool()
def get_report(date_preset: str = "last_7d") -> str:
    """Get performance report for all campaigns.

    date_preset options: today, yesterday, last_7d, last_14d, last_30d, this_month, last_month
    """
    account = _init()
    insights = account.get_insights(fields=[
        "campaign_name", "campaign_id", "impressions", "reach",
        "clicks", "spend", "ctr", "cpc", "actions",
    ], params={
        "date_preset": date_preset,
        "level": "campaign",
    })
    lines = [f"MANGALYA ADS REPORT ({date_preset})", "=" * 50]
    for row in insights:
        spend = float(row.get("spend", 0))
        signups = _get_action(row.get("actions"), "complete_registration")
        cost_per_signup = f"Rs.{spend/signups:.2f}" if signups > 0 else "N/A"
        lines.append(f"\n{row.get('campaign_name')} ({row.get('campaign_id')})")
        lines.append(f"  Impressions : {row.get('impressions', 0)}")
        lines.append(f"  Reach       : {row.get('reach', 0)}")
        lines.append(f"  Clicks      : {row.get('clicks', 0)}")
        lines.append(f"  CTR         : {row.get('ctr', 0)}%")
        lines.append(f"  Spend       : Rs.{spend:.2f}")
        lines.append(f"  CPC         : Rs.{float(row.get('cpc', 0)):.2f}")
        lines.append(f"  Signups     : {signups}")
        lines.append(f"  Cost/Signup : {cost_per_signup}")
    return "\n".join(lines) if len(lines) > 2 else "No data for this period."


@mcp.tool()
def get_adsets(campaign_id: str) -> str:
    """List ad sets for a given campaign ID with their budget and status."""
    _init()
    campaign = Campaign(campaign_id)
    adsets = campaign.get_ad_sets(fields=[
        AdSet.Field.id,
        AdSet.Field.name,
        AdSet.Field.status,
        AdSet.Field.daily_budget,
    ])
    lines = []
    for a in adsets:
        budget = int(a.get("daily_budget", 0)) / 100
        lines.append(f"[{a['status']}] {a['id']} — {a['name']} (Rs.{budget:.0f}/day)")
    return "\n".join(lines) if lines else "No ad sets found."


@mcp.tool()
def update_budget(adset_id: str, daily_budget_rupees: float) -> str:
    """Update the daily budget for an ad set.

    Args:
        adset_id: The ad set ID (e.g. 120265075040130555)
        daily_budget_rupees: Budget in Rupees (e.g. 300 = Rs.300/day)
    """
    _init()
    adset = AdSet(adset_id)
    budget_paise = int(daily_budget_rupees * 100)
    adset.api_update(params={AdSet.Field.daily_budget: budget_paise})
    return f"Ad set {adset_id} budget updated to Rs.{daily_budget_rupees:.0f}/day."


@mcp.tool()
def pause_campaign(campaign_id: str) -> str:
    """Pause a campaign by its ID."""
    _init()
    campaign = Campaign(campaign_id)
    campaign.api_update(params={Campaign.Field.status: "PAUSED"})
    return f"Campaign {campaign_id} paused."


@mcp.tool()
def resume_campaign(campaign_id: str) -> str:
    """Resume (set to ACTIVE) a campaign by its ID."""
    _init()
    campaign = Campaign(campaign_id)
    campaign.api_update(params={Campaign.Field.status: "ACTIVE"})
    return f"Campaign {campaign_id} resumed."


@mcp.tool()
def pause_adset(adset_id: str) -> str:
    """Pause an ad set by its ID."""
    _init()
    adset = AdSet(adset_id)
    adset.api_update(params={AdSet.Field.status: "PAUSED"})
    return f"Ad set {adset_id} paused."


@mcp.tool()
def resume_adset(adset_id: str) -> str:
    """Resume (set to ACTIVE) an ad set by its ID."""
    _init()
    adset = AdSet(adset_id)
    adset.api_update(params={AdSet.Field.status: "ACTIVE"})
    return f"Ad set {adset_id} resumed."


# ── Thresholds (matches optimize.py) ───────────────────────────────────────────
MIN_CTR              = 0.5
MAX_COST_PER_SIGNUP  = 150
GOOD_COST_PER_SIGNUP = 50
MIN_SIGNUPS_TO_SCALE = 3

ADSETS = [
    {"adset_id": "120265076173980555", "name": "mangalya-03 (Kerala)"},
    {"adset_id": "120265076175510555", "name": "Mangalya-01 (AP & Telangana)"},
]


@mcp.tool()
def analyze_campaigns(date_preset: str = "last_3d") -> str:
    """Analyze each ad set's performance and flag issues.

    Returns metrics + a status for each ad set:
    PAUSED_LOW_CTR, EXPENSIVE, SCALING, OK, NO_DATA.

    date_preset options: today, yesterday, last_3d, last_7d, last_14d, last_30d
    """
    _init()
    lines = [f"CAMPAIGN ANALYSIS ({date_preset})", "=" * 50]

    for camp in ADSETS:
        adset = AdSet(camp["adset_id"])
        adset.api_get(fields=["daily_budget", "status"])
        current_budget = int(adset["daily_budget"])
        status = adset["status"]

        rows = adset.get_insights(
            fields=["impressions", "clicks", "spend", "ctr", "actions"],
            params={"date_preset": date_preset},
        )

        lines.append(f"\n{camp['name']} (adset {camp['adset_id']})")
        lines.append(f"  Status        : {status} | Budget: Rs.{current_budget // 100}/day")

        if not rows:
            lines.append("  Data          : No data for this period")
            lines.append("  FLAG          : NO_DATA")
            continue

        row         = rows[0]
        impressions = int(row.get("impressions", 0))
        spend       = float(row.get("spend", 0))
        ctr         = float(row.get("ctr", 0))
        signups     = _get_action(row.get("actions"), "complete_registration")
        cps         = spend / signups if signups > 0 else None

        lines.append(f"  Impressions   : {impressions}")
        lines.append(f"  Clicks        : {row.get('clicks', 0)}")
        lines.append(f"  Spend         : Rs.{spend:.2f}")
        lines.append(f"  CTR           : {ctr:.2f}%")
        lines.append(f"  Signups       : {signups}")
        lines.append(f"  Cost/Signup   : {'Rs.' + str(round(cps, 2)) if cps else 'N/A'}")

        if impressions == 0:
            flag = "NO_IMPRESSIONS — check ad approval"
        elif ctr < MIN_CTR:
            flag = f"PAUSED_LOW_CTR — CTR {ctr:.2f}% below {MIN_CTR}% threshold"
        elif cps and cps > MAX_COST_PER_SIGNUP:
            flag = f"EXPENSIVE — Cost/Signup Rs.{cps:.0f} exceeds Rs.{MAX_COST_PER_SIGNUP} limit"
        elif cps and cps < GOOD_COST_PER_SIGNUP and signups >= MIN_SIGNUPS_TO_SCALE:
            scale = "50%" if (ctr >= 1.0 and signups >= 5) else "25%"
            flag = f"SCALING — Cost/Signup Rs.{cps:.0f} is good, eligible for +{scale} budget increase"
        else:
            flag = "OK — within acceptable range"

        lines.append(f"  FLAG          : {flag}")

    return "\n".join(lines)


@mcp.tool()
def get_recommendations(date_preset: str = "last_3d") -> str:
    """Generate actionable budget and creative recommendations for each ad set.

    Based on the same rules as the daily auto-optimizer:
    - CTR < 0.5% → pause
    - Cost/Signup > Rs.150 → cut budget 25%
    - Cost/Signup < Rs.50 with 3+ signups → raise budget 25%
    - CTR >= 1% with 5+ signups → raise budget 50%

    date_preset options: today, yesterday, last_3d, last_7d, last_14d, last_30d
    """
    _init()
    lines = [f"RECOMMENDATIONS ({date_preset})", "=" * 50]
    has_action = False

    for camp in ADSETS:
        adset = AdSet(camp["adset_id"])
        adset.api_get(fields=["daily_budget", "status"])
        current_budget = int(adset["daily_budget"])

        rows = adset.get_insights(
            fields=["impressions", "clicks", "spend", "ctr", "actions"],
            params={"date_preset": date_preset},
        )

        if not rows:
            lines.append(f"\n{camp['name']}: No data — skip.")
            continue

        row         = rows[0]
        impressions = int(row.get("impressions", 0))
        spend       = float(row.get("spend", 0))
        ctr         = float(row.get("ctr", 0))
        signups     = _get_action(row.get("actions"), "complete_registration")
        cps         = spend / signups if signups > 0 else None
        budget_rs   = current_budget // 100

        lines.append(f"\n{camp['name']}")

        if impressions == 0:
            lines.append("  ACTION: Check ad approval status — 0 impressions.")
            has_action = True
        elif ctr < MIN_CTR:
            lines.append(f"  ACTION: PAUSE this ad set.")
            lines.append(f"  WHY:    CTR is {ctr:.2f}% — below the {MIN_CTR}% minimum.")
            lines.append(f"  NEXT:   Refresh the creative (image/copy) before re-enabling.")
            has_action = True
        elif cps and cps > MAX_COST_PER_SIGNUP:
            new_budget = max(int(budget_rs * 0.75), 100)
            lines.append(f"  ACTION: Reduce budget Rs.{budget_rs} → Rs.{new_budget}/day (-25%).")
            lines.append(f"  WHY:    Cost/Signup Rs.{cps:.0f} exceeds Rs.{MAX_COST_PER_SIGNUP} limit.")
            lines.append(f"  NEXT:   Monitor for 3 days. If no improvement, review targeting.")
            has_action = True
        elif cps and cps < GOOD_COST_PER_SIGNUP and signups >= MIN_SIGNUPS_TO_SCALE:
            if ctr >= 1.0 and signups >= 5:
                factor, label = 1.50, "+50%"
            else:
                factor, label = 1.25, "+25%"
            new_budget = int(budget_rs * factor)
            lines.append(f"  ACTION: Increase budget Rs.{budget_rs} → Rs.{new_budget}/day ({label}).")
            lines.append(f"  WHY:    Cost/Signup Rs.{cps:.0f} is well under Rs.{GOOD_COST_PER_SIGNUP}, {signups} signups.")
            lines.append(f"  NEXT:   Scale gradually. Reassess in 3 days.")
            has_action = True
        else:
            lines.append(f"  No changes needed — performance is acceptable.")
            lines.append(f"  CTR: {ctr:.2f}% | Cost/Signup: {'Rs.'+str(round(cps,2)) if cps else 'N/A'} | Signups: {signups}")

    if not has_action:
        lines.append("\nAll campaigns are performing within acceptable range.")

    return "\n".join(lines)


# ASGI app for deployment (uvicorn mcp_server:app)
app = mcp.sse_app()

if __name__ == "__main__":
    mcp.run(transport="stdio")
