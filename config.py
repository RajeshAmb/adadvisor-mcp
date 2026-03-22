import os
from dotenv import load_dotenv
load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
APP_ID = os.getenv("META_APP_ID", "YOUR_APP_ID")
APP_SECRET = os.getenv("META_APP_SECRET", "YOUR_APP_SECRET")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID", "act_XXXXXXXXXX")
