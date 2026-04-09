"""
packs.py

Write operations and management helpers for Context Packs and Prompt Profiles.

Read-only helpers used by the intake form (get_context_pack, etc.) live in
intake.py — they are imported by main.py for both the form and the management
routes, so there is no need to duplicate them here.
"""

from datetime import datetime, timezone

from app.config import PROJECT_ROOT


# ---------------------------------------------------------------------------
# Seed file paths
# ---------------------------------------------------------------------------

SEED_PACK_PATH    = PROJECT_ROOT / "seed_files" / "correct names w context.md"
SEED_PROFILE_PATH = PROJECT_ROOT / "seed_files" / "transcript prompt.md"

SEED_PACK_NAME    = "correct names w context"
SEED_PROFILE_NAME = "transcript prompt"


# ---------------------------------------------------------------------------
# Context Pack operations
# ---------------------------------------------------------------------------

def get_all_packs(conn):
    """Return all context packs (full rows), ordered by name."""
    return conn.execute(
        "SELECT * FROM context_packs ORDER BY name"
    ).fetchall()


def get_default_pack_id(conn):
    """
    Return the id stored in settings as the default context pack, or None.
    The returned value is a string (SQLite stores it as text); convert to int
    before comparing with pack ids.
    """
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'default_context_pack_id'"
    ).fetchone()
    return int(row["value"]) if row else None


def set_default_pack(conn, pack_id):
    """Write (or overwrite) the default context pack in the settings table."""
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES ('default_context_pack_id', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(pack_id),),
    )
    conn.commit()


def create_pack(conn, name, content):
    """Insert a new context pack and return its id."""
    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO context_packs (name, content, version, created_at, updated_at)
        VALUES (?, ?, 1, ?, ?)
        """,
        (name.strip(), content.strip(), now, now),
    )
    conn.commit()
    return cursor.lastrowid


def update_pack(conn, pack_id, name, content):
    """
    Overwrite the name and content of an existing context pack and
    increment its version number by 1.
    """
    now = _now()
    conn.execute(
        """
        UPDATE context_packs
        SET name = ?, content = ?, version = version + 1, updated_at = ?
        WHERE id = ?
        """,
        (name.strip(), content.strip(), now, pack_id),
    )
    conn.commit()


def delete_pack(conn, pack_id):
    """
    Delete a context pack by id.

    Raises sqlite3.IntegrityError if the pack is referenced by existing runs
    or entries (foreign key constraint). The caller should catch this and
    show a user-friendly error rather than letting it propagate.
    """
    conn.execute("DELETE FROM context_packs WHERE id = ?", (pack_id,))
    conn.commit()


def duplicate_pack(conn, pack_id):
    """
    Create a copy of an existing context pack.

    The new record gets the same content, a name of '<original name> (copy)',
    and starts at version 1.  Returns the new pack's id, or None if the
    source pack was not found.
    """
    original = conn.execute(
        "SELECT * FROM context_packs WHERE id = ?", (pack_id,)
    ).fetchone()
    if original is None:
        return None

    return create_pack(conn, f"{original['name']} (copy)", original["content"])


def import_seed_pack(conn):
    """
    Read the seed context pack file and create a new DB record from it.

    Returns (new_id, None) on success, or (None, error_message) on failure.
    Re-importing is allowed — it always creates a fresh record.
    """
    try:
        content = SEED_PACK_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"Seed file not found: {SEED_PACK_PATH}"
    except OSError as exc:
        return None, f"Could not read seed file: {exc}"

    new_id = create_pack(conn, SEED_PACK_NAME, content)
    return new_id, None


# ---------------------------------------------------------------------------
# Prompt Profile operations
# ---------------------------------------------------------------------------

def get_all_profiles(conn):
    """Return all prompt profiles (full rows), ordered by name."""
    return conn.execute(
        "SELECT * FROM prompt_profiles ORDER BY name"
    ).fetchall()


def get_default_profile_id(conn):
    """
    Return the id stored in settings as the default prompt profile, or None.
    """
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'default_prompt_profile_id'"
    ).fetchone()
    return int(row["value"]) if row else None


def set_default_profile(conn, profile_id):
    """Write (or overwrite) the default prompt profile in the settings table."""
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES ('default_prompt_profile_id', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(profile_id),),
    )
    conn.commit()


def create_profile(conn, name, content):
    """Insert a new prompt profile and return its id."""
    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO prompt_profiles (name, content, version, created_at, updated_at)
        VALUES (?, ?, 1, ?, ?)
        """,
        (name.strip(), content.strip(), now, now),
    )
    conn.commit()
    return cursor.lastrowid


def update_profile(conn, profile_id, name, content):
    """
    Overwrite the name and content of an existing prompt profile and
    increment its version number by 1.
    """
    now = _now()
    conn.execute(
        """
        UPDATE prompt_profiles
        SET name = ?, content = ?, version = version + 1, updated_at = ?
        WHERE id = ?
        """,
        (name.strip(), content.strip(), now, profile_id),
    )
    conn.commit()


def delete_profile(conn, profile_id):
    """
    Delete a prompt profile by id.

    Raises sqlite3.IntegrityError if referenced by existing runs or entries.
    """
    conn.execute("DELETE FROM prompt_profiles WHERE id = ?", (profile_id,))
    conn.commit()


def duplicate_profile(conn, profile_id):
    """
    Create a copy of an existing prompt profile at version 1.
    Returns the new profile's id, or None if the source was not found.
    """
    original = conn.execute(
        "SELECT * FROM prompt_profiles WHERE id = ?", (profile_id,)
    ).fetchone()
    if original is None:
        return None

    return create_profile(conn, f"{original['name']} (copy)", original["content"])


def import_seed_profile(conn):
    """
    Read the seed prompt profile file and create a new DB record from it.

    Returns (new_id, None) on success, or (None, error_message) on failure.
    """
    try:
        content = SEED_PROFILE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"Seed file not found: {SEED_PROFILE_PATH}"
    except OSError as exc:
        return None, f"Could not read seed file: {exc}"

    new_id = create_profile(conn, SEED_PROFILE_NAME, content)
    return new_id, None


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _now():
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
