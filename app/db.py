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
    Create all tables if they do not already exist, then apply any
    column migrations needed for existing databases.

    Safe to call on every startup — existing data is never touched.
    """
    conn = get_connection()
    try:
        _create_tables(conn)
        _migrate(conn)
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


def _migrate(conn):
    """
    Add columns that were introduced after the initial schema.

    This runs every startup but only makes changes when a column is
    missing — safe to call on any database, old or new.

    SQLite does not support IF NOT EXISTS on ALTER TABLE, so we check
    the existing columns via PRAGMA first.
    """
    existing_runs_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(runs)")
    }

    # Columns added in Phase 3.
    new_runs_columns = [
        ("model",             "TEXT"),
        ("assembled_request", "TEXT"),
        ("response_raw",      "TEXT"),
        ("error_message",     "TEXT"),
    ]

    for col_name, col_type in new_runs_columns:
        if col_name not in existing_runs_cols:
            conn.execute(
                f"ALTER TABLE runs ADD COLUMN {col_name} {col_type}"
            )
