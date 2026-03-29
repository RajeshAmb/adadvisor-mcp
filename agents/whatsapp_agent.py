"""
WhatsApp Follow-up Agent — Sends automated messages to new leads via
Meta WhatsApp Cloud API.

Sequence:
  1. Welcome (immediately)     — "Welcome to Mangalya! Complete your profile"
  2. Day 1 — Matches           — "We found X matches in your community"
  3. Day 3 — Views             — "Your profile was viewed Y times"
  4. Day 7 — Upgrade           — "Unlock premium features"

Runs every 5 minutes via Task Scheduler.

Prerequisites:
  - WhatsApp Business API approved in Meta Business Manager
  - Message templates created and approved
  - WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN in .env
"""

import os
import requests
from datetime import datetime
from base import BaseAgent
from telegram_bot import send_message as telegram_msg

GRAPH_API = "https://graph.facebook.com/v21.0"

# Template names — create these in Meta Business Manager
TEMPLATES = {
    "welcome": "mangalya_welcome",
    "day1_matches": "mangalya_matches",
    "day3_views": "mangalya_views",
    "day7_upgrade": "mangalya_upgrade",
}


class WhatsAppAgent(BaseAgent):
    name = "whatsapp"

    # WhatsApp Cloud API rate limit: 250 business-initiated messages/24h (new number tier)
    MAX_MESSAGES_PER_RUN = 20
    MAX_MESSAGES_PER_DAY = 200

    def __init__(self):
        super().__init__()
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.daily_count_file = "whatsapp_daily_count.json"

    def is_configured(self):
        return bool(self.phone_number_id and self.access_token)

    def send_template_message(self, phone, template_name, language="en", params=None):
        """Send a WhatsApp template message via Meta Cloud API.

        Returns message_id on success, None on failure.
        """
        url = f"{GRAPH_API}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        components = []
        if params:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(v)} for v in params
                ],
            })

        body = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
            },
        }
        if components:
            body["template"]["components"] = components

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("messages", [{}])[0].get("id")
            self.log(f"Sent {template_name} to {phone} — msg_id: {msg_id}")
            return msg_id
        except requests.exceptions.HTTPError as e:
            error_body = e.response.text if e.response else str(e)
            self.log_error(f"WhatsApp API error for {phone}: {error_body}")
            return None
        except Exception as e:
            self.log_error(f"WhatsApp send failed for {phone}: {e}")
            return None

    def send_text_message(self, phone, text):
        """Send a freeform text message (only works within 24h conversation window)."""
        url = f"{GRAPH_API}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        }
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=15)
            resp.raise_for_status()
            return resp.json().get("messages", [{}])[0].get("id")
        except Exception as e:
            self.log_error(f"WhatsApp text send failed for {phone}: {e}")
            return None

    def get_daily_send_count(self):
        """Track daily message count to respect rate limits."""
        data = self.load_json(self.daily_count_file)
        today = datetime.now().strftime("%Y-%m-%d")
        if data.get("date") != today:
            return 0
        return data.get("count", 0)

    def increment_daily_count(self, amount=1):
        today = datetime.now().strftime("%Y-%m-%d")
        data = self.load_json(self.daily_count_file)
        if data.get("date") != today:
            data = {"date": today, "count": 0}
        data["count"] = data.get("count", 0) + amount
        self.save_json(self.daily_count_file, data)

    def process_new_leads(self):
        """Find new leads without welcome messages and schedule follow-ups."""
        new_leads = self.db.get_new_leads_since(minutes=10)
        welcome_count = 0

        for lead in new_leads:
            if self.db.has_welcome_been_sent(lead["id"]):
                continue

            # Schedule the full follow-up sequence
            self.db.schedule_follow_ups(lead["id"])
            self.log(f"Scheduled follow-ups for lead #{lead['id']} ({lead['name']})")
            welcome_count += 1

        return welcome_count

    def process_pending_follow_ups(self):
        """Send all due follow-up messages."""
        if not self.is_configured():
            self.log("WhatsApp not configured — skipping message sends")
            return 0, 0

        daily_count = self.get_daily_send_count()
        if daily_count >= self.MAX_MESSAGES_PER_DAY:
            self.log(f"Daily limit reached ({daily_count}/{self.MAX_MESSAGES_PER_DAY})")
            return 0, 0

        pending = self.db.get_pending_follow_ups(limit=self.MAX_MESSAGES_PER_RUN)
        sent = 0
        failed = 0

        for fu in pending:
            if daily_count + sent >= self.MAX_MESSAGES_PER_DAY:
                self.log("Daily limit reached mid-run — stopping")
                break

            phone = fu["lead_phone"]
            if not phone:
                self.db.mark_follow_up_failed(fu["id"], "No phone number")
                failed += 1
                continue

            template = TEMPLATES.get(fu["sequence_step"])
            if not template:
                self.db.mark_follow_up_failed(fu["id"], f"Unknown step: {fu['sequence_step']}")
                failed += 1
                continue

            # Build template parameters based on step
            params = self.get_template_params(fu)

            msg_id = self.send_template_message(phone, template, params=params)
            if msg_id:
                self.db.mark_follow_up_sent(fu["id"], msg_id)
                sent += 1

                # Update lead status on first contact
                if fu["sequence_step"] == "welcome":
                    self.db.update_lead_status(fu["lead_id"], "contacted")
            else:
                self.db.mark_follow_up_failed(fu["id"], "API send failed")
                failed += 1

        if sent > 0:
            self.increment_daily_count(sent)

        return sent, failed

    def get_template_params(self, follow_up):
        """Build template parameters for each sequence step."""
        name = follow_up.get("lead_name", "there")
        community = follow_up.get("lead_community", "South Indian")

        if follow_up["sequence_step"] == "welcome":
            return [name]
        elif follow_up["sequence_step"] == "day1_matches":
            return [name, community]
        elif follow_up["sequence_step"] == "day3_views":
            return [name]
        elif follow_up["sequence_step"] == "day7_upgrade":
            return [name]
        return [name]

    def run(self):
        self.log("=" * 50)
        self.log("WHATSAPP AGENT — Processing follow-ups")

        # Step 1: Check for new leads that need follow-up scheduling
        new_scheduled = self.process_new_leads()
        if new_scheduled > 0:
            self.log(f"Scheduled follow-ups for {new_scheduled} new leads")

        # Step 2: Process pending follow-ups
        sent, failed = self.process_pending_follow_ups()

        # Summary
        daily_total = self.get_daily_send_count()
        self.log(f"Sent: {sent} | Failed: {failed} | Daily total: {daily_total}")

        # Telegram notification if any messages sent
        if sent > 0 or failed > 0:
            telegram_msg(
                f"<b>WhatsApp Agent</b>\n"
                f"Sent: {sent} | Failed: {failed}\n"
                f"Daily total: {daily_total}/{self.MAX_MESSAGES_PER_DAY}"
            )

        self.log("WhatsApp Agent done.\n")


if __name__ == "__main__":
    WhatsAppAgent().run()
