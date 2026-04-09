"""
parser.py

Parses Claude's response into the polished journal entry and an optional
Ambiguities section.

The Prompt Profile instructs Claude to collect any genuine ambiguities
at the very bottom under a single heading: "Ambiguities."
If nothing was ambiguous, Claude omits the section entirely.

Example of a response with ambiguities:

    This was a long and productive day. Sara and I talked about the
    move and decided to push it back a week...

    **Ambiguities.**
    - Unclear whether "the meeting Tuesday" refers to the church elder
      meeting or the MC gathering.

Usage:
    from app.parser import parse_response

    polished, ambiguities = parse_response(raw_text)
    # ambiguities is None if Claude found nothing ambiguous
"""

import re

# Matches the Ambiguities heading as a standalone line.
# Handles all common forms Claude might use:
#   Ambiguities
#   Ambiguities.
#   **Ambiguities.**
#   **Ambiguities**
#
# The pattern requires at least one blank line before the heading so we
# don't accidentally split on the word "Ambiguities" inside a paragraph.
_AMBIGUITIES_HEADING = re.compile(
    r"\n{1,2}\*{0,2}Ambiguities\.?\*{0,2}\s*\n",
    re.IGNORECASE,
)


def parse_response(raw_text):
    """
    Split Claude's response into (polished, ambiguities).

    Looks for the Ambiguities heading and splits there.
    Everything before the heading is the polished journal entry.
    Everything after is the ambiguities text.

    Returns:
        (polished_text, ambiguities_text)  — when the heading is found
        (full_text, None)                  — when no heading is found
    """
    parts = _AMBIGUITIES_HEADING.split(raw_text, maxsplit=1)

    if len(parts) == 2:
        polished = parts[0].strip()
        ambiguities = parts[1].strip()
        # If the ambiguities section ended up empty after stripping, ignore it.
        if not ambiguities:
            return polished, None
        return polished, ambiguities

    return raw_text.strip(), None
