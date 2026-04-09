"""
entries.py

Database helpers for the entries table.

An entry is a saved, accepted journal result. It is created explicitly
by the user from the review page after they decide the polished output
is good enough to keep. Unlike a run (which is a raw API record), an
entry is the permanent record the user actually cares about.
"""

from datetime import datetime, timezone


def save_entry(
    conn,
    *,
    run_id,
    entry_date,
    transcript_raw,
    output_polished,
    output_ambiguities,
    context_pack_id,
    prompt_profile_id,
    context_pack_version,
    prompt_profile_version,
    context_pack_name,
    prompt_profile_name,
):
    """
    Insert a new entry record and return its id.

    title is auto-generated from the first 100 characters of output_polished
    so the archive list always has something readable to show.

    context_pack_name and prompt_profile_name are stored here at save time
    so the export is accurate even if the pack or profile is later renamed
    or deleted.

    All fields are keyword-only to prevent positional mistakes.
    """
    now = _now()
    title = _make_title(output_polished)

    cursor = conn.execute(
        """
        INSERT INTO entries (
            created_at,
            updated_at,
            entry_date,
            run_id,
            title,
            transcript_raw,
            output_polished,
            output_ambiguities,
            context_pack_id,
            prompt_profile_id,
            context_pack_version,
            prompt_profile_version,
            context_pack_name,
            prompt_profile_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now,
            now,
            entry_date,
            run_id,
            title,
            transcript_raw,
            output_polished,
            output_ambiguities,
            context_pack_id,
            prompt_profile_id,
            context_pack_version,
            prompt_profile_version,
            context_pack_name,
            prompt_profile_name,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_entry(conn, entry_id):
    """Return a single entry by id, or None if not found."""
    return conn.execute(
        "SELECT * FROM entries WHERE id = ?", (entry_id,)
    ).fetchone()


def get_entry_for_run(conn, run_id):
    """
    Return the entry saved from a specific run, or None.

    Used on the review page to detect whether a run has already been
    saved so we can show a 'View saved entry' link instead of the form.
    """
    return conn.execute(
        "SELECT id FROM entries WHERE run_id = ?", (run_id,)
    ).fetchone()


def get_all_entries(conn):
    """
    Return all entries, newest first.

    Ordered by entry_date descending, then created_at descending so
    entries on the same date come out in the order they were saved.
    """
    return conn.execute(
        """
        SELECT * FROM entries
        ORDER BY entry_date DESC, created_at DESC
        """
    ).fetchall()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_title(polished_text):
    """
    Generate a short title from the first sentence or ~100 characters
    of the polished output. Collapses newlines to spaces.
    """
    # Flatten whitespace to a single space for a clean one-liner title.
    flat = " ".join(polished_text.split())

    if len(flat) <= 100:
        return flat

    # Truncate at 100 chars, then back up to the last space so we don't
    # cut a word in half. Append an ellipsis.
    truncated = flat[:100]
    last_space = truncated.rfind(" ")
    if last_space > 60:
        truncated = truncated[:last_space]
    return truncated + "…"


def _now():
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
