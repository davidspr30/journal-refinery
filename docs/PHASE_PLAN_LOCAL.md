# Phase Plan — Local Provider Refactor

This plan covers the work required to move Journal Refinery from a hard
Anthropic dependency to a local provider architecture. Each phase has a single
clear goal and its own acceptance criteria. The full acceptance criteria are in
`docs/LOCAL_PROVIDER_REFACTOR_SPEC.md`; this file gives the sequence and the
key files touched per phase.

---

## Phase 0 — Architecture Documentation (this phase)

**Goal:** Describe the full architecture before writing any application code.

**Deliverables:**
- `docs/LOCAL_PROVIDER_REFACTOR_SPEC.md` — master spec
- `docs/PHASE_PLAN_LOCAL.md` — this file
- `docs/TECH_DECISIONS_LOCAL.md` — rationale for key choices
- `docs/BUILD_LOG.md` — updated with this planning entry

**Files touched:** `docs/` only. No application code changes.

**Done when:** All four docs exist and are internally consistent.

---

## Phase 1 — Database Schema

**Goal:** Add the two schema changes required by the new architecture without
breaking anything else.

**Work:**
1. Add `provider_configs` table in `_create_tables()`:
   ```sql
   CREATE TABLE IF NOT EXISTS provider_configs (
       id            INTEGER PRIMARY KEY,
       provider_type TEXT    NOT NULL UNIQUE,
       config_json   TEXT    NOT NULL DEFAULT '{}'
   );
   ```
2. Add `provider_type TEXT` column to `runs` table in `_migrate()`.
3. In `seed_defaults()` (`app/intake.py`), insert `active_provider_type =
   "manual_export"` into `settings` if the key is not already present.

**Files touched:**
- `app/db.py`
- `app/intake.py`

**Done when:**
- `provider_configs` table exists after `init_db()`.
- `runs.provider_type` column exists.
- `_migrate()` can be called twice without errors.
- All 52 existing tests pass unchanged.

---

## Phase 2 — Provider Abstraction and `manual_export`

**Goal:** Replace `app/claude_client.py` with the provider abstraction.
Wire the `/refine` route to call the active provider. Implement `manual_export`
as the default provider.

**Work:**
1. Create `app/providers/` package:
   - `app/providers/__init__.py` — `get_provider(conn)` factory that reads
     `active_provider_type` from `settings` and returns the right instance.
   - `app/providers/base.py` — `ProviderProtocol` definition.
   - `app/providers/manual_export.py` — `ManualExportProvider` class.
2. Update `main.py` `/refine` route:
   - Remove `asyncio.to_thread(call_claude, ...)`.
   - Call `provider = get_provider(conn)` then `await provider.refine_transcript(assembled)`.
   - Pass `provider_type=provider.provider_type` to `save_run()`.
   - Remove `ANTHROPIC_API_KEY` check at the top of the route.
3. Update `app/runs.py` — add `provider_type` parameter to `save_run()`.
4. Update `main.py` `GET /review/{run_id}` — pass `provider_type` to template.
5. Update `templates/review.html` — when `provider_type == "manual_export"`,
   show assembled-request copy-paste UI instead of polished output column.
6. Delete `app/claude_client.py`.
7. Remove `ANTHROPIC_API_KEY` import from `app/config.py`.

**Files touched:**
- `app/providers/__init__.py` (new)
- `app/providers/base.py` (new)
- `app/providers/manual_export.py` (new)
- `app/claude_client.py` (deleted)
- `app/config.py` (trimmed)
- `app/runs.py` (small addition)
- `main.py` (route changes)
- `templates/review.html` (conditional display)

**Done when:**
- App starts with no `ANTHROPIC_API_KEY` in `.env`.
- Refine flow works end-to-end with `manual_export` as the active provider.
- Review page shows assembled request text (not polished output) for
  `manual_export` runs.
- `call_claude` does not appear anywhere in the codebase.
- All 52 existing tests pass.

---

## Phase 3 — `llama_cpp_http` Provider and Health Check

**Goal:** Implement the local llama-server provider and expose a health check
endpoint so the UI can show whether llama-server is reachable.

**Work:**
1. Create `app/providers/llama_cpp_http.py`:
   - Reads `base_url` and `max_tokens` from `provider_configs`.
   - `refine_transcript()` — POST to `{base_url}/v1/chat/completions`.
   - `health_check()` — GET `{base_url}/health`.
   - All five error cases handled (ConnectError, TimeoutException, HTTPStatusError,
     non-JSON response, generic Exception).
2. Update `app/providers/__init__.py` `get_provider()` to return
   `LlamaCppHttpProvider` when `active_provider_type == "llama_cpp_http"`.
3. Add `GET /provider-health` route to `main.py`:
   ```python
   @app.get("/provider-health")
   async def provider_health(conn=Depends(get_db)):
       provider = get_provider(conn)
       ok, message = provider.health_check()
       return {"provider_type": provider.provider_type, "ok": ok, "message": message}
   ```
4. Add `httpx` to `requirements.txt`.

**Files touched:**
- `app/providers/llama_cpp_http.py` (new)
- `app/providers/__init__.py`
- `main.py`
- `requirements.txt`

**Done when:**
- With llama-server running: full refine → polished output in review page.
- With llama-server stopped: review page shows "Could not connect to llama-server" error.
- `GET /provider-health` returns correct JSON for both running and stopped states.
- `anthropic` is still in `requirements.txt` at this point (removal is Phase 5).

---

## Phase 4 — Provider Settings UI

**Goal:** Add a settings screen where the user can choose the active provider
and configure the `llama_cpp_http` connection details — without editing any
files.

**Work:**
1. Add `GET /settings` route — renders a settings form showing:
   - Radio buttons (or a `<select>`) to choose `manual_export` or `llama_cpp_http`.
   - `llama_cpp_http` config section (shown/hidden based on selection):
     - `base_url` text input (default: `http://localhost:8080`)
     - `max_tokens` number input (default: `2048`)
   - "Test connection" button that calls `GET /provider-health` and shows
     the result inline (either a small form POST + redirect, or a `<details>`
     showing the raw JSON).
2. Add `POST /settings` route — saves `active_provider_type` to `settings` table
   and `config_json` to `provider_configs` table for `llama_cpp_http`. Redirects
   back to `GET /settings` (303 See Other).
3. Add settings page to nav in `base.html`.
4. Create `templates/settings.html`.

**Files touched:**
- `main.py`
- `templates/settings.html` (new)
- `templates/base.html`
- `static/style.css` (form styles if needed)

**Done when:**
- User can switch between providers in the UI.
- `base_url` and `max_tokens` changes persist across app restarts.
- "Test connection" shows a clear pass/fail result.
- No file editing required to configure providers.

---

## Phase 5 — Remove Anthropic SDK

**Goal:** Delete every trace of the Anthropic dependency from the codebase.

**Work:**
1. Remove `anthropic==0.51.0` from `requirements.txt`.
2. Remove `ANTHROPIC_API_KEY` and `CLAUDE_MODEL` from `app/config.py` (if any
   remnant remains after Phase 2).
3. Remove `ANTHROPIC_API_KEY` from `.env.example`.
4. Search the entire codebase for `anthropic` and remove any remaining imports
   or references.
5. Update `README.md`:
   - Remove "An Anthropic API key" from Requirements.
   - Replace setup step 4 (API key) with instructions to configure a provider
     from the settings page.
   - Update troubleshooting section: remove Anthropic-specific entries; add
     llama-server setup guidance.
   - Update the "Can I use a different Claude model?" FAQ entry or remove it.
6. Delete `app/claude_client.py` if still present (should be gone from Phase 2).

**Files touched:**
- `requirements.txt`
- `app/config.py`
- `.env.example`
- `README.md`
- Any other file with an `anthropic` import

**Done when:**
- `grep -r "anthropic" .` (excluding `docs/`) returns no results.
- `pip install -r requirements.txt` does not install the Anthropic SDK.
- App starts with a completely empty `.env` file.
- All existing tests pass.

---

## Phase 6 — Tests

**Goal:** Add unit tests for the new provider code.

**Work:**
1. Create `tests/test_providers.py`:
   - `manual_export`: `refine_transcript()` returns `(assembled_text, None)`.
   - `manual_export`: `health_check()` returns `(True, ...)`.
   - `manual_export`: `validate_config()` returns `[]`.
   - `llama_cpp_http`: `refine_transcript()` success path — mock `httpx` to return
     a valid completion response.
   - `llama_cpp_http`: `ConnectError` → returns `(None, error_string)`.
   - `llama_cpp_http`: `TimeoutException` → returns `(None, error_string)`.
   - `llama_cpp_http`: `HTTPStatusError` (e.g. 500) → returns `(None, error_string)`.
   - `llama_cpp_http`: `validate_config()` with empty `base_url` → returns error list.
   - `llama_cpp_http`: `health_check()` when server is up vs. down.
2. Update `tests/test_db.py`:
   - `provider_configs` table exists after `init_db()`.
   - `runs` table has `provider_type` column.

**Files touched:**
- `tests/test_providers.py` (new)
- `tests/test_db.py` (additions)

**Done when:**
- Total test count exceeds 52.
- All tests pass.
- `llama_cpp_http` error branches are tested without a real llama-server.

---

## Phase order rationale

Phases 1 → 2 → 3 must be sequential: schema first, then the abstraction layer,
then the concrete HTTP provider. Phase 4 (UI) can be done in parallel with
Phase 3 or deferred until both providers work. Phase 5 (removal) must come
after both providers are proven working. Phase 6 (tests) can be done
incrementally throughout or as a final sweep.

---

## Files that do not change

These files are untouched by the entire refactor:

- `app/intake.py` — `assemble_request()` is provider-agnostic
- `app/parser.py` — `parse_response()` works on any text output
- `app/entries.py` — save/retrieve entries unchanged
- `app/packs.py` — context pack / prompt profile CRUD unchanged
- `templates/` (except `review.html`, `base.html`, new `settings.html`)
- `static/style.css` — minor additions only (settings page form)
- `tests/test_intake.py`, `tests/test_parser.py`, `tests/test_entries.py`,
  `tests/test_export.py` — all continue to pass unchanged
- `seed_files/` — read-only, not touched
- `data/.gitkeep` — unchanged
