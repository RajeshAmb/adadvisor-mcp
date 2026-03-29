from dotenv import load_dotenv
load_dotenv()
import config
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign

FacebookAdsApi.init(config.APP_ID, config.APP_SECRET, config.ACCESS_TOKEN)

adset = AdSet("120265125536690555")
adset.api_get(fields=["campaign_id"])
camp = Campaign(adset["campaign_id"])
camp.api_get(fields=["name", "status"])
print(f"Campaign: {camp.get('name')} | Status: {camp.get('status')}")
camp.api_update(params={"status": "ACTIVE"})
print("Activated!")
