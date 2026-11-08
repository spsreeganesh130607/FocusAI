import sqlite3


DATABASE_PATH = "database/focusai.db"


def initialize_database():

    connection = sqlite3.connect(DATABASE_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_seconds INTEGER DEFAULT 0,
            status TEXT
        )
    """)

    connection.commit()
    connection.close()


def create_session(start_time):

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO sessions (
            start_time,
            end_time,
            duration_seconds,
            status
        )
        VALUES (?, NULL, 0, ?)
    """, (
        start_time,
        "running"
    ))

    session_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return session_id


def finish_session(
    session_id,
    end_time,
    duration_seconds,
    status="stopped"
):

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    cursor.execute("""
        UPDATE sessions
        SET
            end_time = ?,
            duration_seconds = ?,
            status = ?
        WHERE id = ?
    """, (
        end_time,
        duration_seconds,
        status,
        session_id
    ))

    connection.commit()
    connection.close()


def save_session(
    start_time,
    end_time,
    duration_seconds,
    status
):

    """
    Kept for compatibility with older code.
    Creates a complete session in one operation.
    """

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO sessions (
            start_time,
            end_time,
            duration_seconds,
            status
        )
        VALUES (?, ?, ?, ?)
    """, (
        start_time,
        end_time,
        duration_seconds,
        status
    ))

    session_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return session_id


def get_sessions():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            start_time,
            end_time,
            duration_seconds,
            status
        FROM sessions
        ORDER BY id DESC
    """)

    sessions = cursor.fetchall()

    connection.close()

    return sessions