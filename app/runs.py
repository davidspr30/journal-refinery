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
    response_raw,
    output_polished,
    output_ambiguities,
    status,
    model=None,
    provider_type=None,
    provider_name=None,
    provider_config_snapshot=None,
    error_message=None,
):
    """
    Insert a new run record and return its id.

    All fields are keyword-only to prevent positional mistakes.
    status must be 'complete', 'error', or 'manual_export'.
    model is kept for historical runs; new runs use provider_type/provider_name.
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
            error_message,
            provider_type,
            provider_name,
            provider_config_snapshot
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            provider_type,
            provider_name,
            provider_config_snapshot,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_run(conn, run_id):
    """Return a single run by id, or None if not found."""
    return conn.execute(
        "SELECT * FROM runs WHERE id = ?", (run_id,)
    ).fetchone()
