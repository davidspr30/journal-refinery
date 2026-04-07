"""
config.py

Loads settings from the .env file at the project root.
All other modules import from here rather than reading os.environ directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Find the project root (one level up from this file) and load .env from there.
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# The path where the SQLite database file will be stored.
DATABASE_PATH = PROJECT_ROOT / "data" / "journal.db"

# The Anthropic API key. Will be None if not set — the app checks for this
# before making any API calls.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# The Claude model to use for refinement.
# Override in .env if you want to use a different model.
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

# Maximum tokens Claude is allowed to return.
# 4096 is enough for a typical journal entry with room to expand.
CLAUDE_MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "4096"))
