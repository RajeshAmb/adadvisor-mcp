"""
Checks ad status every 4 hours and sends email.
- Sends approval notification when ads go ACTIVE
- Sends performance report with current stats
- Auto-adjusts: increases budget if CPL < Rs.50, reduces if CPL > Rs.150,
  pauses ad if CTR < 0.3% with > 1000 impressions and zero leads
Run: python status_check.py (scheduled every 4 hours)
"""
from dotenv import load_dotenv
load_dotenv()

import os, smtplib, json, config
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet

FacebookAdsApi.init(config.APP_ID, config.APP_SECRET, config.ACCESS_TOKEN)

# All 3 active campaigns
ADS = [
    {
        "ad_id":     "120265117466930555",
        "adset_id":  "120265117466040555",
        "name":      "Mangalya-Telugu-01 (Reach)",
        "targeting": "South India · Female · 23-33",
        "lead_type": "complete_registration",
    },
    {
        "ad_id":     "120265125537240555",
        "adset_id":  "120265125536690555",
        "name":      "Telugu Women Lead Form (23-33)",
        "targeting": "AP & Telangana · Female · 23-33 · Telugu",
        "lead_type": "lead",
    },
    {
        "ad_id":     "120265125537890555",
        "adset_id":  "120265125537550555",
        "name":      "Telugu Parents Lead Form (45-65)",
        "targeting": "AP & Telangana · Parents · 45-65 · Telugu",
        "lead_type": "lead",
    },
]

FIELDS      = ["impressions", "reach", "clicks", "spend", "ctr", "cpc", "actions"]
STATUS_FILE = "C:/Users/ambav/meta-ads-manager/last_status.json"


def get_action_count(actions, action_type):
    if not actions:
        return 0
    for a in actions:
        if a.get("action_type") == action_type:
            return int(a.get("value", 0))
    return 0


def load_last_status():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except:
        return {}


def save_status(status):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f)


def get_insights(adset_id):
    try:
        rows = AdSet(adset_id).get_insights(fields=FIELDS, params={"date_preset": "today"})
        return rows[0] if rows else {}
    except:
        return {}


def auto_adjust(ad_id, adset_id, name, spend, leads, impressions, ctr_str):
    """
    Auto-adjust based on performance:
    - CPL > Rs.150 → reduce budget by 20%
    - CPL < Rs.50  → increase budget by 20%
    - CTR < 0.3% AND impressions > 1000 AND zero leads → pause ad
    Returns list of action strings for the email report.
    """
    actions_taken = []
    impressions = int(impressions) if impressions else 0
    ctr = float(ctr_str) if ctr_str else 0.0

    # Pause if very poor performance (no leads + low CTR + enough impressions)
    if impressions > 1000 and leads == 0 and ctr < 0.3:
        try:
            Ad(ad_id).api_update(params={"status": "PAUSED"})
            actions_taken.append(f"PAUSED {name} — CTR {ctr:.2f}% < 0.3% with {impressions} impressions and 0 leads")
        except Exception as e:
            actions_taken.append(f"Could not pause {name}: {e}")
        return actions_taken

    if spend == 0 or leads == 0:
        return actions_taken

    cpl = spend / leads
    try:
        adset = AdSet(adset_id)
        adset.api_get(fields=["daily_budget", "lifetime_budget"])
        daily    = int(adset.get("daily_budget", 0) or 0)
        lifetime = int(adset.get("lifetime_budget", 0) or 0)
        budget      = daily or lifetime
        budget_type = "daily_budget" if daily else "lifetime_budget"

        if cpl > 150 and budget > 5000:
            new_budget = int(budget * 0.8)
            AdSet(adset_id).api_update(params={budget_type: new_budget})
            actions_taken.append(
                f"Budget reduced for {name} — CPL Rs.{cpl:.0f} > Rs.150 "
                f"(Rs.{budget/100:.0f} -> Rs.{new_budget/100:.0f})"
            )
        elif cpl < 50 and budget < 100000:
            new_budget = int(budget * 1.2)
            AdSet(adset_id).api_update(params={budget_type: new_budget})
            actions_taken.append(
                f"Budget increased for {name} — CPL Rs.{cpl:.0f} < Rs.50 "
                f"(Rs.{budget/100:.0f} -> Rs.{new_budget/100:.0f})"
            )
    except Exception as e:
        actions_taken.append(f"Auto-adjust skipped for {name}: {e}")

    return actions_taken


def send_email(subject, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = os.getenv("EMAIL_FROM")
    msg["To"]      = os.getenv("EMAIL_TO")
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
        server.sendmail(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_TO"), msg.as_string())
    print(f"Email sent: {subject}")


def status_badge(status):
    colors = {
        "ACTIVE":         "#27ae60",
        "PENDING_REVIEW": "#f39c12",
        "PAUSED":         "#7f8c8d",
        "WITH_ISSUES":    "#e74c3c",
        "DISAPPROVED":    "#e74c3c",
    }
    color = colors.get(status, "#333")
    return f'<span style="background:{color};color:white;padding:3px 8px;border-radius:4px;font-size:12px">{status}</span>'


def build_email(ads_data, newly_approved, all_adjustments):
    rows_html   = ""
    total_spend = 0
    total_leads = 0

    for a in ads_data:
        ins   = a["insights"]
        spend = float(ins.get("spend", 0))
        leads = get_action_count(ins.get("actions"), a["lead_type"])
        cpl   = f"Rs.{spend/leads:.2f}" if leads > 0 else "N/A"
        total_spend += spend
        total_leads += leads

        rows_html += f"""
        <tr>
            <td><b>{a['name']}</b><br><small style='color:#888'>{a['targeting']}</small></td>
            <td>{status_badge(a['status'])}</td>
            <td>{ins.get('impressions', 0)}</td>
            <td>{ins.get('reach', 0)}</td>
            <td>{ins.get('clicks', 0)}</td>
            <td>{ins.get('ctr', 0)}%</td>
            <td>Rs.{spend:.2f}</td>
            <td>{leads}</td>
            <td>{cpl}</td>
        </tr>"""

    cpl_total = f"Rs.{total_spend/total_leads:.2f}" if total_leads > 0 else "N/A"

    approval_banner = ""
    if newly_approved:
        names = ", ".join(newly_approved)
        approval_banner = f"""
        <div style="background:#27ae60;color:white;padding:15px;border-radius:6px;margin-bottom:20px">
            <b>Ad(s) approved and now LIVE!</b><br>{names}
        </div>"""

    adj_html = ""
    if all_adjustments:
        items = "".join(f"<li>{x}</li>" for x in all_adjustments)
        adj_html = f"""
        <div style="background:#eaf4fb;border-left:4px solid #2980b9;padding:12px;margin-top:16px;border-radius:4px">
            <b>Auto-Adjustments Made:</b>
            <ul style="margin:6px 0 0 0">{items}</ul>
        </div>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:750px;margin:auto">
    <h2 style="color:#c0392b">Mangalya Matrimony — Ads Report</h2>
    {approval_banner}

    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:13px">
        <thead style="background:#c0392b;color:white">
            <tr>
                <th>Campaign</th>
                <th>Status</th>
                <th>Impressions</th>
                <th>Reach</th>
                <th>Clicks</th>
                <th>CTR</th>
                <th>Spend</th>
                <th>Leads</th>
                <th>Cost/Lead</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
        <tfoot style="background:#f5f5f5;font-weight:bold">
            <tr>
                <td colspan="6">Total (Today)</td>
                <td>Rs.{total_spend:.2f}</td>
                <td>{total_leads}</td>
                <td>{cpl_total}</td>
            </tr>
        </tfoot>
    </table>
    {adj_html}
    <br>
    <p style="color:#888;font-size:12px">Auto-generated by Mangalya Ads Manager · Every 4 hours</p>
    </body></html>
    """
    return html


if __name__ == "__main__":
    last_status     = load_last_status()
    ads_data        = []
    newly_approved  = []
    all_adjustments = []

    for a in ADS:
        ad = Ad(a["ad_id"])
        ad.api_get(fields=["effective_status"])
        current_status = ad["effective_status"]
        prev_status    = last_status.get(a["ad_id"], "")

        if prev_status == "PENDING_REVIEW" and current_status == "ACTIVE":
            newly_approved.append(a["name"])

        ins    = get_insights(a["adset_id"])
        spend  = float(ins.get("spend", 0))
        leads  = get_action_count(ins.get("actions"), a["lead_type"])
        imps   = ins.get("impressions", 0)
        ctr    = ins.get("ctr", "0")

        adjustments = auto_adjust(a["ad_id"], a["adset_id"], a["name"], spend, leads, imps, ctr)
        all_adjustments.extend(adjustments)

        ads_data.append({
            "name":      a["name"],
            "targeting": a["targeting"],
            "status":    current_status,
            "insights":  ins,
            "lead_type": a["lead_type"],
        })

        last_status[a["ad_id"]] = current_status
        print(f"{a['name']}: {current_status} | Spend: Rs.{spend:.2f} | Leads: {leads}")

    save_status(last_status)

    subject = "Mangalya Ads — APPROVED!" if newly_approved else "Mangalya Ads — Status Report"
    html    = build_email(ads_data, newly_approved, all_adjustments)
    send_email(subject, html)
