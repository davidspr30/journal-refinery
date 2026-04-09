# Journal Refinery

A local-first transcript polisher. Paste a raw voice-journal transcript, apply a Context Pack (names, relationships) and a Prompt Profile (editorial instructions), and your chosen AI provider returns a clean journal entry. Review it side by side with the raw text, save what you accept, and export as Markdown.

Everything runs on your machine. No API key required to get started.

---

## Requirements

- **Python 3.11 or 3.12** (recommended — Python 3.14 has known SSL issues on macOS)
  - Mac: `brew install python@3.12` (see setup step 2)
  - Windows: download from [python.org](https://www.python.org/downloads/)
- A modern web browser

No API key is required. The app ships with **Manual Export** mode as the default
provider — it assembles the full request and shows it in a textarea for you to
copy into any AI tool. To use a local model instead, run a `llama-server` instance
and configure it from the settings page (a future phase).

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/davidspr30/journal-refinery.git
cd journal-refinery
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: py -m venv .venv  &&  .venv\Scripts\activate
```

> **macOS note:** use `python3`, not `python`. If `python3` is missing or very
> new (3.14+), install a stable version first:
> ```bash
> brew install python@3.12
> python3.12 -m venv .venv
> source .venv/bin/activate
> ```
> If `brew` is not found, install Homebrew from [brew.sh](https://brew.sh).

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, uvicorn, Jinja2, and pytest for running tests.

### 4. Start the app

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

The database is created automatically at `data/journal.db` on first startup.
Two placeholder records (a default Context Pack and Prompt Profile) are inserted
so the home form has something to select right away.

---

## First use

The app ships with real example files in `seed_files/`. Here is how to load them:

1. Go to **Context Packs** in the nav and click **Import seed pack from file**.
   This loads `seed_files/correct names w context.md` as a new pack.
2. Click **Set default** next to it so the home form selects it automatically.
3. Go to **Prompt Profiles** and click **Import seed profile from file**.
   This loads `seed_files/transcript prompt.md` as a new profile.
4. Click **Set default** next to it.
5. Go to **New Entry**, paste a transcript, and click **Refine**.
6. On the review page, the assembled request is shown for copying (Manual Export
   mode). Copy it into your AI tool, get a polished result, and come back.
7. Your entry appears in the **Archive**. Click **Export .md** to download it.

---

## Using the app day-to-day

1. Open http://localhost:8000.
2. Paste or upload your transcript (`.txt` or `.md` files accepted).
3. The saved defaults are pre-selected — change them if needed.
4. Click **Refine**. The app assembles the full prompt and sends it to the
   active provider.
5. In Manual Export mode: copy the assembled request from the textarea and
   paste it into your AI tool. In llama_cpp_http mode: the polished text
   appears directly.
6. Pick a date (defaults to today) and click **Save entry**.
7. Done. The entry is in the archive.

---

## Running tests

```bash
python -m pytest
```

The test suite runs 52 tests in under a second. All tests use an in-memory
SQLite database — nothing is written to `data/journal.db`.

To run a specific file:

```bash
python -m pytest tests/test_parser.py
```

To run quietly (dots instead of names):

```bash
python -m pytest -q
```

---

## Where data is stored

| What | Where |
|------|-------|
| SQLite database | `data/journal.db` |
| Context Packs | `context_packs` table in `data/journal.db` |
| Prompt Profiles | `prompt_profiles` table in `data/journal.db` |
| Runs (API calls) | `runs` table in `data/journal.db` |
| Saved entries | `entries` table in `data/journal.db` |
| App defaults | `settings` table in `data/journal.db` |
| Markdown exports | Downloaded to your browser's downloads folder (not stored on disk) |
| Seed files | `seed_files/` directory — read-only, not modified by the app |

To back up your data, copy `data/journal.db` somewhere safe.

To start over, delete `data/journal.db`. The app will recreate it with placeholder
records on next startup.

---

## How Context Packs work

A Context Pack is a text file the app sends to Claude alongside every transcript.
It contains background information Claude needs to understand your entries — names,
relationships, recurring places, common transcription errors, and anything else
that would otherwise require explanation in every entry.

**Example content:**

```
Alice = David's partner.
Bob = David's brother, lives in Portland.
"the house" usually means the new house in Maplewood, not the old apartment.
Transcription error: "Siri" is often "Sara" (my daughter).
```

**Managing Context Packs:**

- Go to **Context Packs** in the nav to see your packs.
- Click **+ New pack** to write one from scratch.
- Click **Import seed pack from file** to load the built-in example.
- Click **Edit** to change an existing pack. Each edit increments the version
  number — old entries still record which version they used.
- Click **Duplicate** to copy a pack before experimenting with changes.
- Click **Set default** to pre-select a pack on the home form.

**Versioning:** Every time you save an edit, the version number goes up by one
(v1 → v2 → v3). The version used for each entry is stored permanently, so you
always know exactly what context Claude had when it produced a given entry.

---

## How Prompt Profiles work

A Prompt Profile contains the editorial instructions that tell Claude how to
refine your transcript — voice, style, cleanup rules, how to handle filler words,
and what to do with genuine ambiguities.

**Example content:**

```
You are an editorial assistant cleaning up a voice journal transcript.

Rules:
- Remove filler words (um, uh, like, you know, sort of).
- Fix punctuation and sentence boundaries.
- Preserve the speaker's first-person voice — do not rewrite ideas, only clean up delivery.
- If a name or reference is genuinely unclear, list it at the bottom under a heading: Ambiguities.
```

**The Ambiguities section:** If Claude is uncertain about something in the
transcript, it adds an "Ambiguities" heading at the end of its response. The
app detects this and displays it in a yellow block on the review page, separately
from the polished entry. You decide what (if anything) to do with it before saving.

**Managing Prompt Profiles:** Same workflow as Context Packs — create, edit,
duplicate, set default, import seed.

---

## Troubleshooting

**"The provider returned an error"**
The review page shows the full error message. This usually means the active
provider could not complete the request (e.g. llama-server is not running).
Check your provider settings and try again.

**"Uploaded file must be .txt or .md"**
The app only accepts plain text files. Convert your file before uploading.

**"The uploaded file was empty"**
The file was blank. Paste the text directly into the textarea instead.

**Port 8000 is already in use**
Another process is using that port. Stop it, or start on a different port:

```bash
uvicorn main:app --port 8001 --reload
```

Then open http://localhost:8001.

**"ssl module not available" / pip install fails with SSL errors**
This usually means your Python installation doesn't have OpenSSL linked — common
with Python 3.14 or a python.org installer on macOS where certificates weren't set up.

Fix: install a stable Python via Homebrew and recreate the venv:

```bash
brew install python@3.12
deactivate                          # exit the broken venv if active
rm -rf .venv                        # delete it
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `brew` is not found, install Homebrew from [brew.sh](https://brew.sh).

---

## Project structure

```
journal-refinery/
├── main.py                  # App entry point — all routes live here
├── requirements.txt
├── pytest.ini               # pytest configuration
├── .env.example             # Copy to .env to override defaults
├── app/
│   ├── config.py            # Loads settings from .env
│   ├── db.py                # Database connection and schema creation
│   ├── intake.py            # Form helpers, request assembly, seed defaults
│   ├── packs.py             # Context Pack and Prompt Profile write operations
│   ├── runs.py              # Run storage helpers
│   ├── entries.py           # Entry storage helpers
│   ├── parser.py            # Splits provider response into polished + ambiguities
│   └── providers/           # Provider abstraction
│       ├── __init__.py      # Exports get_provider()
│       ├── base.py          # ProviderProtocol definition
│       ├── registry.py      # Provider registry and factory
│       ├── manual_export.py # Copy-paste fallback (default provider)
│       └── exceptions.py    # Provider error types
├── templates/               # Jinja2 HTML templates
├── static/                  # style.css
├── data/                    # SQLite database — created at runtime
├── seed_files/              # Example context pack and prompt profile
├── tests/                   # pytest test suite
│   ├── conftest.py          # Shared db_conn fixture (in-memory SQLite)
│   ├── test_db.py           # Schema creation and migration
│   ├── test_intake.py       # Request assembly
│   ├── test_parser.py       # Claude response parsing
│   ├── test_entries.py      # Entry save/retrieve and title generation
│   └── test_export.py       # Markdown export structure
└── docs/                    # Product spec, phase plan, tech decisions, build log
```

---

## Development status

All phases are complete.

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Spec and planning | Done |
| 1 | Project skeleton + DB schema | Done |
| 2 | Transcript intake form and preview | Done |
| 3 | Claude API integration and review page | Done |
| 4 | Save, archive, and Markdown export | Done |
| 5 | Context Pack and Prompt Profile management screens | Done |
| 6 | Usability polish and error handling | Done |
| 7 | Tests, cleanup, and stable v1 | Done |
