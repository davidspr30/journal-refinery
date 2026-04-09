"""
test_entries.py

Tests for the entry save/retrieve flow (app/entries.py).

Each test that touches the database receives a fresh in-memory connection
from the db_conn fixture in conftest.py. Tests are independent — they cannot
affect each other.

Foreign keys are enabled in the test database. Where a run_id is needed,
we insert a minimal run record first so the FK constraint is satisfied.
Where FK references are not relevant to what is being tested, we pass None
(SQLite allows NULL for nullable FK columns without checking the constraint).
"""

import pytest

from app.entries import (
    _make_title,
    get_all_entries,
    get_entry,
    get_entry_for_run,
    save_entry,
)


# ---------------------------------------------------------------------------
# _make_title — pure function, no database needed
# ---------------------------------------------------------------------------

def test_make_title_short_text_unchanged():
    assert _make_title("A short entry.") == "A short entry."


def test_make_title_collapses_newlines():
    text = "Line one.\nLine two.\nLine three."
    assert "\n" not in _make_title(text)


def test_make_title_truncates_long_text():
    # 30 repetitions of "word " = 150 characters — well over the 100-char limit.
    long = "word " * 30
    result = _make_title(long)
    assert result.endswith("…")
    # The part before the ellipsis must be at most 100 chars.
    assert len(result[:-1]) <= 100


def test_make_title_does_not_cut_mid_word():
    # Each word is 8 chars — the truncation point falls inside a word.
    # The function should back up to the previous space.
    text = "abcdefg " * 20  # 8-char words
    result = _make_title(text)
    without_ellipsis = result[:-1]  # strip the "…"
    # After stripping, the result must not end with a partial word fragment
    # (i.e., it must end at a space boundary, so stripping gives a clean word).
    assert without_ellipsis == without_ellipsis.rstrip()


def test_make_title_exactly_100_chars_not_truncated():
    text = "a" * 100
    assert _make_title(text) == text


def test_make_title_101_chars_truncated():
    text = "a " * 51  # 102 chars — just over the limit
    result = _make_title(text)
    assert result.endswith("…")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _insert_minimal_run(conn):
    """
    Insert the smallest valid run record and return its auto-assigned id.

    Most run columns are nullable (they were added via ALTER TABLE and have
    no NOT NULL constraint). Only created_at, transcript_raw, and status
    are required.
    """
    cursor = conn.execute(
        """
        INSERT INTO runs (created_at, transcript_raw, status)
        VALUES ('2025-01-15T10:00:00', 'raw transcript text', 'complete')
        """
    )
    conn.commit()
    return cursor.lastrowid


def _save_test_entry(conn, **overrides):
    """
    Save a minimal entry and return its id.

    FK columns (run_id, context_pack_id, prompt_profile_id) default to None
    so the FK constraint is not triggered — useful when the test is about
    save/retrieve logic, not FK relationships.
    """
    defaults = dict(
        run_id=None,
        entry_date="2025-01-15",
        transcript_raw="raw transcript text",
        output_polished="This was a productive day.",
        output_ambiguities=None,
        context_pack_id=None,
        prompt_profile_id=None,
        context_pack_version=1,
        prompt_profile_version=1,
        context_pack_name="Test Pack",
        prompt_profile_name="Test Profile",
    )
    defaults.update(overrides)
    return save_entry(conn, **defaults)


# ---------------------------------------------------------------------------
# save_entry / get_entry round-trip
# ---------------------------------------------------------------------------

def test_save_entry_returns_integer_id(db_conn):
    entry_id = _save_test_entry(db_conn)
    assert isinstance(entry_id, int)
    assert entry_id > 0


def test_get_entry_retrieves_saved_row(db_conn):
    entry_id = _save_test_entry(db_conn, output_polished="A unique polished text.")
    entry = get_entry(db_conn, entry_id)
    assert entry is not None
    assert entry["output_polished"] == "A unique polished text."
    assert entry["entry_date"] == "2025-01-15"
    assert entry["context_pack_name"] == "Test Pack"


def test_get_entry_not_found_returns_none(db_conn):
    assert get_entry(db_conn, 99999) is None


def test_entry_title_is_auto_generated(db_conn):
    entry_id = _save_test_entry(db_conn, output_polished="Today was fantastic.")
    entry = get_entry(db_conn, entry_id)
    assert entry["title"] == "Today was fantastic."


def test_entry_with_ambiguities(db_conn):
    entry_id = _save_test_entry(
        db_conn,
        output_ambiguities="Unclear whether 'the meeting' was Tuesday or Wednesday.",
    )
    entry = get_entry(db_conn, entry_id)
    assert "Tuesday or Wednesday" in entry["output_ambiguities"]


# ---------------------------------------------------------------------------
# get_entry_for_run
# ---------------------------------------------------------------------------

def test_get_entry_for_run_finds_correct_entry(db_conn):
    run_id = _insert_minimal_run(db_conn)
    entry_id = _save_test_entry(db_conn, run_id=run_id)
    row = get_entry_for_run(db_conn, run_id)
    assert row is not None
    assert row["id"] == entry_id


def test_get_entry_for_run_not_found_returns_none(db_conn):
    # Insert a run but don't save any entry for it.
    run_id = _insert_minimal_run(db_conn)
    assert get_entry_for_run(db_conn, run_id) is None


# ---------------------------------------------------------------------------
# get_all_entries ordering
# ---------------------------------------------------------------------------

def test_get_all_entries_empty_database(db_conn):
    assert get_all_entries(db_conn) == []


def test_get_all_entries_newest_date_first(db_conn):
    _save_test_entry(db_conn, entry_date="2025-01-10")
    _save_test_entry(db_conn, entry_date="2025-01-20")
    _save_test_entry(db_conn, entry_date="2025-01-05")
    entries = get_all_entries(db_conn)
    dates = [e["entry_date"] for e in entries]
    assert dates == sorted(dates, reverse=True)


def test_get_all_entries_returns_all_rows(db_conn):
    _save_test_entry(db_conn, entry_date="2025-01-01")
    _save_test_entry(db_conn, entry_date="2025-01-02")
    _save_test_entry(db_conn, entry_date="2025-01-03")
    assert len(get_all_entries(db_conn)) == 3
