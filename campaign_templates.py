"""
Campaign Templates — Predefined targeting configs for each South Indian community.

Used by the Campaign Creator agent to auto-replicate winning campaigns
across different communities.
"""

# Meta region keys for Indian states
REGIONS = {
    "andhra_pradesh": "1724",
    "telangana": "4100",
    "kerala": "1748",
    "tamil_nadu": "1773",
    "karnataka": "1745",
}

# Meta locale codes for South Indian languages
LOCALES = {
    "telugu": 49,
    "malayalam": 56,
    "tamil": 50,
    "kannada": 57,
}

PAGE_ID = "1053689994488653"  # Mangalya Facebook page
WEBSITE = "https://www.mangalyamatrimony.com"


COMMUNITY_TEMPLATES = {
    "telugu_women": {
        "display_name": "Telugu Women 23-33",
        "community": "Telugu",
        "targeting": {
            "geo_locations": {
                "regions": [
                    {"key": REGIONS["andhra_pradesh"]},
                    {"key": REGIONS["telangana"]},
                ],
            },
            "age_min": 23,
            "age_max": 33,
            "genders": [2],  # Female
            "locales": [LOCALES["telugu"]],
        },
        "default_budget_paise": 25000,  # Rs.250/day
        "language": "Telugu",
    },
    "telugu_parents": {
        "display_name": "Telugu Parents 45-65",
        "community": "Telugu",
        "targeting": {
            "geo_locations": {
                "regions": [
                    {"key": REGIONS["andhra_pradesh"]},
                    {"key": REGIONS["telangana"]},
                ],
            },
            "age_min": 45,
            "age_max": 65,
            "locales": [LOCALES["telugu"]],
        },
        "default_budget_paise": 28000,  # Rs.280/day
        "language": "Telugu",
    },
    "tamil_women": {
        "display_name": "Tamil Women 23-33",
        "community": "Tamil",
        "targeting": {
            "geo_locations": {
                "regions": [{"key": REGIONS["tamil_nadu"]}],
            },
            "age_min": 23,
            "age_max": 33,
            "genders": [2],
            "locales": [LOCALES["tamil"]],
        },
        "default_budget_paise": 20000,
        "language": "Tamil",
    },
    "tamil_parents": {
        "display_name": "Tamil Parents 45-65",
        "community": "Tamil",
        "targeting": {
            "geo_locations": {
                "regions": [{"key": REGIONS["tamil_nadu"]}],
            },
            "age_min": 45,
            "age_max": 65,
            "locales": [LOCALES["tamil"]],
        },
        "default_budget_paise": 20000,
        "language": "Tamil",
    },
    "kerala_women": {
        "display_name": "Kerala Women 23-33",
        "community": "Malayalam",
        "targeting": {
            "geo_locations": {
                "regions": [{"key": REGIONS["kerala"]}],
            },
            "age_min": 23,
            "age_max": 33,
            "genders": [2],
            "locales": [LOCALES["malayalam"]],
        },
        "default_budget_paise": 20000,
        "language": "Malayalam",
    },
    "kerala_parents": {
        "display_name": "Kerala Parents 45-65",
        "community": "Malayalam",
        "targeting": {
            "geo_locations": {
                "regions": [{"key": REGIONS["kerala"]}],
            },
            "age_min": 45,
            "age_max": 65,
            "locales": [LOCALES["malayalam"]],
        },
        "default_budget_paise": 20000,
        "language": "Malayalam",
    },
    "kannada_women": {
        "display_name": "Kannada Women 23-33",
        "community": "Kannada",
        "targeting": {
            "geo_locations": {
                "regions": [{"key": REGIONS["karnataka"]}],
            },
            "age_min": 23,
            "age_max": 33,
            "genders": [2],
            "locales": [LOCALES["kannada"]],
        },
        "default_budget_paise": 20000,
        "language": "Kannada",
    },
    "kannada_parents": {
        "display_name": "Kannada Parents 45-65",
        "community": "Kannada",
        "targeting": {
            "geo_locations": {
                "regions": [{"key": REGIONS["karnataka"]}],
            },
            "age_min": 45,
            "age_max": 65,
            "locales": [LOCALES["kannada"]],
        },
        "default_budget_paise": 20000,
        "language": "Kannada",
    },
    "telugu_diaspora": {
        "display_name": "Telugu Diaspora 25-45",
        "community": "Telugu",
        "targeting": {
            "geo_locations": {
                "regions": [
                    {"key": REGIONS["karnataka"]},
                    {"key": REGIONS["tamil_nadu"]},
                    {"key": REGIONS["kerala"]},
                ],
            },
            "age_min": 25,
            "age_max": 45,
            "locales": [LOCALES["telugu"]],
        },
        "default_budget_paise": 15000,
        "language": "Telugu",
    },
}


def get_template(key):
    """Get a community template by key."""
    return COMMUNITY_TEMPLATES.get(key)


def get_all_communities():
    """Get list of all community template keys."""
    return list(COMMUNITY_TEMPLATES.keys())


def get_templates_for_community(community):
    """Get all templates matching a community name (e.g., 'Telugu')."""
    return {
        k: v for k, v in COMMUNITY_TEMPLATES.items()
        if v["community"].lower() == community.lower()
    }
