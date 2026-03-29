"""
AI Brain Agent — The smart strategist that uses Claude API to analyze
ad performance and make intelligent optimization decisions.

Unlike the simple threshold-based optimizer, this agent:
- Considers trends (is performance improving or declining?)
- Detects creative fatigue (CTR dropping over time)
- Makes budget reallocation decisions across campaigns
- Generates actionable recommendations in plain language
- Sends analysis to Telegram

Runs every 6 hours via Task Scheduler.
"""

import os
import json
from datetime import datetime
from base import BaseAgent
from telegram_bot import send_brain_report, send_message

try:
    import anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False


class BrainAgent(BaseAgent):
    name = "brain"

    # Safety limits
    MAX_BUDGET_INCREASE = 1.5  # Max 50% increase at once
    MAX_BUDGET_DECREASE = 0.5  # Max 50% decrease at once
    MIN_BUDGET_RUPEES = 100    # Never go below Rs.100/day
    MAX_BUDGET_RUPEES = 2000   # Never go above Rs.2000/day without manual approval

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.history_file = "brain_history.json"
        self.actions_log = "brain_actions.json"

    def gather_data(self):
        """Gather all performance data for AI analysis."""
        self.log("Gathering performance data...")

        # Get data for multiple time windows
        data = {
            "today": self.get_all_adsets_performance("today"),
            "last_3d": self.get_all_adsets_performance("last_3d"),
            "last_7d": self.get_all_adsets_performance("last_7d"),
            "timestamp": datetime.now().isoformat(),
        }

        # Load historical brain decisions
        history = self.load_json(self.history_file)
        data["previous_decisions"] = history.get("last_decisions", [])
        data["previous_analysis_date"] = history.get("last_run", "never")

        return data

    def format_data_for_ai(self, data):
        """Format collected data into a prompt for Claude."""
        lines = []
        lines.append("# Mangalya Matrimony — Ad Performance Data")
        lines.append(f"Analysis time: {data['timestamp']}")
        lines.append(f"Previous analysis: {data['previous_analysis_date']}")
        lines.append("")

        for period_name, period_key in [("TODAY", "today"), ("LAST 3 DAYS", "last_3d"), ("LAST 7 DAYS", "last_7d")]:
            lines.append(f"## {period_name}")
            period_data = data[period_key]
            if not period_data:
                lines.append("No data available.")
                lines.append("")
                continue

            total_spend = sum(p["spend"] for p in period_data)
            total_leads = sum(p["leads"] for p in period_data)

            for p in period_data:
                cpl_str = f"Rs.{p['cost_per_lead']}" if p["cost_per_lead"] else "N/A"
                lines.append(
                    f"- {p['name']} [{p['status']}] "
                    f"Budget: Rs.{p['daily_budget']//100}/day | "
                    f"Impressions: {p['impressions']} | "
                    f"Clicks: {p['clicks']} | "
                    f"CTR: {p['ctr']:.2f}% | "
                    f"Spend: Rs.{p['spend']:.0f} | "
                    f"Leads: {p['leads']} | "
                    f"CPL: {cpl_str}"
                )
            lines.append(f"TOTAL: Rs.{total_spend:.0f} spent, {total_leads} leads")
            if total_leads > 0:
                lines.append(f"Average CPL: Rs.{total_spend/total_leads:.0f}")
            lines.append("")

        if data["previous_decisions"]:
            lines.append("## Previous Decisions")
            for d in data["previous_decisions"][-5:]:
                lines.append(f"- [{d.get('date', '?')}] {d.get('action', '?')}: {d.get('reason', '?')}")
            lines.append("")

        return "\n".join(lines)

    def ask_claude(self, performance_data):
        """Send data to Claude API for analysis."""
        if not HAS_CLAUDE or not self.api_key:
            return self.fallback_analysis(performance_data)

        client = anthropic.Anthropic(api_key=self.api_key)

        system_prompt = """You are the AI Brain for Mangalya Matrimony's ad campaigns.
You analyze Meta ad performance data and make optimization decisions.

Your goals:
1. Maximize signups (leads) while keeping cost per lead under Rs.80
2. Identify which audiences/campaigns are performing best
3. Detect problems early (creative fatigue, audience saturation, budget waste)
4. Recommend budget reallocations — move money from poor performers to good ones

Rules:
- Budget changes: max 50% increase or decrease at a time
- Min budget: Rs.100/day per ad set
- Max budget: Rs.2000/day per ad set (flag if higher needed)
- If CTR < 0.5% for 3 days, recommend pausing
- If CPL > Rs.100, recommend reducing budget
- If CPL < Rs.40 with 3+ leads, recommend scaling up
- Always consider trends (improving vs declining)

Respond in this JSON format:
{
  "summary": "2-3 sentence overview",
  "actions": [
    {
      "type": "adjust_budget|pause|resume|no_change",
      "adset_id": "...",
      "adset_name": "...",
      "current_budget_rupees": 200,
      "new_budget_rupees": 250,
      "reason": "..."
    }
  ],
  "insights": ["insight 1", "insight 2"],
  "risk_alerts": ["alert if any"],
  "telegram_message": "A short, readable summary for Telegram (max 500 chars)"
}"""

        formatted = self.format_data_for_ai(performance_data)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"Analyze this ad performance data and recommend actions:\n\n{formatted}"}
            ],
        )

        # Parse response
        response_text = message.content[0].text
        try:
            # Try to extract JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            self.log_error(f"Could not parse AI response as JSON: {response_text[:200]}")
            return {
                "summary": response_text[:500],
                "actions": [],
                "insights": [],
                "risk_alerts": [],
                "telegram_message": response_text[:500],
            }

    def fallback_analysis(self, data):
        """Simple rule-based analysis when Claude API is not available."""
        self.log("Using fallback rule-based analysis (no Claude API key)")
        actions = []
        insights = []

        for p in data.get("last_3d", []):
            if p["status"] != "ACTIVE":
                continue

            budget_rs = p["daily_budget"] // 100
            cpl = p["cost_per_lead"]

            if p["impressions"] == 0:
                insights.append(f"{p['name']}: No impressions — check ad approval")
            elif p["ctr"] < 0.5:
                actions.append({
                    "type": "pause",
                    "adset_id": p["adset_id"],
                    "adset_name": p["name"],
                    "current_budget_rupees": budget_rs,
                    "new_budget_rupees": budget_rs,
                    "reason": f"CTR {p['ctr']:.2f}% below 0.5% threshold",
                })
            elif cpl and cpl > 100:
                new_budget = max(int(budget_rs * 0.75), self.MIN_BUDGET_RUPEES)
                actions.append({
                    "type": "adjust_budget",
                    "adset_id": p["adset_id"],
                    "adset_name": p["name"],
                    "current_budget_rupees": budget_rs,
                    "new_budget_rupees": new_budget,
                    "reason": f"CPL Rs.{cpl:.0f} too high — reducing budget 25%",
                })
            elif cpl and cpl < 40 and p["leads"] >= 3:
                factor = 1.5 if (p["ctr"] >= 1.0 and p["leads"] >= 5) else 1.25
                new_budget = min(int(budget_rs * factor), self.MAX_BUDGET_RUPEES)
                actions.append({
                    "type": "adjust_budget",
                    "adset_id": p["adset_id"],
                    "adset_name": p["name"],
                    "current_budget_rupees": budget_rs,
                    "new_budget_rupees": new_budget,
                    "reason": f"CPL Rs.{cpl:.0f} is good with {p['leads']} leads — scaling up",
                })
            else:
                actions.append({
                    "type": "no_change",
                    "adset_id": p["adset_id"],
                    "adset_name": p["name"],
                    "current_budget_rupees": budget_rs,
                    "new_budget_rupees": budget_rs,
                    "reason": "Performance within acceptable range",
                })

        total_leads = sum(p["leads"] for p in data.get("last_3d", []))
        total_spend = sum(p["spend"] for p in data.get("last_3d", []))
        avg_cpl = round(total_spend / total_leads, 0) if total_leads > 0 else 0

        summary = f"Last 3 days: {total_leads} leads, Rs.{total_spend:.0f} spent, Avg CPL: Rs.{avg_cpl}"
        telegram_msg = f"📊 {summary}\n" + "\n".join(
            f"{'⬆️' if a['type'] == 'adjust_budget' and a['new_budget_rupees'] > a['current_budget_rupees'] else '⬇️' if a['type'] == 'adjust_budget' else '⏸' if a['type'] == 'pause' else '✅'} {a['adset_name']}: {a['reason']}"
            for a in actions if a["type"] != "no_change"
        ) if any(a["type"] != "no_change" for a in actions) else f"📊 {summary}\n✅ All campaigns performing well."

        return {
            "summary": summary,
            "actions": actions,
            "insights": insights,
            "risk_alerts": [],
            "telegram_message": telegram_msg,
        }

    def execute_actions(self, analysis):
        """Execute the recommended actions (with safety checks)."""
        from facebook_business.adobjects.adset import AdSet

        executed = []
        for action in analysis.get("actions", []):
            if action["type"] == "no_change":
                continue

            adset_id = action.get("adset_id")
            if not adset_id:
                continue

            try:
                if action["type"] == "pause":
                    AdSet(adset_id).api_update(params={"status": "PAUSED"})
                    self.log(f"PAUSED: {action['adset_name']} — {action['reason']}")
                    executed.append(action)

                elif action["type"] == "resume":
                    AdSet(adset_id).api_update(params={"status": "ACTIVE"})
                    self.log(f"RESUMED: {action['adset_name']} — {action['reason']}")
                    executed.append(action)

                elif action["type"] == "adjust_budget":
                    new_rs = action["new_budget_rupees"]
                    old_rs = action["current_budget_rupees"]

                    # Safety checks
                    if new_rs < self.MIN_BUDGET_RUPEES:
                        new_rs = self.MIN_BUDGET_RUPEES
                    if new_rs > self.MAX_BUDGET_RUPEES:
                        self.log(f"SKIPPED: {action['adset_name']} — Rs.{new_rs} exceeds max Rs.{self.MAX_BUDGET_RUPEES}")
                        continue
                    if old_rs > 0:
                        ratio = new_rs / old_rs
                        if ratio > self.MAX_BUDGET_INCREASE:
                            new_rs = int(old_rs * self.MAX_BUDGET_INCREASE)
                        elif ratio < self.MAX_BUDGET_DECREASE:
                            new_rs = int(old_rs * self.MAX_BUDGET_DECREASE)

                    AdSet(adset_id).api_update(params={"daily_budget": new_rs * 100})
                    self.log(f"BUDGET: {action['adset_name']} Rs.{old_rs} → Rs.{new_rs}/day — {action['reason']}")
                    action["new_budget_rupees"] = new_rs
                    executed.append(action)

            except Exception as e:
                self.log_error(f"Failed to execute {action['type']} on {action.get('adset_name', adset_id)}: {e}")

        return executed

    def run(self):
        self.log("=" * 50)
        self.log("AI BRAIN — Starting analysis")

        # 1. Gather data
        data = self.gather_data()

        # 2. AI analysis
        self.log("Analyzing with AI...")
        analysis = self.ask_claude(data)

        self.log(f"Summary: {analysis.get('summary', 'N/A')}")
        for insight in analysis.get("insights", []):
            self.log(f"  Insight: {insight}")
        for alert in analysis.get("risk_alerts", []):
            self.log(f"  ALERT: {alert}")

        # 3. Execute actions
        executed = self.execute_actions(analysis)
        self.log(f"Executed {len(executed)} actions")

        # 4. Send Telegram report
        telegram_msg = analysis.get("telegram_message", analysis.get("summary", "No analysis available"))
        if executed:
            action_lines = "\n".join(
                f"• {a['adset_name']}: {a['type']} — {a['reason']}"
                for a in executed
            )
            telegram_msg += f"\n\n<b>Actions Taken:</b>\n{action_lines}"
        send_brain_report(telegram_msg)

        # 5. Save history
        history = self.load_json(self.history_file)
        if "decisions" not in history:
            history["decisions"] = []

        history["last_run"] = datetime.now().isoformat()
        history["last_decisions"] = [
            {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "action": a["type"], "adset": a["adset_name"], "reason": a["reason"]}
            for a in executed
        ]
        history["decisions"].extend(history["last_decisions"])
        # Keep last 100 decisions
        history["decisions"] = history["decisions"][-100:]
        self.save_json(self.history_file, history)

        self.log("AI Brain done.\n")


if __name__ == "__main__":
    BrainAgent().run()
