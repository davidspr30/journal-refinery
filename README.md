# Journal Refinery

A local-first transcript refinery. Paste a raw voice-journal transcript, apply a context pack and prompt profile, send it to Claude, and get a polished journal entry back. Review, save, and export as Markdown.

Everything runs on your machine. Nothing is stored in the cloud.

---

## What it does

1. You paste or upload a raw transcript
2. You choose a Context Pack (names, relationships, recurring context)
3. You choose a Prompt Profile (editorial instructions for Claude)
4. You hit Refine — the app sends the assembled request to Claude
5. You review the polished entry side by side with the raw transcript
6. You save the result and export it as Markdown

---

## Local setup

### 1. Clone the repo

```bash
git clone https://github.com/davidspr30/journal-refinery.git
cd journal-refinery
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key

```bash
cp .env.example .env
```

Open `.env` and replace `your-api-key-here` with your Anthropic API key.
You can get one at https://console.anthropic.com/

### 5. Run the app

```bash
python main.py
```

Open http://localhost:8000 in your browser.

The database is created automatically at `data/journal.db` on first startup.

---

## Project structure

```
journal-refinery/
├── main.py               # App entry point
├── requirements.txt
├── .env.example          # Copy to .env and add your API key
├── app/
│   ├── config.py         # Loads settings from .env
│   └── db.py             # Database connection and schema
├── templates/            # Jinja2 HTML templates
├── static/               # CSS
├── data/                 # SQLite database (created at runtime)
├── exports/              # Markdown exports saved here
├── seed_files/           # Default context pack and prompt profile source files
├── docs/                 # Product spec, phase plan, tech decisions, build log
└── tests/
```

---

## Development status

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Spec and planning | Done |
| 1 | Project skeleton + DB schema | Done |
| 2 | Context Packs and Prompt Profiles UI | Upcoming |
| 3 | Home screen and Claude refinement | Upcoming |
| 4 | Save, archive, and export | Upcoming |
| 5 | Polish and hardening | Upcoming |
