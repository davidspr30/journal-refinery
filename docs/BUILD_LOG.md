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

---

## 2026-04-08 — Phase 5: Context Pack and Prompt Profile Management

**What happened:**
Added full CRUD management screens for Context Packs and Prompt Profiles — the
reusable building blocks that feed into every journal refinement run.

**New files:**
- `app/packs.py` — all write operations for both resource types:
  `create_pack / update_pack / delete_pack / duplicate_pack / get_all_packs /
  get_default_pack_id / set_default_pack / import_seed_pack` and the matching
  `*_profile` variants. Seed file paths are resolved via `PROJECT_ROOT` from
  `config.py`.
- `templates/context_packs.html` — list page: name, version badge, "default"
  pill, Edit / Duplicate / Set default / Delete actions, Import seed button.
- `templates/context_pack_form.html` — create and edit form (single template,
  `pack` variable is `None` for new, a row for edit). Shows version increment
  warning when editing.
- `templates/prompt_profiles.html` — same structure as context_packs.html for
  prompt profiles.
- `templates/prompt_profile_form.html` — same structure as context_pack_form.html
  for prompt profiles.

**Modified files:**
- `main.py` — added 18 new routes (9 per resource type):
  `GET /context-packs`, `GET /context-packs/new`, `POST /context-packs/new`,
  `GET /context-packs/{id}/edit`, `POST /context-packs/{id}/edit`,
  `POST /context-packs/{id}/duplicate`, `POST /context-packs/{id}/set-default`,
  `POST /context-packs/{id}/delete`, `POST /context-packs/import-seed`, and
  identical routes under `/prompt-profiles`. Also updated `GET /` to read
  `default_context_pack_id` and `default_prompt_profile_id` from the settings
  table and pass them to the home form so the dropdowns pre-select defaults.
- `static/style.css` — added `.mgmt-header`, `.mgmt-list`, `.mgmt-item`,
  `.mgmt-item-main`, `.mgmt-item-name`, `.mgmt-item-meta`, `.mgmt-item-actions`,
  `.badge`, `.badge-default`, `.btn-danger`.
- `app/intake.py` — updated `seed_defaults` docstring to remove the stale
  "later phase" note and point to the new management pages instead.

**How versioning works:**
- `update_pack` / `update_profile`: increments `version` in place with
  `version = version + 1` in the SQL UPDATE. The existing row is overwritten;
  there is no history stored. Entries that were saved under an earlier version
  retain a snapshot of the name and version number they used (stored in
  `context_pack_name`, `context_pack_version`, etc. on the entries table).
- `duplicate_pack` / `duplicate_profile`: creates a brand-new row at version 1
  with the name `"<original> (copy)"`. The original is untouched.

**How defaults work:**
- The `settings` table stores `default_context_pack_id` and
  `default_prompt_profile_id` as plain text key/value pairs.
- `set_default_pack` / `set_default_profile` use `INSERT ... ON CONFLICT DO
  UPDATE` (upsert) so there is always at most one row per key.
- `GET /` reads both defaults and passes them as `form["context_pack_id"]` and
  `form["prompt_profile_id"]`. The existing `{% if ... == pack['id'] %}selected
  {% endif %}` logic in `index.html` already handles this correctly.
- If the default points to a deleted pack (edge case), the dropdown simply shows
  nothing selected rather than erroring.

**How seed import works:**
- `import_seed_pack` reads `seed_files/correct names w context.md` and calls
  `create_pack`. `import_seed_profile` does the same for
  `seed_files/transcript prompt.md`.
- Re-importing always creates a fresh record — there is no deduplication check.
  The user can then set the imported record as the default and delete the old one
  if desired.
- If the seed file is missing, an error banner is shown on the list page.

**Delete safety:**
- SQLite's foreign key constraint prevents deleting a pack or profile that is
  referenced by a run or entry. The route catches `sqlite3.IntegrityError` and
  re-renders the list page with an explanatory error banner instead of 500ing.

**Jinja2 note:**
- A block (`{% block title %}`) cannot be defined inside a conditional
  (`{% if %}...{% else %}...{% endif %}`). The title block must be a single
  declaration with the conditional placed inside it:
  `{% block title %}{% if pack %}Edit...{% else %}New...{% endif %}{% endblock %}`.

**Assumptions made:**
1. No edit history is stored. Incrementing the version number in place is
   sufficient for the traceability requirement (entries record the version they
   used at save time).
2. "Import seed" always creates a new record. If the user wants to replace the
   existing seed-imported record, they delete the old one and re-import.
3. Delete confirmation uses the browser's native `confirm()` dialog (one line of
   inline `onsubmit` JS). This requires no additional JavaScript infrastructure
   and is acceptable for a local desktop app with a single user.
4. The "Set default" button is hidden for the item that is already the default,
   to avoid a confusing no-op click.
5. The management list pages show all records sorted by name. No pagination is
   needed for a personal journal tool.

**Phase 5 status:** Complete.

---

## 2026-04-09 — Phase 6: Usability Polish and Error Handling

**Goal:** Make the app feel solid for daily use without expanding scope.

**Bug fixes:**
- `POST /context-packs/new` and `POST /prompt-profiles/new` were missing
  `request: Request` as a route parameter. When the validation-error path
  re-rendered the form template, it passed `{"request": {}}` — a plain dict
  instead of a real Starlette `Request`. Once `base.html` began using
  `request.url.path` for active nav highlighting, this would have raised an
  `AttributeError`. Fixed by adding `request: Request` to both route signatures.
- `.btn-primary` lacked `display: inline-block`, so `<a class="btn-primary">`
  (used on management list pages for "New pack" / "New profile") rendered as an
  inline element where vertical padding collapsed. Added `display: inline-block`
  and `text-decoration: none` to make it work identically on both `<a>` and
  `<button>`.

**Navigation:**
- Added active-nav highlighting to `base.html`. Each `<a>` in `.site-nav` now
  gets `aria-current="page"` when the current path matches it:
  - `/` and `/review/…` → New Entry
  - `/archive` and `/entries/…` → Archive
  - `/context-packs/…` → Context Packs
  - `/prompt-profiles/…` → Prompt Profiles
  CSS rule `.site-nav a[aria-current="page"]` sets `color: #fff` and adds a
  blue underline.
- Added `{% block container_extra_class %}{% endblock %}` to `base.html`'s
  `<main>` tag so child templates can opt into a wider container.
- Added footer link back to the home page ("New entry") so there is always a
  path home regardless of scroll position.

**Review page:**
- Opted in to `.container.wide { max-width: 1100px }` via
  `{% block container_extra_class %}wide{% endblock %}`. This gives each
  column ~530 px of reading width instead of ~420 px.
- Added `required` to the date input (already enforced server-side, now also
  in the browser).
- "Ambiguities flagged by Claude" heading replaces the plain "Ambiguities"
  heading; a short explanatory sentence is added below it.
- Error state: added a "Common causes" hint below the error banner listing
  API key, network, and quota as the most likely culprits.
- Save row: added "Already saved." text before the "View saved entry" link so
  it is clear why the save form is absent.

**Home page:**
- Split the single empty-state notice into three cases: both missing, only
  context packs missing, only prompt profiles missing. Each case links directly
  to the relevant management page.
- The submit button is disabled (with a tooltip) when packs or profiles are
  missing, rather than allowing a form submission that would fail.
- Consolidated the file-upload hint: the precedence rule is now part of the
  textarea label hint rather than a separate paragraph.

**Archive page:**
- Added a `+ New entry` button in the page header (same pattern as management
  pages) so the user does not have to scroll to the nav.
- Subtitle now shows entry count: "3 entries, newest first" / "1 entry, newest
  first".
- Empty-state text is now a `.notice` box with a direct link to refine instead
  of a plain paragraph.
- `(no title)` placeholder text changed to `(untitled)` for consistency.

**Preview page:**
- Removed the stale "Refine with Claude — available in Phase 3" span. The
  preview route has been functional since Phase 3; the text was never updated.
- Subtitle now accurately describes the page as an inspection tool.

**CSS — responsive breakpoints:**
- Added `@media (max-width: 720px)` rules to stack `.review-columns` to a
  single column, stack `.form-row` dropdowns to full width, and allow
  `.mgmt-item` actions to wrap below the name on narrow screens.

**README:**
- Complete rewrite aimed at a first-time user:
  - Requirements section (Python 3.10+, API key, browser)
  - Numbered setup steps with inline explanation
  - "First use" section: walks through importing seed files, setting defaults,
    and running the full refine → review → save → export flow
  - "Day-to-day use" summary for returning users
  - Troubleshooting section covering the five most common error states
  - Updated project structure (removed the non-existent `exports/` entry,
    added all `app/` modules)
  - Updated phase table: all phases now show "Done"

**Assumptions made:**
1. Transcript text is not re-populated after a validation error. The textarea is
   blank on re-render. This is acceptable because: (a) file uploads cannot be
   re-populated at all by browsers, and (b) storing potentially large text in a
   hidden field or server-side session would add complexity for little gain.
2. Active nav does not attempt to highlight `/health` or `/preview` as unique
   sections; they fall under "New Entry" and no active state respectively.
   `/preview` falls under "New Entry" as it is part of the intake flow.
3. Flash messages after create/edit/delete are not implemented. The list-page
   redirect already shows the changed state; adding a flash mechanism would
   require session infrastructure that is out of scope.

**Phase 6 status:** Complete.

---

## 2026-04-09 — Phase 7: Tests, Cleanup, and Stable v1

**Goal:** Leave the project in a state a beginner can run, understand, and trust.

**Test suite added:**

Five test files covering the five meaningful logic units of the app.
All tests use an in-memory SQLite database — the real `data/journal.db` is
never touched during a test run. Total: **52 tests, all passing**.

| File | What is tested |
|------|---------------|
| `tests/test_db.py` | All five tables exist after init; required columns present in `runs` and `entries`; `_migrate()` is safe to call twice (no crash, no duplicate columns) |
| `tests/test_intake.py` | `assemble_request()` puts profile before pack before transcript; separators present; notes included/excluded correctly; whitespace stripped |
| `tests/test_parser.py` | No-ambiguities path; plain, bold, period, and case-insensitive heading variants; empty section → None; whitespace stripped from both parts; word "ambiguities" inside body does not trigger split |
| `tests/test_entries.py` | `_make_title()` truncation at word boundary, newline collapsing, 100-char edge case; save+retrieve round-trip; `get_entry_for_run`; `get_all_entries` order and empty-table case |
| `tests/test_export.py` | `_build_markdown()` heading, metadata, polished text, with/without ambiguities, ambiguities appear after polished text, ends with newline |

**Infrastructure:**

- `tests/conftest.py` — shared `db_conn` pytest fixture. Creates a fresh
  in-memory SQLite connection per test with FK enforcement enabled. The
  `db_conn` fixture is used by `test_db.py` indirectly (tests make their own
  connections there) and directly by `test_entries.py`.
- `pytest.ini` — sets `testpaths = tests` and `addopts = -v` so `python -m
  pytest` from the project root finds and names all tests without extra flags.
- `requirements.txt` — added `pytest>=8.0` so a single `pip install -r
  requirements.txt` gives a beginner everything needed to run both the app and
  the tests.

**README expanded:**

Added four new sections to the README:
1. **Running tests** — `python -m pytest`, with variants for quiet output and
   single-file runs.
2. **Where data is stored** — table listing every data location including the
   SQLite tables, exports (browser downloads folder, not disk), and seed files.
3. **How Context Packs work** — explanation of purpose, example content, the
   edit/version workflow, and how to manage packs in the UI.
4. **How Prompt Profiles work** — same structure; explains the Ambiguities
   section mechanism.

**What the tests do NOT cover (known limitations):**

1. **HTTP routes** — no integration tests for the FastAPI routes. End-to-end
   route testing (e.g., with `httpx` + `TestClient`) would require either a
   real database file or dependency injection to swap the DB connection. Not
   added to keep complexity low.
2. **Claude API call** — `call_claude()` is not tested because testing it
   requires a live API key and would make the suite slow and network-dependent.
   The error-handling branches (AuthenticationError, RateLimitError, etc.) are
   readable in `app/claude_client.py` but not unit-tested.
3. **Jinja2 template rendering** — templates are not rendered in tests. Visual
   regressions are caught manually.
4. **`packs.py` write operations** — CRUD for packs and profiles follows the
   same SQLite insert/update/delete pattern exercised in `test_entries.py`.
   Testing it separately would add tests without adding coverage of new logic.
5. **`resolve_transcript()` async helper** — async functions need `pytest-asyncio`
   or a manual event loop in tests. Skipped to avoid adding a dependency.

**Assumptions made:**

1. `pytest>=8.0` is a reasonable floor — it is widely available and the API
   used (fixtures, plain `assert`, file discovery) is stable across 8.x.
2. Tests import `_build_markdown` from `main.py`. Importing `main` creates the
   FastAPI app object and mounts static files, but does not start the server or
   touch the database. This is acceptable for unit tests.
3. `_make_title` and `_build_markdown` are tested as private functions
   (`_`-prefixed). The alternative — making them public — would change the
   module API just to satisfy a test convention; testing private helpers
   directly is simpler and appropriate here.

**Phase 7 status:** Complete. v1 is done.

---

## 2026-04-09 — Phase 8: Local Provider Refactor — Architecture Planning

**Goal:** Replace the hard Anthropic API dependency with a local provider
abstraction. Produce the full architecture documentation before writing any
application code.

**What prompted this phase:**
The v1 app requires a paid Anthropic API key and a live internet connection for
every transcript refinement. The user wants the app to work completely offline
with a local model via `llama-server` (llama.cpp's built-in HTTP server), plus
a manual export fallback when no local model is running.

**Deliverables (docs only — no app code):**

- `docs/LOCAL_PROVIDER_REFACTOR_SPEC.md` — full spec: what stays, what changes,
  provider interface definition, both provider implementations, settings storage
  design, migration strategy, acceptance criteria per phase, out-of-scope list.
- `docs/PHASE_PLAN_LOCAL.md` — six-phase implementation plan (Phase 0 = this
  planning phase; Phases 1–6 = implementation).
- `docs/TECH_DECISIONS_LOCAL.md` — ten technical decisions with alternatives
  considered and rationale.
- `docs/BUILD_LOG.md` — this entry.

**Key architecture decisions made:**

1. Provider interface uses `typing.Protocol` — no inheritance, structurally typed,
   type-checker verifiable.
2. `manual_export` provider returns the assembled request as-is. No AI involved.
   Used as the default provider so new installs work immediately.
3. `llama_cpp_http` provider calls a separately-running `llama-server` via
   `httpx.AsyncClient` using the OpenAI-compatible `/v1/chat/completions` endpoint.
4. Provider config stored in a new `provider_configs` SQLite table. Active
   provider selection stored in the existing `settings` table. Both editable
   via a settings UI page (Phase 4).
5. `httpx` is the only new dependency. No native extensions, no model downloads,
   no process supervision.
6. `assemble_request()` and `parse_response()` are completely unchanged — the
   abstraction sits between them.
7. The `(text, error)` return convention from `call_claude()` is preserved in
   `refine_transcript()` so the route changes are minimal.

**Implementation phases planned:**

| Phase | Goal |
|-------|------|
| 1 | DB schema: `provider_configs` table + `runs.provider_type` column |
| 2 | Provider abstraction + `manual_export`; delete `claude_client.py` |
| 3 | `llama_cpp_http` provider + `/provider-health` endpoint |
| 4 | Provider settings UI |
| 5 | Remove `anthropic` SDK entirely |
| 6 | Tests for all provider code |

**Files that will NOT change:**
`app/intake.py`, `app/parser.py`, `app/entries.py`, `app/packs.py`,
`tests/test_intake.py`, `tests/test_parser.py`, `tests/test_entries.py`,
`tests/test_export.py`, `seed_files/`.

**Phase 8 status:** Complete (planning only).

**Next step:** Phase 1 — Database schema changes.

---

## 2026-04-09 — Phase 9: Provider Abstraction and Manual Export

**Goal:** Remove Anthropic from the critical path. Introduce the provider
abstraction and wire up `manual_export` as the default provider.

**Files created:**

- `app/providers/__init__.py` — exports `get_provider()` and `list_provider_types()`
- `app/providers/base.py` — `ProviderProtocol` definition using `typing.Protocol`
- `app/providers/manual_export.py` — `ManualExportProvider` class
- `app/providers/registry.py` — `get_provider(conn)` factory and `list_provider_types()`
- `app/providers/exceptions.py` — `ProviderError`, `ProviderUnavailable`

**Files modified:**

- `app/db.py` — added `provider_configs` table to `_create_tables()`; added
  `provider_type`, `provider_name`, `provider_config_snapshot` columns to `runs`
  via `_migrate()`
- `app/runs.py` — added `provider_type`, `provider_name`, `provider_config_snapshot`
  kwargs to `save_run()`; made `model` optional (default `None`) for backward
  compatibility with historical runs
- `app/intake.py` — `seed_defaults()` now inserts `active_provider_type =
  "manual_export"` into `settings` on first startup
- `app/config.py` — removed `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`,
  `CLAUDE_MAX_TOKENS`; now only exposes `DATABASE_PATH`
- `main.py` — removed `import asyncio`, `import app.config as config`,
  `from app.claude_client import call_claude`; added `from app.providers import
  get_provider`; `/refine` route now calls `await provider.refine_transcript(assembled)`
  with a three-branch result handler (`error` / `manual_export` / AI-polished)
- `templates/review.html` — metadata strip shows `provider_name` (falls back to
  `model` for historical runs); added `manual_export` branch showing assembled
  request in a copy textarea; error banner is now provider-agnostic;
  ambiguities label updated
- `static/style.css` — added `.info-banner` and `textarea.assembled-export` rules
- `requirements.txt` — removed `anthropic==0.51.0`
- `.env.example` — removed Anthropic key variables; now documents only the
  optional `DATABASE_PATH` override
- `README.md` — removed API key requirement from requirements section and setup;
  updated first-use and day-to-day guides; updated troubleshooting; updated
  project structure tree

**Files deleted:**

- `app/claude_client.py` — replaced by `app/providers/` package

**Schema changes:**

| Table | Change |
|-------|--------|
| `provider_configs` | New table: `id`, `provider_type` (UNIQUE), `config_json` |
| `runs` | Three new nullable columns: `provider_type`, `provider_name`, `provider_config_snapshot` |
| `settings` | Seeded with `active_provider_type = "manual_export"` on startup |

All changes go through `_migrate()` — safe to run on an existing database.

**How `manual_export` works:**

`refine_transcript()` returns the assembled request text unchanged. The `/refine`
route detects `provider.provider_type == "manual_export"` and stores the assembled
text as `output_polished` without calling `parse_response()`. The review page
shows the assembled text in a read-only textarea for copying to any external AI
tool.

**Test results:** 52 / 52 passing. All existing tests pass unchanged.

**Phase 9 status:** Complete.

**Next step:** Phase 3 — `llama_cpp_http` provider and `/provider-health` endpoint.
