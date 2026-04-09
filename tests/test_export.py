"""
test_export.py

Tests for Markdown export (_build_markdown in main.py).

_build_markdown() takes an entry (dict-like) and returns a Markdown string.
We pass plain Python dicts here — the function only uses [] access, which
dicts support just as well as sqlite3.Row objects.

No database, no API calls.
"""

from main import _build_markdown


# A minimal entry with no ambiguities.
ENTRY = {
    "entry_date": "2025-01-15",
    "context_pack_name": "My Context Pack",
    "context_pack_version": 2,
    "prompt_profile_name": "Editorial Style",
    "prompt_profile_version": 1,
    "output_polished": "This was a great day. I went for a walk with Alice.",
    "output_ambiguities": None,
}


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_starts_with_h1_heading():
    md = _build_markdown(ENTRY)
    assert md.startswith("# Journal Entry — 2025-01-15")


def test_ends_with_newline():
    md = _build_markdown(ENTRY)
    assert md.endswith("\n")


def test_contains_horizontal_rule():
    md = _build_markdown(ENTRY)
    assert "---" in md


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def test_date_in_metadata():
    md = _build_markdown(ENTRY)
    assert "**Date:** 2025-01-15" in md


def test_context_pack_with_version():
    md = _build_markdown(ENTRY)
    assert "**Context Pack:** My Context Pack (v2)" in md


def test_prompt_profile_with_version():
    md = _build_markdown(ENTRY)
    assert "**Prompt Profile:** Editorial Style (v1)" in md


# ---------------------------------------------------------------------------
# Polished text
# ---------------------------------------------------------------------------

def test_polished_text_included():
    md = _build_markdown(ENTRY)
    assert ENTRY["output_polished"] in md


# ---------------------------------------------------------------------------
# Ambiguities section
# ---------------------------------------------------------------------------

def test_no_ambiguities_section_when_none():
    md = _build_markdown(ENTRY)
    assert "## Ambiguities" not in md


def test_ambiguities_section_included_when_present():
    entry = dict(ENTRY)
    entry["output_ambiguities"] = "Unclear if 'Sarah' is Sarah Jones or Sarah Lee."
    md = _build_markdown(entry)
    assert "## Ambiguities" in md
    assert "Sarah Jones" in md


def test_ambiguities_section_after_polished_text():
    entry = dict(ENTRY)
    entry["output_ambiguities"] = "Some ambiguity."
    md = _build_markdown(entry)
    polished_pos = md.index(ENTRY["output_polished"])
    ambiguities_pos = md.index("## Ambiguities")
    assert polished_pos < ambiguities_pos


# ---------------------------------------------------------------------------
# Version combinations
# ---------------------------------------------------------------------------

def test_version_numbers_appear_correctly():
    entry = dict(ENTRY)
    entry["context_pack_version"] = 5
    entry["prompt_profile_version"] = 3
    md = _build_markdown(entry)
    assert "(v5)" in md
    assert "(v3)" in md
