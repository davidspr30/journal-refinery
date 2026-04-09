"""
test_parser.py

Tests for Claude response parsing (app/parser.py).

parse_response() is a pure function. These tests check every variant of the
Ambiguities heading that Claude might produce, plus the no-ambiguities case.
"""

from app.parser import parse_response

POLISHED = "This was a great day. I went for a walk with Alice and we talked about the move."
AMBIGUITY_NOTE = "Unclear whether 'the move' refers to the office relocation or Alice moving houses."


# ---------------------------------------------------------------------------
# No ambiguities
# ---------------------------------------------------------------------------

def test_no_ambiguities_returns_full_text():
    polished, ambiguities = parse_response(POLISHED)
    assert polished == POLISHED.strip()
    assert ambiguities is None


def test_no_ambiguities_when_word_appears_in_body():
    # The word "ambiguities" in a sentence should NOT trigger a split.
    text = "There were no ambiguities in the conversation."
    polished, ambiguities = parse_response(text)
    assert polished == text.strip()
    assert ambiguities is None


# ---------------------------------------------------------------------------
# Heading variants
# ---------------------------------------------------------------------------

def test_plain_heading():
    raw = f"{POLISHED}\n\nAmbiguities\n{AMBIGUITY_NOTE}"
    polished, ambiguities = parse_response(raw)
    assert polished == POLISHED
    assert AMBIGUITY_NOTE in ambiguities


def test_heading_with_period():
    raw = f"{POLISHED}\n\nAmbiguities.\n{AMBIGUITY_NOTE}"
    polished, ambiguities = parse_response(raw)
    assert polished == POLISHED
    assert AMBIGUITY_NOTE in ambiguities


def test_bold_heading_with_period():
    raw = f"{POLISHED}\n**Ambiguities.**\n{AMBIGUITY_NOTE}"
    polished, ambiguities = parse_response(raw)
    assert polished == POLISHED
    assert AMBIGUITY_NOTE in ambiguities


def test_bold_heading_without_period():
    raw = f"{POLISHED}\n**Ambiguities**\n{AMBIGUITY_NOTE}"
    polished, ambiguities = parse_response(raw)
    assert polished == POLISHED
    assert AMBIGUITY_NOTE in ambiguities


def test_case_insensitive_heading():
    raw = f"{POLISHED}\n\nAMBIGUITIES\n{AMBIGUITY_NOTE}"
    polished, ambiguities = parse_response(raw)
    assert polished == POLISHED
    assert ambiguities is not None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_ambiguities_section_returns_none():
    # Heading present but nothing meaningful after it.
    raw = f"{POLISHED}\n\nAmbiguities\n   \n  "
    polished, ambiguities = parse_response(raw)
    assert polished == POLISHED
    assert ambiguities is None


def test_whitespace_stripped_from_both_parts():
    raw = f"  {POLISHED}  \n\nAmbiguities\n  {AMBIGUITY_NOTE}  "
    polished, ambiguities = parse_response(raw)
    assert polished == POLISHED          # leading/trailing spaces removed
    assert ambiguities == AMBIGUITY_NOTE  # same for ambiguities


def test_multiple_ambiguity_items():
    items = "- Item one.\n- Item two.\n- Item three."
    raw = f"{POLISHED}\n\nAmbiguities\n{items}"
    polished, ambiguities = parse_response(raw)
    assert polished == POLISHED
    assert "Item one" in ambiguities
    assert "Item three" in ambiguities
