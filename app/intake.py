"""
intake.py

Helpers for the transcript intake flow:
- fetching context packs and prompt profiles for dropdowns
- seeding placeholder records on first startup
- assembling the full request that will later be sent to Claude
"""

from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_all_context_packs(conn):
    """Return all context packs, ordered by name."""
    return conn.execute(
        "SELECT id, name, version FROM context_packs ORDER BY name"
    ).fetchall()


def get_all_prompt_profiles(conn):
    """Return all prompt profiles, ordered by name."""
    return conn.execute(
        "SELECT id, name, version FROM prompt_profiles ORDER BY name"
    ).fetchall()


def get_context_pack(conn, pack_id):
    """Return a single context pack by id, or None if not found."""
    return conn.execute(
        "SELECT * FROM context_packs WHERE id = ?", (pack_id,)
    ).fetchone()


def get_prompt_profile(conn, profile_id):
    """Return a single prompt profile by id, or None if not found."""
    return conn.execute(
        "SELECT * FROM prompt_profiles WHERE id = ?", (profile_id,)
    ).fetchone()


# ---------------------------------------------------------------------------
# Seed defaults
# ---------------------------------------------------------------------------

def seed_defaults(conn):
    """
    Insert one placeholder Context Pack and one placeholder Prompt Profile
    if the tables are empty.

    This runs at startup so the dropdowns on the home screen always have
    at least one option. The user can edit or delete these at any time.

    The actual seed files (seed_files/) will be ingested in a later phase.
    """
    now = _now()

    pack_count = conn.execute("SELECT COUNT(*) FROM context_packs").fetchone()[0]
    if pack_count == 0:
        conn.execute(
            """
            INSERT INTO context_packs (name, content, version, created_at, updated_at)
            VALUES (?, ?, 1, ?, ?)
            """,
            (
                "Default Context Pack",
                "Add your context here — names, relationships, places, "
                "and any recurring references that help the editor understand your entries.",
                now,
                now,
            ),
        )

    profile_count = conn.execute("SELECT COUNT(*) FROM prompt_profiles").fetchone()[0]
    if profile_count == 0:
        conn.execute(
            """
            INSERT INTO prompt_profiles (name, content, version, created_at, updated_at)
            VALUES (?, ?, 1, ?, ?)
            """,
            (
                "Default Prompt Profile",
                "You are an editorial assistant. Clean up the transcript: "
                "remove filler words, fix punctuation, smooth out awkward phrasing, "
                "and preserve the speaker's voice. Return the polished text only. "
                "If anything was genuinely ambiguous, list it under a single heading: Ambiguities.",
                now,
                now,
            ),
        )

    conn.commit()


# ---------------------------------------------------------------------------
# Request assembly
# ---------------------------------------------------------------------------

def assemble_request(transcript, context_pack_content, prompt_profile_content, notes):
    """
    Build the full text that will be sent to Claude.

    Order: prompt profile (editorial instructions) → context pack (reference
    material) → transcript → notes (if provided).

    This function is pure — it takes strings and returns a string.
    It does not touch the database or make any API calls.
    """
    parts = [
        prompt_profile_content.strip(),
        "---",
        context_pack_content.strip(),
        "---",
        transcript.strip(),
    ]

    if notes and notes.strip():
        parts += ["---", "Notes from the author:", notes.strip()]

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now():
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
