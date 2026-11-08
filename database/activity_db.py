import sqlite3
from datetime import datetime

DATABASE_PATH = "database/focusai.db"


def initialize_activity_database():
    """Create the activities table and ensure its session_id column exists."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                application TEXT NOT NULL,
                activity_title TEXT,
                url TEXT,
                category TEXT NOT NULL,
                duration_seconds INTEGER DEFAULT 0,
                session_id INTEGER
            )
        """)
        columns = connection.execute(
            "PRAGMA table_info(activities)"
        ).fetchall()
        column_names = [column[1] for column in columns]

        # Safe migration for databases created before session tracking existed.
        if "session_id" not in column_names:
            connection.execute(
                "ALTER TABLE activities ADD COLUMN session_id INTEGER"
            )


def add_session_id_column():
    """Idempotently add session_id to an existing activities table if needed."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        columns = connection.execute(
            "PRAGMA table_info(activities)"
        ).fetchall()
        column_names = [column[1] for column in columns]

        if "session_id" not in column_names:
            connection.execute(
                "ALTER TABLE activities ADD COLUMN session_id INTEGER"
            )


def save_activity(
    application,
    activity_title,
    url,
    category,
    duration_seconds=0,
    session_id=None,
):
    """Save one completed activity and associate it with a session when provided."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        timestamp = datetime.now().isoformat()
        connection.execute("""
            INSERT INTO activities (
                timestamp,
                application,
                activity_title,
                url,
                category,
                duration_seconds,
                session_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            application,
            activity_title,
            url,
            category,
            duration_seconds,
            session_id,
        ))


def get_activities():
    with sqlite3.connect(DATABASE_PATH) as connection:
        return connection.execute("""
            SELECT
                id,
                timestamp,
                application,
                activity_title,
                url,
                category,
                duration_seconds,
                session_id
            FROM activities
            ORDER BY id DESC
        """).fetchall()


def get_session_activities(session_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        return connection.execute("""
            SELECT
                id,
                timestamp,
                application,
                activity_title,
                url,
                category,
                duration_seconds,
                session_id
            FROM activities
            WHERE session_id = ?
            ORDER BY id ASC
        """, (session_id,)).fetchall()
