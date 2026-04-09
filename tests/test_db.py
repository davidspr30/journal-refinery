"""
test_db.py

Tests for database initialisation (app/db.py).

These tests use an in-memory SQLite database so nothing is written to
data/journal.db. They verify that:
  - all five tables are created by _create_tables + _migrate
  - each table has the columns the app depends on
  - calling _migrate() twice does not crash or create duplicate columns
"""

import sqlite3

from app.db import _create_tables, _migrate


def _make_db():
    """Return an in-memory connection with the full schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    _migrate(conn)
    conn.commit()
    return conn


def _table_names(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row["name"] for row in rows}


def _column_names(conn, table):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


# ---------------------------------------------------------------------------
# Table presence
# ---------------------------------------------------------------------------

def test_all_five_tables_exist():
    conn = _make_db()
    tables = _table_names(conn)
    for name in ("context_packs", "prompt_profiles", "runs", "entries", "settings"):
        assert name in tables, f"Table '{name}' was not created"
    conn.close()


# ---------------------------------------------------------------------------
# Required columns
# ---------------------------------------------------------------------------

def test_runs_has_required_columns():
    conn = _make_db()
    cols = _column_names(conn, "runs")
    required = {
        "id", "created_at", "transcript_raw",
        "model", "assembled_request", "response_raw",
        "output_polished", "output_ambiguities",
        "status", "error_message",
        "context_pack_id", "context_pack_version",
        "prompt_profile_id", "prompt_profile_version",
    }
    missing = required - cols
    assert not missing, f"Columns missing from runs: {missing}"
    conn.close()


def test_entries_has_required_columns():
    conn = _make_db()
    cols = _column_names(conn, "entries")
    required = {
        "id", "created_at", "updated_at", "entry_date",
        "run_id", "title", "transcript_raw",
        "output_polished", "output_ambiguities",
        "context_pack_id", "context_pack_version",
        "context_pack_name",
        "prompt_profile_id", "prompt_profile_version",
        "prompt_profile_name",
    }
    missing = required - cols
    assert not missing, f"Columns missing from entries: {missing}"
    conn.close()


def test_settings_has_key_and_value_columns():
    conn = _make_db()
    cols = _column_names(conn, "settings")
    assert "key" in cols
    assert "value" in cols
    conn.close()


# ---------------------------------------------------------------------------
# Migration idempotency
# ---------------------------------------------------------------------------

def test_migrate_twice_does_not_crash():
    """Running _migrate() on an already-migrated database must be a no-op."""
    conn = sqlite3.connect(":memory:")
    _create_tables(conn)
    _migrate(conn)
    _migrate(conn)  # second call — must not raise
    conn.close()


def test_migrate_does_not_duplicate_columns():
    conn = sqlite3.connect(":memory:")
    _create_tables(conn)
    _migrate(conn)
    _migrate(conn)
    # Column names must be unique — duplicates would cause silent query bugs.
    for table in ("runs", "entries"):
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        assert len(cols) == len(set(cols)), (
            f"Duplicate column names found in {table}: {cols}"
        )
    conn.close()
