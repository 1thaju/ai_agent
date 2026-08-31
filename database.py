import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path("bookings.db")
VALID_ACTIONS = ("confirm", "cancel", "reschedule", "inquiry")
VALID_STATUS = ("pending", "confirmed", "needs_followup")


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_action(raw_action: str | None) -> str:
    """Normalize a user/LLM intent into one of the canonical actions."""
    if raw_action is None:
        return "inquiry"

    normalized = raw_action.strip().lower()
    aliases = {
        "confirm": "confirm",
        "confirmed": "confirm",
        "confirmation": "confirm",
        "book": "confirm",
        "booking": "confirm",
        "cancel": "cancel",
        "canceled": "cancel",
        "cancelled": "cancel",
        "reschedule": "reschedule",
        "rescheduled": "reschedule",
        "move": "reschedule",
        "date change": "reschedule",
        "question": "inquiry",
        "inquiry": "inquiry",
        "ask": "inquiry",
        "info": "inquiry",
        "details": "inquiry",
    }
    return aliases.get(normalized, "inquiry")


def classify_booking_action(transcript: str) -> str:
    """Rule-based intent classification as a fallback when the LLM is uncertain."""
    text = (transcript or "").lower()

    if any(word in text for word in ("cancel", "canceled", "cancelled", "not interested", "don't want", "stop")):
        return "cancel"
    if any(word in text for word in ("reschedule", "rescheduled", "move the appointment", "different time", "another time", "change date")):
        return "reschedule"
    if any(word in text for word in ("confirm", "confirmed", "yes", "okay", "sounds good", "book it", "proceed")):
        return "confirm"
    return "inquiry"


def init_db(db_path: str | Path | None = None):
    """Create the booking tables if they do not exist yet."""
    conn = _connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS call_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('confirm', 'cancel', 'reschedule', 'inquiry')),
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'needs_followup')),
            customer_transcript TEXT NOT NULL,
            agent_reply TEXT NOT NULL,
            summary TEXT,
            details_json TEXT DEFAULT '{}',
            confidence REAL DEFAULT 0.0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS booking_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            action TEXT,
            status TEXT,
            summary TEXT,
            details_json TEXT,
            last_updated TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def save_call_event(
    action: str,
    customer_transcript: str,
    agent_reply: str,
    *,
    summary: str = "",
    details: dict[str, Any] | str | None = None,
    status: str = "pending",
    confidence: float = 0.0,
    db_path: str | Path | None = None,
) -> int:
    """Save one end-to-end call outcome in a structured, queryable form."""
    normalized_action = normalize_action(action)
    if normalized_action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported action: {action!r}")

    normalized_status = status.strip().lower()
    if normalized_status not in VALID_STATUS:
        raise ValueError(f"Unsupported status: {status!r}")

    if details is None:
        details_payload = {}
    elif isinstance(details, str):
        details_payload = {"note": details}
    elif isinstance(details, dict):
        details_payload = details
    else:
        details_payload = {"value": details}

    created_at = datetime.now(timezone.utc).isoformat()
    conn = _connect(db_path)
    cursor = conn.execute(
        """
        INSERT INTO call_events (
            created_at, action, status, customer_transcript, agent_reply, summary, details_json, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            created_at,
            normalized_action,
            normalized_status,
            customer_transcript,
            agent_reply,
            summary,
            json.dumps(details_payload, ensure_ascii=False),
            float(confidence),
        ),
    )
    conn.execute(
        """
        INSERT INTO booking_state (id, action, status, summary, details_json, last_updated)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            action = excluded.action,
            status = excluded.status,
            summary = excluded.summary,
            details_json = excluded.details_json,
            last_updated = excluded.last_updated
        """,
        (
            normalized_action,
            normalized_status,
            summary,
            json.dumps(details_payload, ensure_ascii=False),
            created_at,
        ),
    )
    conn.commit()
    conn.close()
    return int(cursor.lastrowid)


def get_recent_events(limit: int = 50, db_path: str | Path | None = None):
    """Return recent events sorted newest first."""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT * FROM call_events ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_latest_booking_state(db_path: str | Path | None = None):
    """Return the latest structured booking state."""
    conn = _connect(db_path)
    row = conn.execute("SELECT * FROM booking_state WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None
