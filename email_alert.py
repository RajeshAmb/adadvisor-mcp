"""
Daily email alert for Mangalya Meta Ads performance.
Scheduled via Task Scheduler — runs at 9AM daily.
"""
from dotenv import load_dotenv
load_dotenv()

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
import config
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet

FacebookAdsApi.init(config.APP_ID, config.APP_SECRET, config.ACCESS_TOKEN)
account = AdAccount(config.AD_ACCOUNT_ID)

FIELDS = ["impressions", "clicks", "spend", "ctr", "actions", "reach"]

def get_leads(actions):
    return next((int(a["value"]) for a in (actions or []) if a["action_type"] == "lead"), 0)

# ── Collect data ──────────────────────────────────────────────────
rows = []
total_spend = 0
total_leads = 0

for c in account.get_campaigns(fields=["name"]):
    for a in Campaign(c["id"]).get_ad_sets(fields=["name", "daily_budget", "effective_status"]):
        insights = AdSet(a["id"]).get_insights(fields=FIELDS, params={"date_preset": "last_3d"})
        budget = int(a.get("daily_budget", 0)) // 100
        if not insights:
            rows.append({
                "name": a.get("name"), "status": a.get("effective_status"),
                "budget": budget, "reach": 0, "impressions": 0,
                "clicks": 0, "ctr": 0, "spend": 0, "leads": 0, "cpl": None
            })
            continue
        r = insights[0]
        sp = float(r.get("spend", 0))
        lc = get_leads(r.get("actions"))
        total_spend += sp
        total_leads += lc
        rows.append({
            "name": a.get("name"), "status": a.get("effective_status"),
            "budget": budget,
            "reach": int(r.get("reach", 0)),
            "impressions": int(r.get("impressions", 0)),
            "clicks": int(r.get("clicks", 0)),
            "ctr": float(r.get("ctr", 0)),
            "spend": sp, "leads": lc,
            "cpl": round(sp / lc, 2) if lc > 0 else None,
        })

avg_cpl = round(total_spend / total_leads, 2) if total_leads > 0 else None

# ── Alerts ────────────────────────────────────────────────────────
alerts = []
for r in rows:
    if r["status"] == "ACTIVE" and r["impressions"] > 0:
        if r["ctr"] < 0.5:
            alerts.append(f"LOW CTR: {r['name']} — {r['ctr']:.2f}% (below 0.5%)")
        if r["cpl"] and r["cpl"] > 100:
            alerts.append(f"HIGH CPL: {r['name']} — Rs.{r['cpl']} (above Rs.100)")
        if r["cpl"] and r["cpl"] < 40 and r["leads"] >= 3:
            alerts.append(f"SCALE UP: {r['name']} — Rs.{r['cpl']}/lead, {r['leads']} leads. Increase budget!")

# ── Build email ───────────────────────────────────────────────────
today = date.today().strftime("%d %b %Y")

table_rows = ""
for r in rows:
    cpl_str = f"Rs.{r['cpl']}" if r['cpl'] else "N/A"
    color = "#d4edda" if r["leads"] > 0 else ("#fff3cd" if r["status"] == "ACTIVE" else "#f8f9fa")
    table_rows += f"""
    <tr style="background:{color}">
      <td style="padding:8px;border:1px solid #dee2e6">{r['name']}</td>
      <td style="padding:8px;border:1px solid #dee2e6;text-align:center">{r['status']}</td>
      <td style="padding:8px;border:1px solid #dee2e6;text-align:center">Rs.{r['budget']}/day</td>
      <td style="padding:8px;border:1px solid #dee2e6;text-align:center">{r['reach']:,}</td>
      <td style="padding:8px;border:1px solid #dee2e6;text-align:center">{r['ctr']:.2f}%</td>
      <td style="padding:8px;border:1px solid #dee2e6;text-align:center">Rs.{r['spend']:.2f}</td>
      <td style="padding:8px;border:1px solid #dee2e6;text-align:center"><b>{r['leads']}</b></td>
      <td style="padding:8px;border:1px solid #dee2e6;text-align:center">{cpl_str}</td>
    </tr>"""

alert_html = ""
if alerts:
    alert_items = "".join(f"<li>{a}</li>" for a in alerts)
    alert_html = f"""
    <div style="background:#fff3cd;border:1px solid #ffc107;padding:12px;border-radius:4px;margin:16px 0">
      <b>Action Required:</b>
      <ul style="margin:8px 0 0">{alert_items}</ul>
    </div>"""

html = f"""
<html><body style="font-family:Arial,sans-serif;color:#333;max-width:700px;margin:auto">
  <h2 style="color:#1a73e8">Mangalya Ads Report — {today}</h2>
  <p style="color:#666">Performance summary for last 3 days</p>

  {alert_html}

  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <tr style="background:#1a73e8;color:white">
      <th style="padding:8px;border:1px solid #dee2e6;text-align:left">Ad Set</th>
      <th style="padding:8px;border:1px solid #dee2e6">Status</th>
      <th style="padding:8px;border:1px solid #dee2e6">Budget</th>
      <th style="padding:8px;border:1px solid #dee2e6">Reach</th>
      <th style="padding:8px;border:1px solid #dee2e6">CTR</th>
      <th style="padding:8px;border:1px solid #dee2e6">Spend</th>
      <th style="padding:8px;border:1px solid #dee2e6">Leads</th>
      <th style="padding:8px;border:1px solid #dee2e6">CPL</th>
    </tr>
    {table_rows}
  </table>

  <div style="margin-top:16px;padding:12px;background:#f8f9fa;border-radius:4px">
    <b>TOTAL (last 3 days)</b><br>
    Spend: <b>Rs.{total_spend:.2f}</b> &nbsp;|&nbsp;
    Leads: <b>{total_leads}</b> &nbsp;|&nbsp;
    Avg CPL: <b>{'Rs.'+str(avg_cpl) if avg_cpl else 'N/A'}</b>
  </div>

  <p style="color:#999;font-size:11px;margin-top:24px">
    Sent automatically by Mangalya AdAdvisor &mdash; {today}
  </p>
</body></html>
"""

# ── Send email ────────────────────────────────────────────────────
msg = MIMEMultipart("alternative")
msg["Subject"] = f"Mangalya Ads Report {today} — {total_leads} leads, Rs.{total_spend:.0f} spent"
msg["From"]    = os.getenv("EMAIL_FROM")
msg["To"]      = os.getenv("EMAIL_TO")
msg.attach(MIMEText(html, "html"))

try:
    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
        server.sendmail(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_TO"), msg.as_string())
    print(f"Email sent to {os.getenv('EMAIL_TO')}")
except Exception as e:
    print(f"Email failed: {e}")
