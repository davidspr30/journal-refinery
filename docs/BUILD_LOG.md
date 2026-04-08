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

---

## 2026-04-07 — Phase 2: Transcript Intake and Prompt Assembly Preview

**What happened:**
Built the transcript intake form on the homepage, added validation, seeded placeholder records on startup, and built a preview page that shows each component of the assembled request before any Claude call is made.

**Files created:**
- `app/intake.py` — DB helpers (`get_all_context_packs`, `get_all_prompt_profiles`, `get_context_pack`, `get_prompt_profile`), `seed_defaults()` to insert placeholder records on first startup, and `assemble_request()` to build the full prompt string
- `templates/preview.html` — shows the raw transcript, context pack, prompt profile, optional notes, and the assembled request (each in its own section); Back button; "Refine" placeholder for Phase 3

**Files modified:**
- `main.py` — lifespan now calls `seed_defaults()`; `GET /` passes pack and profile lists to the template; new `POST /preview` route handles validation, transcript resolution, assembly, and preview rendering
- `templates/index.html` — rewritten as the real intake form: transcript textarea, file upload (.txt/.md), two dropdowns, notes textarea, submit button; error banner; empty-state notice
- `static/style.css` — added form styles (label, hint, textarea, select, file input, two-column dropdown row, button), error banner, preview section cards, monospace text block, assembled request highlight

**Transcript precedence rule:**
If the user fills in the textarea AND uploads a file, the textarea wins. Reason: the textarea is the visible input. If there is text in the box, that is what the user intends to submit. A file upload alongside existing textarea content is almost certainly accidental. This rule is documented in the `POST /preview` docstring.

**Seed bootstrap:**
`seed_defaults()` checks whether `context_packs` and `prompt_profiles` each have zero rows. If so, it inserts one placeholder record for each. This runs every startup via the lifespan hook but only writes when the tables are empty. The actual seed files (`seed_files/`) are not ingested yet — that is planned for a later phase.

**Assembled request format:**
`assemble_request()` concatenates: prompt profile content → `---` separator → context pack content → `---` → transcript → `---` → notes (if provided). This matches the order described in TECH_DECISIONS.md and will be sent to Claude unchanged in Phase 3.

**Validation handled:**
- No transcript text and no file → error
- File provided with a disallowed extension → error (allowed: .txt, .md)
- Transcript text present (after stripping whitespace) is empty → error
- Context pack or prompt profile not found in DB → error
- On any error, the home form is re-rendered with the error message and the user's previous dropdown/notes selections preserved

**What was not done in this phase:**
- No Claude API call (Phase 3)
- No CRUD for Context Packs or Prompt Profiles (was originally Phase 2 in PHASE_PLAN, now deferred — the task asked for intake + preview only)
- No save/archive/export (Phase 4)

**Assumptions made:**
1. FastAPI's `UploadFile` sends an object with `filename == ""` when no file is selected. The check `transcript_file.filename != ""` is the reliable way to detect whether a real file was uploaded.
2. File content is decoded as UTF-8 with `errors="replace"` so non-UTF-8 bytes become replacement characters rather than raising an exception.
3. The textarea is not pre-populated on error (the user's typed transcript is lost if they hit an error). This is acceptable for a local single-user tool. The dropdown selections and notes field are preserved.
4. `assemble_request()` is a pure function — it takes strings and returns a string. It has no DB or API side effects, making it easy to test in isolation in Phase 3.

**Phase 2 status:** Complete.

**Next step:** Phase 3 — Claude API call and review page.

---

## 2026-04-07 — Phase 3: Claude Integration and Review Page

**What happened:**
Wired up the Anthropic API, built a response parser, stored runs in the database, and built the side-by-side review page. The full end-to-end flow now works: form → Claude → review.

**Files created:**
- `app/claude_client.py` — `call_claude(assembled_request)` → `(text, error)`. Uses the sync Anthropic SDK. Catches `AuthenticationError`, `RateLimitError`, `APIConnectionError`, `APIStatusError`, and the base `APIError` class. Returns `(None, human-readable message)` on any failure.
- `app/parser.py` — `parse_response(raw_text)` → `(polished, ambiguities_or_None)`. Regex splits on the Ambiguities heading in all common forms Claude might output. Returns `None` for ambiguities if none are found or if the section is blank after stripping.
- `app/runs.py` — `save_run(conn, ...)` inserts a run with all fields; `get_run(conn, run_id)` fetches one by id.
- `templates/review.html` — side-by-side two-column layout (raw transcript | polished output), metadata strip (model, context pack, prompt profile, timestamp), yellow ambiguities block, error state.

**Files modified:**
- `app/config.py` — added `CLAUDE_MODEL` (default: `claude-sonnet-4-6`) and `CLAUDE_MAX_TOKENS` (default: `4096`). Both overridable via `.env`.
- `app/db.py` — added `_migrate(conn)` called from `init_db()`. Checks `PRAGMA table_info(runs)` and adds any missing columns with `ALTER TABLE`. Handles: `model`, `assembled_request`, `response_raw`, `error_message`. Safe to run on any existing database.
- `app/intake.py` — extracted `resolve_transcript(transcript_text, transcript_file, allowed_extensions)` as a shared async helper. Eliminated duplicated validation logic between `/preview` and `/refine`. Also added `_file_extension()` helper.
- `main.py` — added `POST /refine` (validate → assemble → call Claude via `asyncio.to_thread` → save run → 303 redirect to `/review/{run_id}`) and `GET /review/{run_id}` (fetches run, pack, profile; renders review template). Updated `POST /preview` to use the shared `resolve_transcript` helper. Added all new imports.
- `templates/index.html` — form action changed from `/preview` to `/refine`; button text changed to "Refine with Claude →"; subtitle updated.
- `static/style.css` — added review page styles: `.review-header`, `.run-meta`, `.review-columns`, `.review-col`, `.review-text`, `.review-text.polished`, `.ambiguities-section`.
- `.env.example` — documented optional `CLAUDE_MODEL` and `CLAUDE_MAX_TOKENS` vars.

**How the Claude call works:**
The sync `call_claude()` function is called inside the `async def refine` route using `await asyncio.to_thread(call_claude, assembled)`. This runs the blocking SDK call in a thread pool so it doesn't block the event loop. The assembled request is a single user-role message sent to the Anthropic Messages API.

**How the ambiguities parser works:**
`parse_response()` applies a single regex: `\n{1,2}\*{0,2}Ambiguities\.?\*{0,2}\s*\n` (case-insensitive). This matches the word "Ambiguities" as a standalone line, with optional surrounding `**` bold markers and an optional trailing period. The text is split on the first match: everything before is the polished entry, everything after is the ambiguities text. If there is no match, the full response is treated as the polished entry and ambiguities is `None`. An empty ambiguities section after stripping also returns `None`.

**Error handling:**
- Missing API key: caught before the API call, returns home with an error banner.
- Any API failure: the run is saved with `status="error"` and the error message stored in `error_message`. The review page detects `status == 'error'` and shows the error instead of the two columns.
- 404: `GET /review/{id}` raises `HTTPException(404)` if the run id does not exist.

**What was not done in this phase:**
- No save-as-journal-entry (Phase 4).
- No archive page (Phase 4).
- No Markdown export (Phase 4).
- No CRUD for Context Packs or Prompt Profiles (deferred).

**Assumptions made:**
1. The sync Anthropic SDK client is instantiated inside `call_claude()` on every call rather than at module import time. This ensures the API key is always read from the current config state, and avoids any global client state.
2. `asyncio.to_thread` is used to run the blocking SDK call. For a single-user local tool this is fine. If streaming is added later, the async client (`anthropic.AsyncAnthropic`) would be the cleaner choice.
3. `max_tokens=4096` is enough for a typical journal entry with expansion. A very long transcript might approach or hit this limit. This is configurable via `CLAUDE_MAX_TOKENS` in `.env`.
4. The `303 See Other` redirect after `POST /refine` ensures that refreshing the review page does not re-submit the form.
5. Failed runs (status="error") are stored in the DB. The run ID appears in the review URL, which preserves it for debugging. The error_message is shown on the review page.

**Phase 3 status:** Complete.

**Next step:** Phase 4 — Save as journal entry, archive page, and Markdown export.

---

## 2026-04-08 — Phase 4: Save, Archive, and Markdown Export

**What happened:**
Added the ability to save a reviewed result as a permanent journal entry, browse all saved entries in an archive, view individual entries, and download any entry as a Markdown file.

**Files created:**
- `app/entries.py` — `save_entry()`, `get_entry()`, `get_entry_for_run()`, `get_all_entries()`. `save_entry()` auto-generates a `title` from the first ~100 characters of the polished output. Stores `context_pack_name` and `prompt_profile_name` at save time so export metadata is accurate even if a pack or profile is later renamed or deleted.
- `templates/archive.html` — lists all entries newest first; shows date, auto-generated title, pack/profile names; each row has View and Export .md buttons; includes an empty-state notice.
- `templates/entry.html` — entry detail page; polished text at full height (no max-height cap); ambiguities block if present; raw transcript in a native `<details>` collapsible element (no JavaScript needed); Export .md button; Back to Archive link.

**Files modified:**
- `app/db.py` — extended `_migrate()` to add four new columns to `entries`: `title`, `context_pack_name`, `prompt_profile_name`, `updated_at`. Migration is safe on existing databases.
- `main.py` — added four routes:
  - `POST /entries`: saves a run as an entry; redirects to detail on success; prevents duplicates by checking `get_entry_for_run()` first; returns 400 if run is not complete.
  - `GET /archive`: renders all entries newest first.
  - `GET /entries/{id}`: renders single entry detail.
  - `GET /entries/{id}/export`: builds and serves the Markdown file as a download.
  - Added `_build_markdown()` helper to construct the export content.
  - Updated `GET /review/{run_id}` to pass `today` (ISO date) and `existing_entry_id` to the template.
- `templates/review.html` — replaced "coming soon" with a real save form. Form shows a date input (pre-filled with today) and a hidden `run_id` field. If the run is already saved, shows a "View saved entry →" link instead of the form.
- `static/style.css` — added: `.save-form`, `.save-label`, `.save-date-input` (inline form on review page); `.archive-list`, `.archive-item`, `.archive-item-date`, `.archive-item-body`, `.archive-item-title`, `.archive-item-meta`, `.archive-item-actions`; `.entry-header`, `.entry-section`, `.entry-body`, `.transcript-details` (collapsible raw transcript).

**Export filename format:**
`YYYY-MM-DD-journal-entry.md` — exactly the format specified. If two entries share the same date, they produce the same filename; the user renames as needed. The entry id is intentionally omitted to keep filenames clean.

**Export Markdown structure:**
```
# Journal Entry — YYYY-MM-DD

**Date:** YYYY-MM-DD
**Context Pack:** Name (vN)
**Prompt Profile:** Name (vN)

---

[polished journal text]

---          ← only if ambiguities present
## Ambiguities
[ambiguities text]
```

**Duplicate-save guard:**
`POST /entries` checks for an existing entry with the same `run_id` before inserting. If found, it redirects to the existing entry (303). This prevents accidental double-saves on double-click or page refresh.

**What was not done in this phase:**
- No CRUD for Context Packs or Prompt Profiles (still deferred).
- No search, tags, or filtering on the archive.
- No entry editing after save.

**Assumptions made:**
1. Entries are immutable after save. The `updated_at` field is set at creation time and is not updated by any current route. It is there for future use.
2. `context_pack_name` and `prompt_profile_name` are stored at save time (denormalized). This means the exported Markdown always shows the name that was active when the entry was saved, even if the pack or profile is later renamed or deleted.
3. Auto-generated titles are derived from the first ~100 characters of `output_polished`. No manual title entry is needed. The truncation backs up to the last word boundary to avoid mid-word cuts.
4. The native HTML `<details>` / `<summary>` element is used for the collapsible raw transcript on the entry detail page. This requires no JavaScript and works in all modern browsers.
5. Export uses `media_type="text/plain; charset=utf-8"` with `Content-Disposition: attachment`. This reliably triggers a file download in all browsers regardless of `.md` file association settings.

**Phase 4 status:** Complete.

**Next step:** Phase 5 — Polish, hardening, CRUD for Context Packs and Prompt Profiles, seed file ingestion.
