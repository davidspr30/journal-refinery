# Journal Refinery — Build Log

---

## 2026-04-07 — Phase 0: Spec and Planning

**What happened:**
Created the four planning documents that define the product and implementation approach before any application code is written.

**Documents created:**
- `docs/PRODUCT_SPEC.md` — defines what the app is, what it is not, required screens, data objects, in-scope and out-of-scope features, and acceptance criteria for v1
- `docs/PHASE_PLAN.md` — breaks the build into five phases, each with a single clear goal
- `docs/TECH_DECISIONS.md` — records every significant tech choice and the reason for it
- `docs/BUILD_LOG.md` — this file

**Seed files reviewed:**
- `seed_files/correct names w context.md` — a detailed context reference listing names, relationships, common transcription errors, and disambiguation rules; will become the default Context Pack
- `seed_files/transcript prompt.md` — an editorial prompt describing the speaker's voice and the cleanup rules; will become the default Prompt Profile

**Assumptions made:**
1. The app is used by a single user on a single machine. No multi-user support is needed now or anticipated.
2. The Claude API call is synchronous for v1. The transcript and prompt are small enough that waiting a few seconds for a response is acceptable. Streaming can be added later if needed.
3. Entry dates are either supplied by the user or default to the run date. There is no attempt to parse a date out of the transcript.
4. "Version" on Context Packs and Prompt Profiles is a simple integer that increments on every save. It is stored on runs and entries for traceability, but there is no version history UI in v1.
5. Parsing the Ambiguities section from Claude's response relies on the heading `Ambiguities` appearing in the output, as described in the Prompt Profile. If the prompt is changed in a way that removes this heading, parsing will gracefully return no ambiguities rather than crashing.
6. The `.env` file approach is sufficient for API key management for a local single-user tool.
7. Markdown export produces a simple `.md` file with the polished text. No special front matter or metadata is added in v1.
8. File upload in v1 accepts `.txt` files only. Other formats (Word, PDF) are out of scope.

**Phase 0 status:** Complete.

**Next step:** Phase 1 — Project Skeleton.

---

## 2026-04-07 — Phase 1: Project Skeleton

**What happened:**
Scaffolded the full project structure and built a runnable FastAPI app shell with the complete SQLite schema.

**Files created:**

- `main.py` — FastAPI entry point; mounts static files, sets up Jinja2 templates, calls `init_db()` on startup, serves `GET /` and `GET /health`
- `app/__init__.py` — makes `app/` a Python package
- `app/config.py` — loads `.env` using `python-dotenv`; exposes `DATABASE_PATH` and `ANTHROPIC_API_KEY`
- `app/db.py` — `get_connection()` opens a named-column SQLite connection; `init_db()` creates all five tables with `CREATE TABLE IF NOT EXISTS`
- `templates/base.html` — base HTML template with site header, nav, main block, and footer
- `templates/index.html` — homepage extending base; placeholder notice until Phase 3 wires up the form
- `static/style.css` — minimal plain CSS; readable body font, container layout, header, nav, footer, subtitle and notice utility classes
- `requirements.txt` — six pinned dependencies (fastapi, uvicorn, jinja2, python-multipart, anthropic, python-dotenv)
- `.env.example` — documents the only required environment variable (`ANTHROPIC_API_KEY`)
- `.gitignore` — excludes `.env`, `data/*.db`, `__pycache__`, venvs, editor files
- `README.md` — rewritten with local setup instructions and project structure overview
- `data/.gitkeep`, `exports/.gitkeep`, `context_packs/.gitkeep`, `prompt_profiles/.gitkeep` — empty placeholder files to keep empty directories in git
- `tests/__init__.py` — makes `tests/` a Python package, ready for test files

**Schema created (five tables):**
- `context_packs` — id, name, content, version, created_at, updated_at
- `prompt_profiles` — id, name, content, version, created_at, updated_at
- `runs` — id, created_at, transcript_raw, context_pack_id, prompt_profile_id, version snapshots, output_polished, output_ambiguities, status
- `entries` — id, created_at, entry_date, run_id, transcript_raw, output_polished, output_ambiguities, context_pack_id, prompt_profile_id, version snapshots
- `settings` — key, value (for app-level config such as default selections)

**What was not done in this phase:**
- Seed files not yet ingested (Phase 2)
- No CRUD routes yet (Phase 2)
- No Claude API call (Phase 3)
- No archive logic (Phase 4)

**Assumptions made:**
1. `sqlite3.Row` row factory is used on every connection so columns are always accessible by name.
2. Foreign key enforcement is turned on via `PRAGMA foreign_keys = ON` per connection.
3. All datetime fields are stored as `TEXT` in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`). SQLite has no native datetime type; TEXT is the clearest and most portable choice.
4. The `settings` table is included now to avoid a schema migration later. It will store key/value pairs like the default context pack or prompt profile.
5. `context_packs/` and `prompt_profiles/` directories are created as empty folders for potential future file-based import workflows; they are not used by the app in v1.
6. The `anthropic` package is included in `requirements.txt` now so the Phase 3 developer environment is ready without a separate install step.

**Phase 1 status:** Complete.

**Next step:** Phase 2 — Context Packs and Prompt Profiles UI.
