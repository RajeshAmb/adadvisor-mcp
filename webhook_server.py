"""
Webhook Server — Receives real-time lead data from Meta Lead Ads.

Endpoints:
  GET  /webhook  — Meta verification (hub.verify_token challenge)
  POST /webhook  — Receive lead notifications, fetch lead data, store in DB
  GET  /health   — Health check

Deploy on Render alongside MCP server, or expose via ngrok for testing.
Run: python webhook_server.py
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

import config
import database as db
import requests as http_requests

# Telegram notifications
sys.path.insert(0, str(PROJECT_ROOT / "agents"))
from telegram_bot import send_message, send_lead_alert

app = Flask(__name__)

# Logging — file handler only if logs/ dir exists (not on Render)
log_handlers = [logging.StreamHandler()]
log_dir = PROJECT_ROOT / "logs"
if log_dir.exists():
    log_handlers.append(
        logging.FileHandler(log_dir / "webhook.log", encoding="utf-8")
    )

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=log_handlers,
)
logger = logging.getLogger("webhook")


# ── Meta API helper ───────────────────────────────────────────────────────────

def fetch_lead_data(leadgen_id):
    """Fetch actual lead field values from Meta API using leadgen_id."""
    url = f"https://graph.facebook.com/v21.0/{leadgen_id}"
    resp = http_requests.get(url, params={
        "access_token": config.ACCESS_TOKEN,
        "fields": "field_data,campaign_id,adset_id,ad_id,created_time",
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()


def parse_lead_fields(field_data):
    """Parse Meta lead form field_data into a flat dict."""
    result = {}
    for field in field_data:
        name = field.get("name", "").lower()
        values = field.get("values", [])
        value = values[0] if values else ""
        if "name" in name or "full_name" in name:
            result["name"] = value
        elif "phone" in name or "mobile" in name:
            result["phone"] = value
        elif "email" in name:
            result["email"] = value
        elif "gender" in name:
            result["gender"] = value
        elif "community" in name or "language" in name:
            result["community"] = value
    return result


# ── Webhook endpoints ─────────────────────────────────────────────────────────

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta webhook verification — responds to hub.challenge."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == config.WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return challenge, 200
    else:
        logger.warning(f"Webhook verification failed — token mismatch")
        return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def receive_webhook():
    """Receive lead notifications from Meta."""
    payload = request.get_json(silent=True)
    if not payload:
        return "Bad Request", 400

    logger.info(f"Webhook received: {json.dumps(payload)[:500]}")

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "leadgen":
                continue

            value = change.get("value", {})
            leadgen_id = value.get("leadgen_id")
            adgroup_id = value.get("adgroup_id", "")  # ad set ID
            page_id = value.get("page_id", "")

            if not leadgen_id:
                logger.warning("No leadgen_id in webhook payload")
                continue

            try:
                process_lead(leadgen_id, adgroup_id)
            except Exception as e:
                logger.error(f"Error processing lead {leadgen_id}: {e}")

    return "OK", 200


@app.route("/health", methods=["GET"])
def health():
    stats = db.get_stats()
    return jsonify({"status": "ok", "stats": stats})


# ── Lead processing ───────────────────────────────────────────────────────────

def process_lead(leadgen_id, adgroup_id=""):
    """Fetch lead data from Meta, store in DB, schedule follow-ups, alert."""
    logger.info(f"Processing lead: {leadgen_id}")

    # Fetch actual lead data from Meta
    lead_raw = fetch_lead_data(leadgen_id)
    fields = parse_lead_fields(lead_raw.get("field_data", []))

    name = fields.get("name", "Unknown")
    phone = fields.get("phone", "")
    email = fields.get("email")
    community = fields.get("community")
    gender = fields.get("gender")
    campaign_id = lead_raw.get("campaign_id", "")

    # Store in database
    lead_id = db.add_lead(
        name=name,
        phone=phone,
        email=email,
        community=community,
        gender=gender,
        source="meta_lead_ad",
        source_campaign=campaign_id,
        source_adset=adgroup_id,
        meta_lead_id=leadgen_id,
    )

    if lead_id is None:
        logger.info(f"Duplicate lead {leadgen_id} — skipping")
        return

    logger.info(f"New lead #{lead_id}: {name} ({phone})")

    # Schedule WhatsApp follow-up sequence
    db.schedule_follow_ups(lead_id)
    logger.info(f"Follow-ups scheduled for lead #{lead_id}")

    # Send Telegram alert
    send_lead_alert({
        "campaign": campaign_id,
        "adset": adgroup_id,
        "time": datetime.now().strftime("%I:%M %p"),
        "total_today": db.get_lead_count(),
        "cost_per_lead": "N/A",
        "spend_today": "0",
    })

    send_message(
        f"<b>WEBHOOK LEAD</b>\n"
        f"Name: {name}\n"
        f"Phone: {phone}\n"
        f"Community: {community or 'N/A'}\n"
        f"Source: Lead Ad ({adgroup_id})"
    )


# ── Run server ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", 5001))
    logger.info(f"Starting webhook server on port {port}")
    app.run(host="0.0.0.0", port=port)
