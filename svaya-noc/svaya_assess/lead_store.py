"""
Lead capture: SQLite persistence + CRM webhook (HubSpot / Salesforce / n8n compatible).
Stores survey answers, maturity scores, and probe results per lead.
"""

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import requests

DB_PATH = os.getenv("ASSESS_DB_PATH", os.path.join(os.path.dirname(__file__), "leads.db"))
CRM_WEBHOOK_URL = os.getenv("CRM_WEBHOOK_URL", "")
CRM_WEBHOOK_SECRET = os.getenv("CRM_WEBHOOK_SECRET", "")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS leads (
    id           TEXT PRIMARY KEY,
    created_at   INTEGER NOT NULL,
    company      TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    email        TEXT NOT NULL,
    phone        TEXT,
    country      TEXT,
    network_size TEXT,
    answers      TEXT NOT NULL,   -- JSON
    scores       TEXT NOT NULL,   -- JSON (MaturityScore serialised)
    probe_result TEXT,            -- JSON or NULL if no probe run
    readiness    TEXT,            -- READY | PARTIAL | NEEDS_CONFIG | UNREACHABLE | null
    overall_level REAL,
    webhook_sent INTEGER DEFAULT 0,
    webhook_at   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
"""


@dataclass
class LeadRecord:
    id: str
    created_at: int
    company: str
    contact_name: str
    email: str
    phone: str
    country: str
    network_size: str
    answers: dict
    scores: dict
    probe_result: Optional[dict] = None
    readiness: Optional[str] = None
    overall_level: Optional[float] = None
    webhook_sent: bool = False
    webhook_at: Optional[int] = None


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_conn() as conn:
        conn.executescript(_DDL)


def save_lead(
    company: str,
    contact_name: str,
    email: str,
    phone: str,
    country: str,
    network_size: str,
    answers: dict,
    scores: dict,
    probe_result: Optional[dict] = None,
) -> str:
    """Persist a lead and return its UUID."""
    init_db()
    lead_id = str(uuid.uuid4())
    now = int(time.time())
    readiness = (probe_result or {}).get("astra_readiness")
    overall = scores.get("overall")

    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO leads
                (id, created_at, company, contact_name, email, phone, country,
                 network_size, answers, scores, probe_result, readiness, overall_level)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                lead_id, now, company, contact_name, email, phone or "", country or "",
                network_size or "",
                json.dumps(answers),
                json.dumps(scores),
                json.dumps(probe_result) if probe_result else None,
                readiness,
                overall,
            ),
        )

    # Fire webhook in the background (best-effort — doesn't block result page)
    if CRM_WEBHOOK_URL:
        _fire_webhook(lead_id, company, contact_name, email, phone, country,
                      network_size, scores, readiness, overall, now)

    return lead_id


def get_lead(lead_id: str) -> Optional[LeadRecord]:
    init_db()
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if not row:
        return None
    return LeadRecord(
        id=row["id"],
        created_at=row["created_at"],
        company=row["company"],
        contact_name=row["contact_name"],
        email=row["email"],
        phone=row["phone"],
        country=row["country"],
        network_size=row["network_size"],
        answers=json.loads(row["answers"]),
        scores=json.loads(row["scores"]),
        probe_result=json.loads(row["probe_result"]) if row["probe_result"] else None,
        readiness=row["readiness"],
        overall_level=row["overall_level"],
        webhook_sent=bool(row["webhook_sent"]),
        webhook_at=row["webhook_at"],
    )


# ---------------------------------------------------------------------------
# CRM webhook
# ---------------------------------------------------------------------------

def _fire_webhook(
    lead_id: str,
    company: str,
    contact_name: str,
    email: str,
    phone: str,
    country: str,
    network_size: str,
    scores: dict,
    readiness: Optional[str],
    overall_level: Optional[float],
    created_at: int,
) -> None:
    payload = {
        "source": "svaya_assess",
        "lead_id": lead_id,
        "created_at": created_at,
        "contact": {
            "name": contact_name,
            "email": email,
            "phone": phone,
            "company": company,
            "country": country,
            "network_size": network_size,
        },
        "maturity": {
            "overall_level": overall_level,
            "level_label": scores.get("level"),
            "domains": scores.get("domains", {}),
        },
        "network_readiness": readiness,
        "utm_source": "astra_assessment",
    }
    headers = {"Content-Type": "application/json"}
    if CRM_WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = CRM_WEBHOOK_SECRET

    try:
        resp = requests.post(CRM_WEBHOOK_URL, json=payload, headers=headers, timeout=8)
        sent = resp.status_code < 300
    except Exception:
        sent = False

    try:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE leads SET webhook_sent=?, webhook_at=? WHERE id=?",
                (int(sent), int(time.time()), lead_id),
            )
    except Exception:
        pass
