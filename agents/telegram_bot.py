"""Telegram notification module for Mangalya agents."""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(text, parse_mode="HTML"):
    """Send a Telegram message. Returns True on success."""
    if not BOT_TOKEN or not CHAT_ID:
        print(f"[Telegram] Not configured — message: {text[:100]}")
        return False
    try:
        resp = requests.post(
            f"{API_BASE}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        return False


def send_alert(title, body):
    """Send a formatted alert."""
    msg = f"<b>{title}</b>\n\n{body}"
    return send_message(msg)


def send_lead_alert(lead_data):
    """Send instant lead notification."""
    msg = (
        f"🎯 <b>NEW SIGNUP!</b>\n\n"
        f"<b>Campaign:</b> {lead_data.get('campaign', 'N/A')}\n"
        f"<b>Ad Set:</b> {lead_data.get('adset', 'N/A')}\n"
        f"<b>Time:</b> {lead_data.get('time', 'N/A')}\n"
        f"<b>Total Today:</b> {lead_data.get('total_today', '?')}\n"
        f"<b>Cost/Lead:</b> Rs.{lead_data.get('cost_per_lead', 'N/A')}\n\n"
        f"💰 <b>Spend Today:</b> Rs.{lead_data.get('spend_today', '0')}"
    )
    return send_message(msg)


def send_daily_summary(data):
    """Send daily performance summary."""
    lines = [f"📊 <b>DAILY SUMMARY — {data.get('date', 'Today')}</b>\n"]
    for camp in data.get("campaigns", []):
        emoji = "✅" if camp.get("leads", 0) > 0 else "⏸" if camp.get("status") == "PAUSED" else "⚠️"
        lines.append(
            f"{emoji} <b>{camp['name']}</b>\n"
            f"   Leads: {camp.get('leads', 0)} | "
            f"Spend: Rs.{camp.get('spend', 0):.0f} | "
            f"CPL: {('Rs.' + str(round(camp['cost_per_lead'], 0))) if camp.get('cost_per_lead') else 'N/A'}"
        )
    lines.append(f"\n<b>TOTAL:</b> {data.get('total_leads', 0)} leads | Rs.{data.get('total_spend', 0):.0f} spent")
    if data.get("avg_cpl"):
        lines.append(f"<b>Avg CPL:</b> Rs.{data['avg_cpl']:.0f}")
    return send_message("\n".join(lines))


def send_brain_report(analysis):
    """Send AI Brain analysis report."""
    msg = f"🧠 <b>AI BRAIN REPORT</b>\n\n{analysis}"
    # Telegram has 4096 char limit
    if len(msg) > 4000:
        msg = msg[:3997] + "..."
    return send_message(msg)


def send_whatsapp_status(data):
    """Send WhatsApp agent status update."""
    msg = (
        f"📱 <b>WHATSAPP AGENT</b>\n\n"
        f"<b>Sent:</b> {data.get('sent', 0)}\n"
        f"<b>Failed:</b> {data.get('failed', 0)}\n"
        f"<b>Daily Total:</b> {data.get('daily_total', 0)}\n"
        f"<b>Pending:</b> {data.get('pending', 0)}"
    )
    return send_message(msg)


def send_campaign_created(data):
    """Send notification when auto-campaign is created."""
    msg = (
        f"🚀 <b>NEW CAMPAIGN CREATED</b>\n\n"
        f"<b>Campaign:</b> {data.get('campaign_name', 'N/A')}\n"
        f"<b>Community:</b> {data.get('community', 'N/A')}\n"
        f"<b>Budget:</b> {data.get('budget', 'N/A')}\n"
        f"<b>Status:</b> PAUSED (awaiting approval)\n\n"
        f"Activate in Meta Ads Manager or via MCP tools."
    )
    return send_message(msg)


def send_video_status(data):
    """Send video pipeline status update."""
    msg = (
        f"🎬 <b>VIDEO GENERATOR</b>\n\n"
        f"<b>New Scripts:</b> {data.get('new', 0)}\n"
        f"<b>Rendering:</b> {data.get('rendering', 0)}\n"
        f"<b>Uploaded:</b> {data.get('uploaded', 0)}\n"
        f"<b>Pipeline:</b> {data.get('status_summary', {})}"
    )
    return send_message(msg)


def send_webhook_lead(data):
    """Send instant webhook lead notification."""
    msg = (
        f"⚡ <b>INSTANT LEAD (Webhook)</b>\n\n"
        f"<b>Name:</b> {data.get('name', 'N/A')}\n"
        f"<b>Phone:</b> {data.get('phone', 'N/A')}\n"
        f"<b>Community:</b> {data.get('community', 'N/A')}\n"
        f"<b>Source:</b> {data.get('source', 'Lead Ad')}\n\n"
        f"WhatsApp follow-up scheduled automatically."
    )
    return send_message(msg)


if __name__ == "__main__":
    # Test
    send_message("✅ Mangalya Agent Team — Telegram connected!")
