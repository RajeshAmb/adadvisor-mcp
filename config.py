import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Meta Ads API
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
APP_ID = os.getenv("META_APP_ID", "YOUR_APP_ID")
APP_SECRET = os.getenv("META_APP_SECRET", "YOUR_APP_SECRET")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID", "act_XXXXXXXXXX")

# Database
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent / "data" / "mangalya.db"))

# WhatsApp Business API (Meta Cloud API)
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")

# Video Generation (Pictory AI)
PICTORY_API_KEY = os.getenv("PICTORY_API_KEY", "")
PICTORY_USER_ID = os.getenv("PICTORY_USER_ID", "")

# Webhook
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "mangalya_verify_2024")
