"""
Mangalya CRM Database — SQLite storage for leads, campaigns, brain decisions,
follow-ups, daily metrics, and video jobs.

Replaces JSON file storage with proper relational database.
All agents use this module via BaseAgent.db.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = os.getenv(
    "DB_PATH",
    str(Path(__file__).resolve().parent / "data" / "mangalya.db"),
)


def get_db():
    """Get a database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            community TEXT,
            gender TEXT,
            age INTEGER,
            source TEXT DEFAULT 'meta_lead_ad',
            source_campaign TEXT,
            source_adset TEXT,
            status TEXT DEFAULT 'new',
            meta_lead_id TEXT UNIQUE,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_campaign_id TEXT UNIQUE,
            name TEXT,
            objective TEXT,
            status TEXT,
            created_by TEXT DEFAULT 'manual',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ad_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_adset_id TEXT UNIQUE,
            meta_campaign_id TEXT,
            name TEXT,
            daily_budget INTEGER,
            status TEXT,
            targeting_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS brain_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            adset_id TEXT,
            adset_name TEXT,
            old_budget INTEGER,
            new_budget INTEGER,
            reason TEXT,
            analysis_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER REFERENCES leads(id),
            sequence_step TEXT,
            scheduled_at TEXT,
            sent_at TEXT,
            status TEXT DEFAULT 'pending',
            message_id TEXT,
            error_message TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            adset_id TEXT,
            adset_name TEXT,
            leads INTEGER DEFAULT 0,
            spend REAL DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            ctr REAL DEFAULT 0,
            cost_per_lead REAL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(date, adset_id)
        );

        CREATE TABLE IF NOT EXISTS video_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            community TEXT,
            theme TEXT,
            script_json TEXT,
            provider TEXT DEFAULT 'pictory',
            provider_job_id TEXT,
            status TEXT DEFAULT 'script_generated',
            video_local_path TEXT,
            meta_video_id TEXT,
            meta_creative_id TEXT,
            meta_ad_id TEXT,
            error_message TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
        CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
        CREATE INDEX IF NOT EXISTS idx_follow_ups_pending ON follow_ups(status, scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(date);
        CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON video_jobs(status);
    """)
    conn.commit()
    conn.close()


# ── Leads ─────────────────────────────────────────────────────────────────────

def add_lead(name, phone, email=None, community=None, gender=None, age=None,
             source="meta_lead_ad", source_campaign=None, source_adset=None,
             meta_lead_id=None):
    """Insert a new lead. Returns lead ID, or None if duplicate."""
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO leads
               (name, phone, email, community, gender, age, source,
                source_campaign, source_adset, meta_lead_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, normalize_phone(phone), email, community, gender, age,
             source, source_campaign, source_adset, meta_lead_id),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_lead(lead_id):
    """Get a lead by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_lead_by_phone(phone):
    """Get a lead by phone number."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM leads WHERE phone = ?", (normalize_phone(phone),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_leads(status=None, since=None, limit=100):
    """Get leads with optional filters."""
    conn = get_db()
    query = "SELECT * FROM leads WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if since:
        query += " AND created_at >= ?"
        params.append(since)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_new_leads_since(minutes=10):
    """Get leads created in the last N minutes with status 'new'."""
    since = (datetime.utcnow() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    return get_leads(status="new", since=since)


def update_lead_status(lead_id, status):
    """Update a lead's status."""
    conn = get_db()
    conn.execute(
        "UPDATE leads SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, lead_id),
    )
    conn.commit()
    conn.close()


def get_lead_count(status=None):
    """Get total lead count, optionally filtered by status."""
    conn = get_db()
    if status:
        row = conn.execute("SELECT COUNT(*) FROM leads WHERE status = ?", (status,)).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM leads").fetchone()
    conn.close()
    return row[0]


# ── Campaigns & Ad Sets ───────────────────────────────────────────────────────

def upsert_campaign(meta_campaign_id, name, objective, status, created_by="manual"):
    """Insert or update a campaign record."""
    conn = get_db()
    conn.execute(
        """INSERT INTO campaigns (meta_campaign_id, name, objective, status, created_by)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(meta_campaign_id) DO UPDATE SET
             name=excluded.name, status=excluded.status, updated_at=datetime('now')""",
        (meta_campaign_id, name, objective, status, created_by),
    )
    conn.commit()
    conn.close()


def upsert_adset(meta_adset_id, meta_campaign_id, name, daily_budget, status,
                 targeting_json=None):
    """Insert or update an ad set record."""
    conn = get_db()
    conn.execute(
        """INSERT INTO ad_sets (meta_adset_id, meta_campaign_id, name, daily_budget, status, targeting_json)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(meta_adset_id) DO UPDATE SET
             name=excluded.name, daily_budget=excluded.daily_budget,
             status=excluded.status, updated_at=datetime('now')""",
        (meta_adset_id, meta_campaign_id, name, daily_budget, status, targeting_json),
    )
    conn.commit()
    conn.close()


# ── Brain Decisions ───────────────────────────────────────────────────────────

def add_brain_decision(action_type, adset_id=None, adset_name=None,
                       old_budget=None, new_budget=None, reason=None,
                       analysis_json=None):
    """Log a brain decision."""
    conn = get_db()
    conn.execute(
        """INSERT INTO brain_decisions
           (action_type, adset_id, adset_name, old_budget, new_budget, reason, analysis_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (action_type, adset_id, adset_name, old_budget, new_budget, reason, analysis_json),
    )
    conn.commit()
    conn.close()


def get_brain_history(limit=50):
    """Get recent brain decisions."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM brain_decisions ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Follow-ups ────────────────────────────────────────────────────────────────

def schedule_follow_ups(lead_id):
    """Schedule the full WhatsApp follow-up sequence for a lead."""
    now = datetime.utcnow()
    steps = [
        ("welcome", now),
        ("day1_matches", now + timedelta(days=1)),
        ("day3_views", now + timedelta(days=3)),
        ("day7_upgrade", now + timedelta(days=7)),
    ]
    conn = get_db()
    for step, scheduled_at in steps:
        conn.execute(
            """INSERT INTO follow_ups (lead_id, sequence_step, scheduled_at)
               VALUES (?, ?, ?)""",
            (lead_id, step, scheduled_at.strftime("%Y-%m-%d %H:%M:%S")),
        )
    conn.commit()
    conn.close()


def get_pending_follow_ups(limit=50):
    """Get follow-ups that are due to be sent."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    rows = conn.execute(
        """SELECT f.*, l.name as lead_name, l.phone as lead_phone,
                  l.community as lead_community, l.gender as lead_gender
           FROM follow_ups f
           JOIN leads l ON f.lead_id = l.id
           WHERE f.status = 'pending' AND f.scheduled_at <= ?
           ORDER BY f.scheduled_at ASC LIMIT ?""",
        (now, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_follow_up_sent(follow_up_id, message_id=None):
    """Mark a follow-up as sent."""
    conn = get_db()
    conn.execute(
        """UPDATE follow_ups
           SET status = 'sent', sent_at = datetime('now'), message_id = ?
           WHERE id = ?""",
        (message_id, follow_up_id),
    )
    conn.commit()
    conn.close()


def mark_follow_up_failed(follow_up_id, error_message=None):
    """Mark a follow-up as failed."""
    conn = get_db()
    conn.execute(
        """UPDATE follow_ups
           SET status = 'failed', error_message = ?
           WHERE id = ?""",
        (error_message, follow_up_id),
    )
    conn.commit()
    conn.close()


def has_welcome_been_sent(lead_id):
    """Check if welcome message has already been sent/scheduled for a lead."""
    conn = get_db()
    row = conn.execute(
        """SELECT COUNT(*) FROM follow_ups
           WHERE lead_id = ? AND sequence_step = 'welcome'""",
        (lead_id,),
    ).fetchone()
    conn.close()
    return row[0] > 0


# ── Daily Metrics ─────────────────────────────────────────────────────────────

def upsert_daily_metrics(date, adset_id, adset_name=None, leads=0, spend=0.0,
                         impressions=0, clicks=0, ctr=0.0, cost_per_lead=None):
    """Insert or update daily metrics for an ad set."""
    conn = get_db()
    conn.execute(
        """INSERT INTO daily_metrics
           (date, adset_id, adset_name, leads, spend, impressions, clicks, ctr, cost_per_lead)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(date, adset_id) DO UPDATE SET
             leads=excluded.leads, spend=excluded.spend,
             impressions=excluded.impressions, clicks=excluded.clicks,
             ctr=excluded.ctr, cost_per_lead=excluded.cost_per_lead""",
        (date, adset_id, adset_name, leads, spend, impressions, clicks, ctr, cost_per_lead),
    )
    conn.commit()
    conn.close()


def get_daily_metrics(date=None, adset_id=None):
    """Get daily metrics, optionally filtered."""
    conn = get_db()
    query = "SELECT * FROM daily_metrics WHERE 1=1"
    params = []
    if date:
        query += " AND date = ?"
        params.append(date)
    if adset_id:
        query += " AND adset_id = ?"
        params.append(adset_id)
    query += " ORDER BY date DESC, adset_name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Video Jobs ────────────────────────────────────────────────────────────────

def create_video_job(community, theme, script_json, provider="pictory"):
    """Create a new video generation job. Returns job ID."""
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO video_jobs (community, theme, script_json, provider)
           VALUES (?, ?, ?, ?)""",
        (community, theme, script_json, provider),
    )
    conn.commit()
    job_id = cur.lastrowid
    conn.close()
    return job_id


def update_video_job(job_id, **kwargs):
    """Update a video job's fields. Pass any column as keyword arg."""
    allowed = {
        "status", "provider_job_id", "video_local_path", "meta_video_id",
        "meta_creative_id", "meta_ad_id", "error_message",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    conn = get_db()
    conn.execute(f"UPDATE video_jobs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_video_jobs(status=None, limit=20):
    """Get video jobs, optionally filtered by status."""
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM video_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM video_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_video_job(job_id):
    """Get a single video job by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM video_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_phone(phone):
    """Normalize Indian phone number to 91XXXXXXXXXX format."""
    if not phone:
        return phone
    phone = str(phone).strip().replace(" ", "").replace("-", "").replace("+", "")
    if len(phone) == 10 and phone[0] in "6789":
        phone = "91" + phone
    return phone


def get_stats():
    """Get overall CRM stats for dashboard."""
    conn = get_db()
    stats = {}
    stats["total_leads"] = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    stats["new_leads"] = conn.execute("SELECT COUNT(*) FROM leads WHERE status='new'").fetchone()[0]
    stats["contacted"] = conn.execute("SELECT COUNT(*) FROM leads WHERE status='contacted'").fetchone()[0]
    stats["follow_ups_pending"] = conn.execute("SELECT COUNT(*) FROM follow_ups WHERE status='pending'").fetchone()[0]
    stats["follow_ups_sent"] = conn.execute("SELECT COUNT(*) FROM follow_ups WHERE status='sent'").fetchone()[0]
    stats["brain_decisions_today"] = conn.execute(
        "SELECT COUNT(*) FROM brain_decisions WHERE date(created_at) = date('now')"
    ).fetchone()[0]
    stats["video_jobs_active"] = conn.execute(
        "SELECT COUNT(*) FROM video_jobs WHERE status NOT IN ('failed', 'ad_created')"
    ).fetchone()[0]
    conn.close()
    return stats


# Initialize DB on import
init_db()
