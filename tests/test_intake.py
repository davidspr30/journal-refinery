"""
test_intake.py

Tests for request assembly (app/intake.py).

assemble_request() is a pure function — it takes strings and returns a string.
No database, no API calls. Easy to test exhaustively.
"""

from app.intake import assemble_request

PROFILE  = "Clean up the transcript. Fix punctuation and remove filler words."
PACK     = "Context: Alice is David's partner. Bob is David's brother."
TRANSCRIPT = "um so yeah we uh went to the store and like bought some stuff"
SEPARATOR = "\n\n---\n\n"


# ---------------------------------------------------------------------------
# Order and structure
# ---------------------------------------------------------------------------

def test_profile_comes_before_pack():
    result = assemble_request(TRANSCRIPT, PACK, PROFILE, "")
    assert result.index(PROFILE.strip()) < result.index(PACK.strip())


def test_pack_comes_before_transcript():
    result = assemble_request(TRANSCRIPT, PACK, PROFILE, "")
    assert result.index(PACK.strip()) < result.index(TRANSCRIPT.strip())


def test_separator_between_sections():
    result = assemble_request(TRANSCRIPT, PACK, PROFILE, "")
    assert SEPARATOR in result


def test_three_separators_without_notes():
    # profile --- pack --- transcript  →  two separators
    result = assemble_request(TRANSCRIPT, PACK, PROFILE, "")
    assert result.count("---") == 2


# ---------------------------------------------------------------------------
# Notes handling
# ---------------------------------------------------------------------------

def test_notes_section_included_when_provided():
    notes = "I was exhausted that evening."
    result = assemble_request(TRANSCRIPT, PACK, PROFILE, notes)
    assert "Notes from the author:" in result
    assert notes in result


def test_notes_section_adds_a_third_separator():
    notes = "Important context."
    result = assemble_request(TRANSCRIPT, PACK, PROFILE, notes)
    assert result.count("---") == 3


def test_empty_notes_excluded():
    result = assemble_request(TRANSCRIPT, PACK, PROFILE, "")
    assert "Notes from the author:" not in result


def test_whitespace_only_notes_excluded():
    result = assemble_request(TRANSCRIPT, PACK, PROFILE, "   \n  ")
    assert "Notes from the author:" not in result


# ---------------------------------------------------------------------------
# Whitespace stripping
# ---------------------------------------------------------------------------

def test_leading_trailing_whitespace_stripped_from_inputs():
    padded_transcript = "\n\n  " + TRANSCRIPT + "  \n\n"
    result = assemble_request(padded_transcript, PACK, PROFILE, "")
    # The transcript content should be present, but not with extra whitespace
    # at the very start or end of the assembled string.
    assert not result.startswith("\n")
    assert not result.endswith("\n")
    assert TRANSCRIPT in result
