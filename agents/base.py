"""Base agent class with shared utilities."""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import config
import database as db
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.ad import Ad

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


class BaseAgent:
    """Base class for all Mangalya agents."""

    name = "base"

    def __init__(self):
        self.logger = self._setup_logger()
        self._meta_initialized = False
        self.db = db

    def _setup_logger(self):
        logger = logging.getLogger(f"mangalya.{self.name}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            # File handler
            fh = logging.FileHandler(
                LOG_DIR / f"{self.name}.log", encoding="utf-8"
            )
            fh.setFormatter(logging.Formatter(
                "[%(asctime)s] %(levelname)s — %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
            logger.addHandler(fh)
            # Console handler
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(ch)
        return logger

    def init_meta(self):
        """Initialize Meta Ads API (lazy, call only when needed)."""
        if not self._meta_initialized:
            FacebookAdsApi.init(config.APP_ID, config.APP_SECRET, config.ACCESS_TOKEN)
            self._meta_initialized = True
        return AdAccount(config.AD_ACCOUNT_ID)

    def log(self, msg):
        self.logger.info(msg)

    def log_error(self, msg):
        self.logger.error(msg)

    def load_json(self, filename):
        """Load JSON from data/ directory."""
        path = DATA_DIR / filename
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_json(self, filename, data):
        """Save JSON to data/ directory."""
        path = DATA_DIR / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def get_adset_performance(self, adset_id, date_preset="last_3d"):
        """Get performance metrics for an ad set."""
        self.init_meta()
        adset = AdSet(adset_id)
        adset.api_get(fields=["daily_budget", "status", "name"])
        rows = adset.get_insights(
            fields=["impressions", "reach", "clicks", "spend", "ctr", "cpc", "actions"],
            params={"date_preset": date_preset},
        )
        row = rows[0] if rows else {}
        leads = self._get_action_count(row.get("actions"), "lead")
        spend = float(row.get("spend", 0))
        return {
            "adset_id": adset_id,
            "name": adset.get("name", ""),
            "status": adset.get("status", ""),
            "daily_budget": int(adset.get("daily_budget", 0)),
            "impressions": int(row.get("impressions", 0)),
            "reach": int(row.get("reach", 0)),
            "clicks": int(row.get("clicks", 0)),
            "spend": spend,
            "ctr": float(row.get("ctr", 0)),
            "cpc": float(row.get("cpc", 0)) if row.get("cpc") else 0,
            "leads": leads,
            "cost_per_lead": round(spend / leads, 2) if leads > 0 else None,
            "date_preset": date_preset,
        }

    def get_all_adsets_performance(self, date_preset="last_3d"):
        """Get performance for all active ad sets."""
        account = self.init_meta()
        results = []
        for c in account.get_campaigns(fields=["name", "status"]):
            if c["status"] != "ACTIVE":
                continue
            campaign = Campaign(c["id"])
            for adset in campaign.get_ad_sets(fields=["name", "daily_budget", "status"]):
                try:
                    perf = self.get_adset_performance(adset["id"], date_preset)
                    perf["campaign_name"] = c["name"]
                    perf["campaign_id"] = c["id"]
                    results.append(perf)
                except Exception as e:
                    self.log_error(f"Error getting {adset.get('name', adset['id'])}: {e}")
        return results

    @staticmethod
    def _get_action_count(actions, action_type):
        if not actions:
            return 0
        for a in actions:
            if a.get("action_type") == action_type:
                return int(a.get("value", 0))
        return 0

    def run(self):
        """Override in subclass."""
        raise NotImplementedError
