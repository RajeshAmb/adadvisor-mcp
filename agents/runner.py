"""
Agent Runner — Runs all agents or a specific one.
Usage:
  python agents/runner.py              # Run all agents
  python agents/runner.py lead_hunter  # Run specific agent
  python agents/runner.py brain        # Run AI Brain
  python agents/runner.py content      # Run Content Creator
  python agents/runner.py dashboard    # Start Dashboard
"""

import sys
import os
from pathlib import Path

# Add agents dir to path
AGENTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENTS_DIR))

from lead_hunter import LeadHunter
from brain import BrainAgent
from content_creator import ContentCreator
from whatsapp_agent import WhatsAppAgent
from campaign_creator import CampaignCreator
from video_generator import VideoGenerator


AGENTS = {
    "lead_hunter": LeadHunter,
    "brain": BrainAgent,
    "content": ContentCreator,
    "whatsapp": WhatsAppAgent,
    "campaign_creator": CampaignCreator,
    "video_generator": VideoGenerator,
}


def run_agent(name):
    if name == "dashboard":
        from dashboard import app
        print("Starting Dashboard at http://localhost:5000")
        app.run(host="0.0.0.0", port=5000)
    elif name in AGENTS:
        print(f"Running {name}...")
        AGENTS[name]().run()
    else:
        print(f"Unknown agent: {name}")
        print(f"Available: {', '.join(list(AGENTS.keys()) + ['dashboard'])}")


def run_all():
    """Run all monitoring agents (not dashboard)."""
    for name, cls in AGENTS.items():
        if name == "content":
            continue  # Content runs on its own schedule
        try:
            cls().run()
        except Exception as e:
            print(f"Error running {name}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_agent(sys.argv[1])
    else:
        run_all()
