"""
Mangalya Agent Team Dashboard — Flask web app.
Shows all metrics, agent activity, and leads in one place.

Run: python agents/dashboard.py
Then open: http://localhost:5000
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, jsonify

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mangalya Agent Team</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #0f1117; color: #e0e0e0; }
        .header {
            background: linear-gradient(135deg, #c0392b, #8e2222);
            padding: 20px 30px; display: flex; justify-content: space-between; align-items: center;
        }
        .header h1 { font-size: 24px; color: white; }
        .header .status { font-size: 13px; color: #ffcdd2; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }

        /* KPI Cards */
        .kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .kpi-card {
            background: #1a1d27; border-radius: 12px; padding: 20px;
            border: 1px solid #2a2d37;
        }
        .kpi-card .label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
        .kpi-card .value { font-size: 32px; font-weight: bold; margin-top: 4px; }
        .kpi-card .sub { font-size: 12px; color: #666; margin-top: 4px; }
        .green { color: #27ae60; }
        .red { color: #e74c3c; }
        .gold { color: #f39c12; }
        .blue { color: #3498db; }

        /* Sections */
        .section { background: #1a1d27; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #2a2d37; }
        .section h2 { font-size: 18px; margin-bottom: 16px; color: #fff; display: flex; align-items: center; gap: 8px; }

        /* Table */
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th { text-align: left; padding: 10px 12px; background: #252830; color: #888; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }
        td { padding: 10px 12px; border-top: 1px solid #252830; }
        tr:hover { background: #1f222c; }
        .badge {
            display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
        }
        .badge-active { background: #1b4332; color: #27ae60; }
        .badge-paused { background: #3d3100; color: #f39c12; }

        /* Agent Status */
        .agent-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
        .agent-card {
            background: #252830; border-radius: 8px; padding: 16px;
            border-left: 4px solid #3498db;
        }
        .agent-card h3 { font-size: 14px; margin-bottom: 8px; }
        .agent-card .meta { font-size: 12px; color: #888; }
        .agent-card.active { border-left-color: #27ae60; }

        /* Content Preview */
        .content-card {
            background: #252830; border-radius: 8px; padding: 16px; margin-bottom: 12px;
        }
        .content-card .tag { font-size: 11px; background: #c0392b; color: white; padding: 2px 8px; border-radius: 3px; display: inline-block; margin-bottom: 8px; }
        .content-card p { font-size: 13px; color: #ccc; line-height: 1.5; }

        /* Log */
        .log-area {
            background: #0a0c12; border-radius: 8px; padding: 16px; max-height: 300px;
            overflow-y: auto; font-family: 'Consolas', monospace; font-size: 12px; color: #888;
            line-height: 1.6;
        }

        .refresh-btn {
            background: #c0392b; color: white; border: none; padding: 8px 20px;
            border-radius: 6px; cursor: pointer; font-size: 13px;
        }
        .refresh-btn:hover { background: #e74c3c; }

        /* Auto refresh indicator */
        .auto-refresh { font-size: 11px; color: #555; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Mangalya Agent Team</h1>
            <div class="status">mangalyamatrimony.com — AI-Powered Lead Generation</div>
        </div>
        <div>
            <button class="refresh-btn" onclick="location.reload()">Refresh</button>
            <div class="auto-refresh">Auto-refreshes every 60s</div>
        </div>
    </div>

    <div class="container">
        <!-- KPI Cards -->
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="label">Leads Today</div>
                <div class="value green">{{ kpi.leads_today }}</div>
                <div class="sub">Signups from ads</div>
            </div>
            <div class="kpi-card">
                <div class="label">Spend Today</div>
                <div class="value gold">Rs.{{ kpi.spend_today }}</div>
                <div class="sub">Across all campaigns</div>
            </div>
            <div class="kpi-card">
                <div class="label">Cost / Lead</div>
                <div class="value {{ 'green' if kpi.cpl_color == 'good' else 'red' }}">{{ kpi.cpl_today }}</div>
                <div class="sub">Target: &lt; Rs.80</div>
            </div>
            <div class="kpi-card">
                <div class="label">Leads (7 days)</div>
                <div class="value blue">{{ kpi.leads_7d }}</div>
                <div class="sub">Total: Rs.{{ kpi.spend_7d }} spent</div>
            </div>
            <div class="kpi-card">
                <div class="label">Active Agents</div>
                <div class="value green">{{ kpi.active_agents }}</div>
                <div class="sub">{{ kpi.agent_status }}</div>
            </div>
        </div>

        <!-- Campaign Performance -->
        <div class="section">
            <h2>Campaign Performance (Last 3 Days)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Ad Set</th>
                        <th>Status</th>
                        <th>Budget</th>
                        <th>Impressions</th>
                        <th>Clicks</th>
                        <th>CTR</th>
                        <th>Spend</th>
                        <th>Leads</th>
                        <th>CPL</th>
                    </tr>
                </thead>
                <tbody>
                    {% for c in campaigns %}
                    <tr>
                        <td><strong>{{ c.name }}</strong></td>
                        <td><span class="badge {{ 'badge-active' if c.status == 'ACTIVE' else 'badge-paused' }}">{{ c.status }}</span></td>
                        <td>Rs.{{ c.budget }}/day</td>
                        <td>{{ c.impressions }}</td>
                        <td>{{ c.clicks }}</td>
                        <td>{{ c.ctr }}%</td>
                        <td>Rs.{{ c.spend }}</td>
                        <td><strong>{{ c.leads }}</strong></td>
                        <td>{{ c.cpl }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Agent Status -->
        <div class="section">
            <h2>Agent Team Status</h2>
            <div class="agent-grid">
                {% for agent in agents %}
                <div class="agent-card {{ 'active' if agent.active else '' }}">
                    <h3>{{ agent.icon }} {{ agent.name }}</h3>
                    <div class="meta">
                        Schedule: {{ agent.schedule }}<br>
                        Last run: {{ agent.last_run }}<br>
                        Status: {{ agent.status }}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- AI Brain Insights -->
        <div class="section">
            <h2>AI Brain — Latest Insights</h2>
            {% if brain_insights %}
            <p style="margin-bottom: 12px; color: #ccc;">{{ brain_insights.summary }}</p>
            {% for action in brain_insights.actions %}
            <div class="content-card">
                <span class="tag">{{ action.type }}</span>
                <p><strong>{{ action.adset_name }}</strong> — {{ action.reason }}</p>
            </div>
            {% endfor %}
            {% else %}
            <p style="color: #666;">No AI analysis yet. Brain agent runs every 6 hours.</p>
            {% endif %}
        </div>

        <!-- Generated Content -->
        <div class="section">
            <h2>Latest Generated Content</h2>
            {% if content_previews %}
            {% for item in content_previews %}
            <div class="content-card">
                <span class="tag">{{ item.type }}</span>
                <p>{{ item.text }}</p>
            </div>
            {% endfor %}
            {% else %}
            <p style="color: #666;">No content generated yet. Content Creator runs daily.</p>
            {% endif %}
        </div>

        <!-- Recent Logs -->
        <div class="section">
            <h2>Recent Agent Activity</h2>
            <div class="log-area">
                {% for line in log_lines %}
                {{ line }}<br>
                {% endfor %}
            </div>
        </div>
    </div>

    <script>
        // Auto-refresh every 60 seconds
        setTimeout(() => location.reload(), 60000);
    </script>
</body>
</html>
"""


def load_json_safe(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def get_recent_logs(n=50):
    """Get recent log lines from all agents."""
    lines = []
    for log_file in LOG_DIR.glob("*.log"):
        try:
            with open(log_file, encoding="utf-8") as f:
                agent_lines = f.readlines()[-20:]
                lines.extend(agent_lines)
        except:
            pass
    lines.sort()
    return [l.strip() for l in lines[-n:]]


@app.route("/")
def index():
    # Load lead counts
    lead_data = load_json_safe(DATA_DIR / "lead_counts.json")
    leads_today = lead_data.get("total_leads", 0)
    spend_today = lead_data.get("total_spend", 0)
    cpl_today = f"Rs.{spend_today / leads_today:.0f}" if leads_today > 0 else "N/A"
    cpl_color = "good" if leads_today > 0 and (spend_today / leads_today) < 80 else "bad"

    # Load brain history
    brain_data = load_json_safe(DATA_DIR / "brain_history.json")

    # Load generated content
    content_data = load_json_safe(DATA_DIR / "generated_content.json")
    today = datetime.now().strftime("%Y-%m-%d")
    today_content = content_data.get(today, {})

    # Build content previews
    content_previews = []
    for key, val in today_content.items():
        if key.startswith("ad_copy") and isinstance(val, list) and val:
            for copy in val[:2]:
                content_previews.append({
                    "type": f"Ad Copy ({key.replace('ad_copy_', '').title()})",
                    "text": f"{copy.get('headline', '')} — {copy.get('primary_text', '')}",
                })
        elif key == "instagram" and isinstance(val, dict):
            content_previews.append({
                "type": "Instagram",
                "text": val.get("caption", "")[:200],
            })

    # Build campaign data from lead counts
    campaigns = []
    for aid, info in lead_data.get("adsets", {}).items():
        if isinstance(info, dict):
            leads = info.get("leads", 0)
            spend = info.get("spend", 0)
            campaigns.append({
                "name": aid[:20] + "...",
                "status": "ACTIVE",
                "budget": "—",
                "impressions": "—",
                "clicks": "—",
                "ctr": "—",
                "spend": f"{spend:.0f}",
                "leads": leads,
                "cpl": f"Rs.{spend/leads:.0f}" if leads > 0 else "N/A",
            })

    # Agent statuses
    agents = [
        {
            "name": "Lead Hunter",
            "icon": "🎯",
            "schedule": "Every 15 min",
            "last_run": _get_last_log_time("lead_hunter"),
            "status": "Running",
            "active": True,
        },
        {
            "name": "AI Brain",
            "icon": "🧠",
            "schedule": "Every 6 hours",
            "last_run": brain_data.get("last_run", "Never")[:16] if brain_data.get("last_run") else "Never",
            "status": "Running" if brain_data.get("last_run") else "Waiting",
            "active": bool(brain_data.get("last_run")),
        },
        {
            "name": "Content Creator",
            "icon": "✍️",
            "schedule": "Daily 8 AM",
            "last_run": _get_last_log_time("content_creator"),
            "status": "Running" if today_content else "Waiting",
            "active": bool(today_content),
        },
        {
            "name": "Instagram Poster",
            "icon": "📸",
            "schedule": "Daily 10 AM",
            "last_run": _get_last_log_time("instagram"),
            "status": "Running",
            "active": True,
        },
        {
            "name": "Status Checker",
            "icon": "📊",
            "schedule": "Every 4 hours",
            "last_run": _get_last_log_time("status_check"),
            "status": "Running",
            "active": True,
        },
    ]

    # Brain insights
    brain_insights = None
    if brain_data.get("last_decisions"):
        brain_insights = {
            "summary": f"Last analysis: {brain_data.get('last_run', 'N/A')[:16]}",
            "actions": [
                {"type": d.get("action", "?"), "adset_name": d.get("adset", "?"), "reason": d.get("reason", "?")}
                for d in brain_data.get("last_decisions", [])
            ],
        }

    kpi = {
        "leads_today": leads_today,
        "spend_today": f"{spend_today:.0f}",
        "cpl_today": cpl_today,
        "cpl_color": cpl_color,
        "leads_7d": "—",
        "spend_7d": "—",
        "active_agents": sum(1 for a in agents if a["active"]),
        "agent_status": "All systems operational",
    }

    return render_template_string(
        DASHBOARD_HTML,
        kpi=kpi,
        campaigns=campaigns,
        agents=agents,
        brain_insights=brain_insights,
        content_previews=content_previews,
        log_lines=get_recent_logs(),
    )


@app.route("/api/status")
def api_status():
    """JSON API for agent status."""
    lead_data = load_json_safe(DATA_DIR / "lead_counts.json")
    brain_data = load_json_safe(DATA_DIR / "brain_history.json")
    return jsonify({
        "leads_today": lead_data.get("total_leads", 0),
        "spend_today": lead_data.get("total_spend", 0),
        "brain_last_run": brain_data.get("last_run"),
        "brain_decisions": brain_data.get("last_decisions", []),
        "timestamp": datetime.now().isoformat(),
    })


def _get_last_log_time(agent_name):
    """Get last log timestamp for an agent."""
    log_file = LOG_DIR / f"{agent_name}.log"
    if not log_file.exists():
        # Check old log files in project root
        old_log = PROJECT_ROOT / f"{agent_name}_log.txt"
        if old_log.exists():
            try:
                with open(old_log, encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        last = lines[-1].strip()
                        if "]" in last:
                            return last[1:last.index("]")]
            except:
                pass
        return "Never"
    try:
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last = lines[-1].strip()
                if "]" in last:
                    return last[1:last.index("]")]
    except:
        pass
    return "Unknown"


if __name__ == "__main__":
    print("Starting Mangalya Agent Dashboard at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
