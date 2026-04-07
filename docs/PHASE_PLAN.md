# Journal Refinery — Phase Plan

Each phase has one clear goal. A phase is complete when its goal is met and the app still runs.

---

## Phase 0 — Spec and Planning (current)

**Goal:** Agree on what we are building before writing a line of application code.

Deliverables:
- `docs/PRODUCT_SPEC.md`
- `docs/PHASE_PLAN.md`
- `docs/TECH_DECISIONS.md`
- `docs/BUILD_LOG.md`

No application code is written in this phase.

---

## Phase 1 — Project Skeleton

**Goal:** A runnable FastAPI app with the database schema created and the two seed files loaded as default records.

Work:
- Create the directory structure (`app/`, `templates/`, `static/`, `data/`)
- Create `main.py` entry point
- Create `db.py` — connect to SQLite, run `CREATE TABLE IF NOT EXISTS` for all four tables (`runs`, `entries`, `context_packs`, `prompt_profiles`)
- Write a seed script (or startup hook) that inserts the default Context Pack from `seed_files/correct names w context.md` and the default Prompt Profile from `seed_files/transcript prompt.md` if no records exist yet
- Confirm the app starts cleanly and the database file is created

No UI, no Claude call yet.

---

## Phase 2 — Context Packs and Prompt Profiles UI

**Goal:** A user can view, create, edit, and delete Context Packs and Prompt Profiles through the browser.

Work:
- Route: `GET /context-packs` — list all
- Route: `GET /context-packs/new` — create form
- Route: `POST /context-packs/new` — save new record, increment version on edit
- Route: `GET /context-packs/{id}/edit` — edit form pre-filled
- Route: `POST /context-packs/{id}/edit` — save changes
- Route: `POST /context-packs/{id}/delete` — delete record
- Same six routes for Prompt Profiles
- Simple Jinja2 templates for each screen
- Navigation header linking all major sections

No Claude call yet.

---

## Phase 3 — Home Screen and Refinement

**Goal:** A user can paste or upload a transcript, choose a Context Pack and Prompt Profile, click Refine, and see the Claude response.

Work:
- Route: `GET /` — home screen with textarea, file upload, and two dropdowns (context pack, prompt profile)
- Route: `POST /refine` — assemble the full prompt (context pack content + prompt profile content + transcript), call the Claude API, store the result as a `run` record, redirect to the review page
- Handle Claude API key from `.env`
- Parse Claude's response to split polished text from the Ambiguities section (if present)
- Route: `GET /review/{run_id}` — show raw transcript and polished output side by side; show Ambiguities block if present; show Save button

---

## Phase 4 — Save, Archive, and Export

**Goal:** A user can save an accepted entry and browse or export saved entries.

Work:
- Route: `POST /entries` — save a run as an Entry record (copy relevant fields, store version snapshots)
- Route: `GET /archive` — list all entries, newest first, with date and a short preview of the polished text
- Route: `GET /entries/{id}` — single entry detail view (raw + polished + ambiguities)
- Route: `GET /entries/{id}/export` — generate and serve a `.md` file download

---

## Phase 5 — Polish and Hardening

**Goal:** The app is clean enough for daily use.

Work:
- Error handling: Claude API failures, empty transcript submission, missing API key
- Basic input validation (transcript cannot be blank, a context pack and prompt profile must be selected)
- Sensible page titles and minimal navigation
- Confirmation prompt before deleting a Context Pack or Prompt Profile
- Verify the seed data loads correctly on a fresh install
- Manual end-to-end walkthrough: paste transcript → refine → review → save → archive → export

---

## What Is Not Planned

- Voice recording
- Cloud sync or auth
- Search, tags, or categories
- Any frontend JavaScript framework
- Mobile layout
- PDF export
