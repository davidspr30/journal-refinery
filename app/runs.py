"""
runs.py

Database helpers for the runs table.

A run is created every time the user hits Refine — it records the full
input (transcript, assembled request), what Claude returned, and the
outcome (complete or error).
"""

from datetime import datetime, timezone


def save_run(
    conn,
    *,
    transcript_raw,
    context_pack_id,
    prompt_profile_id,
    context_pack_version,
    prompt_profile_version,
    assembled_request,
    model,
    response_raw,
    output_polished,
    output_ambiguities,
    status,
    error_message=None,
):
    """
    Insert a new run record and return its id.

    All fields are keyword-only to prevent positional mistakes.
    status must be 'complete' or 'error'.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    cursor = conn.execute(
        """
        INSERT INTO runs (
            created_at,
            transcript_raw,
            context_pack_id,
            prompt_profile_id,
            context_pack_version,
            prompt_profile_version,
            assembled_request,
            model,
            response_raw,
            output_polished,
            output_ambiguities,
            status,
            error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now,
            transcript_raw,
            context_pack_id,
            prompt_profile_id,
            context_pack_version,
            prompt_profile_version,
            assembled_request,
            model,
            response_raw,
            output_polished,
            output_ambiguities,
            status,
            error_message,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_run(conn, run_id):
    """Return a single run by id, or None if not found."""
    return conn.execute(
        "SELECT * FROM runs WHERE id = ?", (run_id,)
    ).fetchone()
