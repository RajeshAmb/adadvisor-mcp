"""
One-time migration: Move existing JSON data into SQLite database.
Run once: python migrate_json_to_db.py

Does NOT delete JSON files — they remain as backup.
"""

import json
from pathlib import Path
import database as db

DATA_DIR = Path(__file__).resolve().parent / "data"


def migrate_lead_counts():
    """Migrate data/lead_counts.json → daily_metrics table."""
    path = DATA_DIR / "lead_counts.json"
    if not path.exists():
        print("No lead_counts.json found — skipping")
        return 0

    data = json.loads(path.read_text(encoding="utf-8"))
    date = data.get("date", "unknown")
    count = 0

    for adset_id, metrics in data.get("adsets", {}).items():
        try:
            db.upsert_daily_metrics(
                date=date,
                adset_id=adset_id,
                leads=metrics.get("leads", 0),
                spend=metrics.get("spend", 0.0),
            )
            count += 1
        except Exception as e:
            print(f"  Error migrating adset {adset_id}: {e}")

    print(f"Migrated {count} ad set metrics from lead_counts.json")
    return count


def migrate_brain_history():
    """Migrate data/brain_history.json → brain_decisions table."""
    path = DATA_DIR / "brain_history.json"
    if not path.exists():
        print("No brain_history.json found — skipping")
        return 0

    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0

    for decision in data.get("last_decisions", []):
        try:
            db.add_brain_decision(
                action_type=decision.get("action", decision.get("type", "unknown")),
                adset_id=decision.get("adset_id"),
                adset_name=decision.get("adset_name"),
                old_budget=decision.get("current_budget_rupees"),
                new_budget=decision.get("new_budget_rupees"),
                reason=decision.get("reason", ""),
                analysis_json=json.dumps(decision),
            )
            count += 1
        except Exception as e:
            print(f"  Error migrating brain decision: {e}")

    print(f"Migrated {count} brain decisions from brain_history.json")
    return count


def migrate_brain_actions():
    """Migrate data/brain_actions.json → brain_decisions table."""
    path = DATA_DIR / "brain_actions.json"
    if not path.exists():
        print("No brain_actions.json found — skipping")
        return 0

    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0

    actions = data if isinstance(data, list) else data.get("actions", [])
    for action in actions:
        try:
            db.add_brain_decision(
                action_type=action.get("type", "unknown"),
                adset_id=action.get("adset_id"),
                adset_name=action.get("adset_name"),
                old_budget=action.get("old_budget"),
                new_budget=action.get("new_budget"),
                reason=action.get("reason", ""),
                analysis_json=json.dumps(action),
            )
            count += 1
        except Exception as e:
            print(f"  Error migrating brain action: {e}")

    print(f"Migrated {count} brain actions from brain_actions.json")
    return count


if __name__ == "__main__":
    print("=" * 50)
    print("MANGALYA JSON -> SQLite MIGRATION")
    print("=" * 50)

    db.init_db()
    print(f"Database: {db.DB_PATH}")
    print()

    total = 0
    total += migrate_lead_counts()
    total += migrate_brain_history()
    total += migrate_brain_actions()

    print()
    print(f"Migration complete. {total} records migrated.")
    print(f"JSON files kept as backup in {DATA_DIR}")

    stats = db.get_stats()
    print(f"\nDB Stats: {stats}")
