# Journal Refinery

A local-first transcript polisher. Paste a raw voice-journal transcript, apply a Context Pack (names, relationships) and a Prompt Profile (editorial instructions), and Claude returns a clean journal entry. Review it side by side with the raw text, save what you accept, and export as Markdown.

Everything runs on your machine. The only data that leaves is the API request to Claude.

---

## Requirements

- Python 3.10 or newer
- An [Anthropic API key](https://console.anthropic.com/)
- A modern web browser

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/davidspr30/journal-refinery.git
cd journal-refinery
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Anthropic API key

```bash
cp .env.example .env
```

Open `.env` in any text editor and replace `your-api-key-here` with your real key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

You can get a key at [console.anthropic.com](https://console.anthropic.com/).

### 5. Start the app

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
5. Go to **New Entry**, paste a transcript, and click **Refine with Claude**.
6. On the review page, read the polished output side by side with the raw
   transcript, then click **Save entry**.
7. Your entry appears in the **Archive**. Click **Export .md** to download it.

---

## Using the app day-to-day

1. Open http://localhost:8000.
2. Paste or upload your transcript.
3. The saved defaults are pre-selected — change them if needed.
4. Click **Refine with Claude**. The app calls the Claude API and shows the
   result on the review page.
5. Review the polished text. If Claude flagged any ambiguities, they appear in
   a yellow block below the columns.
6. Pick a date (defaults to today) and click **Save entry**.
7. Done. The entry is in the archive.

---

## Troubleshooting

**"ANTHROPIC_API_KEY is not set"**
Your `.env` file is missing or the key is not set. Run `cp .env.example .env`
and add your key.

**"Claude returned an error"**
The review page shows the error message from Anthropic. Common causes:
- Invalid API key
- API rate limit reached (wait a minute and try again)
- Network error (check your connection)

**"Uploaded file must be .txt or .md"**
The app only accepts plain text files. Convert your file before uploading.

**"The uploaded file was empty"**
The file was blank. Paste the text directly into the textarea instead.

**Port 8000 is already in use**
Another process is using that port. Stop it, or start Journal Refinery on a
different port:
```bash
UVICORN_PORT=8001 python main.py
```
Then open http://localhost:8001.

**Can I use a different Claude model?**
Yes. Add this to your `.env`:
```
CLAUDE_MODEL=claude-opus-4-6
```

---

## Project structure

```
journal-refinery/
├── main.py               # App entry point — all routes live here
├── requirements.txt
├── .env.example          # Copy to .env and add your API key
├── app/
│   ├── config.py         # Loads settings from .env
│   ├── db.py             # Database connection and schema creation
│   ├── intake.py         # Form helpers, request assembly, seed defaults
│   ├── packs.py          # Context pack and prompt profile write operations
│   ├── runs.py           # Run storage helpers
│   ├── entries.py        # Entry storage helpers
│   ├── claude_client.py  # Anthropic API call
│   └── parser.py         # Splits Claude response into polished + ambiguities
├── templates/            # Jinja2 HTML templates
├── static/               # CSS (style.css)
├── data/                 # SQLite database — created at runtime
├── seed_files/           # Example context pack and prompt profile
└── docs/                 # Product spec, phase plan, tech decisions, build log
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
