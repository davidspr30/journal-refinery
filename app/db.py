"""
db.py

Handles the SQLite database connection and schema creation.

Usage:
    from app.db import get_connection, init_db

    init_db()                  # called once at startup
    conn = get_connection()    # called per request when needed
    conn.close()               # always close when done
"""

import sqlite3
from app.config import DATABASE_PATH


def get_connection():
    """
    Open and return a connection to the SQLite database.

    Callers are responsible for closing the connection when done.
    row_factory is set so that rows can be accessed by column name
    (e.g. row["name"]) rather than only by index.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enforce foreign key constraints on every connection.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Create all tables if they do not already exist.

    Safe to call on every startup — the IF NOT EXISTS clause means
    it will never overwrite existing data.
    """
    conn = get_connection()
    try:
        _create_tables(conn)
        conn.commit()
    finally:
        conn.close()


def _create_tables(conn):
    """Run all CREATE TABLE IF NOT EXISTS statements."""

    conn.execute("""
        CREATE TABLE IF NOT EXISTS context_packs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            version     INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS prompt_profiles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            version     INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at            TEXT    NOT NULL,
            transcript_raw        TEXT    NOT NULL,
            context_pack_id       INTEGER REFERENCES context_packs(id),
            prompt_profile_id     INTEGER REFERENCES prompt_profiles(id),
            context_pack_version  INTEGER,
            prompt_profile_version INTEGER,
            output_polished       TEXT,
            output_ambiguities    TEXT,
            status                TEXT    NOT NULL DEFAULT 'pending'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at            TEXT    NOT NULL,
            entry_date            TEXT    NOT NULL,
            run_id                INTEGER REFERENCES runs(id),
            transcript_raw        TEXT    NOT NULL,
            output_polished       TEXT    NOT NULL,
            output_ambiguities    TEXT,
            context_pack_id       INTEGER REFERENCES context_packs(id),
            prompt_profile_id     INTEGER REFERENCES prompt_profiles(id),
            context_pack_version  INTEGER,
            prompt_profile_version INTEGER
        )
    """)

    # settings stores simple key/value pairs for app-level configuration,
    # such as the default context pack or prompt profile selection.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
