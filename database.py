import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("bookings.db")


def init_db():
    """Create the bookings table if it doesn't exist yet. Call once at startup."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            action TEXT NOT NULL,          -- 'confirm', 'cancel', 'reschedule', 'inquiry'
            customer_transcript TEXT,       -- what the customer said
            agent_reply TEXT,               -- what the agent replied
            details TEXT,                   -- free-text notes (date/time mentioned, etc.)
            status TEXT DEFAULT 'pending'   -- 'pending', 'confirmed', 'needs_followup'
        )
    """)
    conn.commit()
    conn.close()


def save_booking_event(action: str, customer_transcript: str, agent_reply: str, details: str = "", status: str = "pending"):
    """Insert one booking-related event into the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO bookings (created_at, action, customer_transcript, agent_reply, details, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (datetime.now().isoformat(), action, customer_transcript, agent_reply, details, status),
    )
    conn.commit()
    conn.close()


def get_all_bookings(limit: int = 50):
    """Return recent booking events, most recent first."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM bookings ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]