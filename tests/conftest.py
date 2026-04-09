"""
conftest.py

Shared pytest fixtures for the Journal Refinery test suite.

The db_conn fixture gives each test its own isolated in-memory SQLite database
with the full app schema applied. Tests that write to the database do not
affect each other, and no data is written to the real data/journal.db file.
"""

import sqlite3
import pytest

from app.db import _create_tables, _migrate


@pytest.fixture
def db_conn():
    """
    Yield a fresh in-memory SQLite connection with the full app schema.

    Foreign key enforcement is enabled, matching production behaviour.
    The connection is closed automatically when the test finishes.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _create_tables(conn)
    _migrate(conn)
    conn.commit()
    yield conn
    conn.close()
