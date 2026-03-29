"""
Meta Ads Manager
Run: python main.py
"""
from dotenv import load_dotenv
load_dotenv()

import config
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
import ads_manager as ads

FacebookAdsApi.init(config.APP_ID, config.APP_SECRET, config.ACCESS_TOKEN)
account = AdAccount(config.AD_ACCOUNT_ID)


def create_campaign_full(campaign_name, objective, adset_name, targeting,
                          daily_budget_paise, image_hash, message, headline,
                          destination_url, optimization_goal="OFFSITE_CONVERSIONS"):

    # Campaign
    campaign = account.create_campaign(fields=[], params={
        'name': campaign_name,
        'objective': objective,
        'status': 'PAUSED',
        'special_ad_categories': [],
        'is_adset_budget_sharing_enabled': False,
    })

    # Ad Set
    adset = account.create_ad_set(fields=[], params={
        'name': adset_name,
        'campaign_id': campaign['id'],
        'daily_budget': daily_budget_paise,
        'billing_event': 'IMPRESSIONS',
        'optimization_goal': optimization_goal,
        'targeting': targeting,
        'status': 'PAUSED',
        'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
        'promoted_object': {
            'pixel_id': '965010763370621',
            'custom_event_type': 'COMPLETE_REGISTRATION',
        },
    })

    # Creative
    creative = account.create_ad_creative(fields=[], params={
        'name': f'{campaign_name}-creative',
        'object_story_spec': {
            'page_id': '1053689994488653',
            'link_data': {
                'image_hash': image_hash,
                'link': destination_url,
                'message': message,
                'name': headline,
                'call_to_action': {
                    'type': 'SIGN_UP',
                    'value': {'link': destination_url},
                },
            },
        },
    })

    # Ad
    ad = account.create_ad(fields=[], params={
        'name': f'{campaign_name}-ad',
        'adset_id': adset['id'],
        'creative': {'creative_id': creative['id']},
        'status': 'ACTIVE',
    })

    # Activate campaign
    Campaign(campaign['id']).api_update(params={'status': 'ACTIVE'})

    print(f"Campaign ID : {campaign['id']}")
    print(f"Ad Set ID   : {adset['id']}")
    print(f"Ad ID       : {ad['id']}")

    # Send setup confirmation email
    ads.send_setup_email(
        campaign_name=campaign_name,
        campaign_id=campaign['id'],
        adset_name=adset_name,
        adset_id=adset['id'],
        ad_id=ad['id'],
        targeting=adset_name,
        budget_paise=daily_budget_paise,
        destination_url=destination_url,
    )

    return campaign, adset, ad


if __name__ == "__main__":
    # Example — uncomment and fill in to create a new campaign
    pass

    # create_campaign_full(
    #     campaign_name   = "Mangalya-Telugu-01",
    #     objective       = "OUTCOME_LEADS",
    #     adset_name      = "AP Telangana Women 23-33",
    #     targeting       = {
    #         "geo_locations": {
    #             "regions": [{"key": "1724"}, {"key": "4100"}],
    #             "location_types": ["home", "recent"],
    #         },
    #         "age_min": 23, "age_max": 33,
    #         "genders": [2],
    #         "locales": [49],
    #     },
    #     daily_budget_paise = 25000,
    #     image_hash      = "17cc9cab70d176d54d4683bf6c45fcdd",
    #     message         = "Trusted Telugu Matrimony. 100% verified profiles. Join now.",
    #     headline        = "Find Your Perfect Match",
    #     destination_url = "https://mangalyamatrimony.com/login",
    # )
