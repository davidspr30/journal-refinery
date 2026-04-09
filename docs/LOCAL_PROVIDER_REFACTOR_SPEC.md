# Local Provider Refactor — Specification

## Why this refactor

Journal Refinery v1 hard-wires the Anthropic Claude API as the only path through
the `/refine` route. Every transcript refinement requires a paid cloud account,
a live internet connection, and a valid API key. This makes the app unusable
offline and couples it permanently to one vendor.

This refactor removes Anthropic from the critical path and introduces a **provider
abstraction** — a simple interface that any refinement backend can implement.
The first two concrete providers are:

1. `manual_export` — no AI involved; returns the assembled request so the user
   can copy it into any external tool.
2. `llama_cpp_http` — calls a locally running `llama-server` (llama.cpp's built-in
   HTTP API) over plain HTTP.

After this refactor the app works completely offline with no paid accounts or
cloud dependencies.

---

## What stays the same

| Component | Notes |
|-----------|-------|
| FastAPI + Jinja2 + SQLite stack | No changes to framework or storage layer |
| `assemble_request()` in `app/intake.py` | Pure function; provider-agnostic; unchanged |
| `parse_response()` in `app/parser.py` | Parses `Ambiguities` heading; unchanged |
| Archive, context packs, prompt profiles | Data model and UI fully intact |
| `save_run()` / `get_run()` in `app/runs.py` | Small addition only (see below) |
| All 52 existing tests | Must pass throughout every phase |
| `settings` table pattern | Extended slightly for active provider selection |

---

## What changes

### `app/claude_client.py` → removed / replaced

The entire file is deleted. Its role is taken over by the provider abstraction.
The `(text, error)` return convention from `call_claude()` is preserved in the
new `refine_transcript()` interface so callers change as little as possible.

### New `app/providers/` package

```
app/providers/
    __init__.py          # exports get_provider() factory
    base.py              # ProviderProtocol definition
    manual_export.py     # copy-paste fallback provider
    llama_cpp_http.py    # local llama-server provider
```

### `app/config.py`

Remove: `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `CLAUDE_MAX_TOKENS`.

After the refactor `config.py` has nothing Anthropic-specific. The `.env` file
still exists for the database path, but the API key variables are gone.

### `app/db.py`

Two schema additions via the existing `_migrate()` pattern:

1. New `provider_configs` table (stores per-provider settings as JSON).
2. New `provider_type TEXT` column on the `runs` table (records which provider
   produced each run).

### `main.py` — `/refine` route

The route currently does:
```python
result = await asyncio.to_thread(call_claude, assembled)
```

After the refactor it does:
```python
provider = get_provider(conn)
result = await provider.refine_transcript(assembled)
```

No `asyncio.to_thread` needed because the new providers are async-native
(`httpx.AsyncClient` for `llama_cpp_http`, immediate return for `manual_export`).

The `save_run()` call gains a `provider_type` argument.

### `requirements.txt`

```
# Remove:
anthropic==0.51.0

# Add:
httpx
```

### `.env.example`

Remove the `ANTHROPIC_API_KEY` and `CLAUDE_MODEL` lines. The file will only
document `DATABASE_PATH` (already optional / defaulted).

---

## Provider interface

Defined in `app/providers/base.py` using `typing.Protocol`.

```python
from typing import Protocol

class ProviderProtocol(Protocol):
    provider_type: str
    """Short machine-readable identifier, e.g. 'manual_export', 'llama_cpp_http'."""

    provider_name: str
    """Human-readable display name shown in the UI, e.g. 'Manual Export'."""

    def validate_config(self) -> list[str]:
        """
        Check that the provider's stored settings are valid.
        Return a list of human-readable error strings.
        Return an empty list if everything looks good.
        Does NOT make any network calls.
        """
        ...

    def health_check(self) -> tuple[bool, str]:
        """
        Test whether the provider is reachable and ready.
        Return (True, 'ready message') on success.
        Return (False, 'error message') on failure.
        For providers with no external dependency (manual_export), always return (True, 'ready').
        """
        ...

    async def refine_transcript(self, assembled: str) -> tuple[str | None, str | None]:
        """
        Run the transcript through the provider.
        Return (polished_text, None) on success.
        Return (None, error_string) on failure.
        Same convention as the old call_claude() function.
        """
        ...
```

### Why `typing.Protocol`

No inheritance is required. Any class that implements these three methods and
two attributes satisfies the protocol. This is checked by type-checkers (mypy,
pyright) and requires no base class boilerplate. See `docs/TECH_DECISIONS_LOCAL.md`.

---

## Provider 1: `manual_export`

**File:** `app/providers/manual_export.py`

**Behaviour:**
- `refine_transcript()` returns the assembled request text unchanged as the
  `text` value. No AI is called.
- The review page detects `provider_type == "manual_export"` and replaces the
  "polished output" column with a copy-paste textarea containing the full
  assembled request. The user then pastes it into any LLM of their choice and
  copies the result back into the app manually — or just reads it.
- `health_check()` always returns `(True, "ready")`.
- `validate_config()` always returns `[]`.

**Config:** None. No settings are stored for this provider.

**When to use:** No local model is running; user has no API key; debugging the
assembled request before sending it anywhere.

---

## Provider 2: `llama_cpp_http`

**File:** `app/providers/llama_cpp_http.py`

**Behaviour:**
- `refine_transcript()` sends the assembled request to a running `llama-server`
  instance using the OpenAI-compatible `/v1/chat/completions` endpoint.
- The request is a single user-role message (same pattern as the old Anthropic
  call).
- Uses `httpx.AsyncClient` — no `asyncio.to_thread` needed.
- `health_check()` sends a GET to `{base_url}/health` and returns
  `(True, "llama-server is running")` on HTTP 200, or `(False, error)` otherwise.
- `validate_config()` checks that `base_url` is set and non-empty.

**Config (stored in `provider_configs` table):**

| Key | Default | Description |
|-----|---------|-------------|
| `base_url` | `http://localhost:8080` | Base URL of the running llama-server |
| `max_tokens` | `2048` | `max_tokens` sent in the completion request |

**Error handling** (mirrors `claude_client.py`):

| Exception | Human-readable message |
|-----------|------------------------|
| `httpx.ConnectError` | "Could not connect to llama-server at {base_url}. Is it running?" |
| `httpx.TimeoutException` | "Request to llama-server timed out." |
| `httpx.HTTPStatusError` | "llama-server returned HTTP {status}: {body}" |
| `Exception` (catch-all) | "Unexpected error: {str(e)}" |

**What this provider does NOT do:**
- It does not start or restart llama-server.
- It does not download or manage models.
- It does not embed llama.cpp bindings into Python.
- It assumes llama-server is already running and reachable at `base_url`.

---

## Provider configuration storage

### `provider_configs` table

```sql
CREATE TABLE IF NOT EXISTS provider_configs (
    id            INTEGER PRIMARY KEY,
    provider_type TEXT    NOT NULL UNIQUE,
    config_json   TEXT    NOT NULL DEFAULT '{}'
);
```

Config values are stored as a JSON string keyed by field name:
```json
{"base_url": "http://localhost:8080", "max_tokens": 2048}
```

Reading config: `json.loads(row["config_json"])`.
Writing config: `json.dumps(config_dict)`.

The `manual_export` provider stores no config row — or an empty `{}` row.

### Active provider selection

Stored in the existing `settings` table as a key/value pair:

```
key   = "active_provider_type"
value = "llama_cpp_http"   (or "manual_export")
```

This follows the same pattern as `default_context_pack_id` and
`default_prompt_profile_id`. The `get_provider()` factory reads this setting
and returns the appropriate provider instance, populated with config from
`provider_configs`.

### `get_provider()` factory

```python
# app/providers/__init__.py

def get_provider(conn) -> ProviderProtocol:
    """
    Read the active_provider_type from settings and return the right provider.
    Falls back to manual_export if the setting is missing or unrecognised.
    """
    ...
```

---

## Database migration strategy

All schema changes go through the existing `_migrate()` function in `app/db.py`,
which checks `PRAGMA table_info()` before issuing any `ALTER TABLE`. This is
safe to run on an existing database — nothing is destroyed.

### Changes to `runs` table

Add `provider_type TEXT` column. Existing runs get `NULL` (which is fine —
they were Anthropic runs and can be labelled retroactively if desired, but
`NULL` is an honest representation).

### New `provider_configs` table

Created by `_create_tables()` with `CREATE TABLE IF NOT EXISTS`. Idempotent.

### Seed defaults

`seed_defaults()` in `app/intake.py` gains logic to insert a default
`active_provider_type = "manual_export"` setting row if none exists, so new
installs start with a working (if limited) provider immediately.

---

## Review page changes for `manual_export`

When `provider_type == "manual_export"` the polished output column shows a
`<textarea readonly>` containing the assembled request text, with a "Copy to
clipboard" button. The yellow Ambiguities block is not shown (there is none).

A banner at the top of the review page says:
> "Manual Export mode — copy the text below into your preferred AI tool, then
> paste the result back here to save it manually."

The save form still appears so the user can paste refined output into a future
edit flow (or save a note about the entry). This is a v1 affordance — a
dedicated paste-back UI can come in a later phase.

---

## `/health` and `/provider-health` endpoints

The existing `GET /health` route (returns `{"status": "ok"}`) is unchanged.

A new `GET /provider-health` route is added. It calls `provider.health_check()`
and returns:
```json
{"provider_type": "llama_cpp_http", "ok": true, "message": "llama-server is running"}
```

The provider settings UI calls this endpoint via a small `<form>` (or a plain
fetch) and displays the result inline.

---

## Acceptance criteria

### Phase 1 — DB schema (done when):
- `provider_configs` table exists after `init_db()`.
- `runs` table has a `provider_type` column.
- `_migrate()` is safe to run twice (no crash).
- All 52 existing tests still pass.

### Phase 2 — Provider abstraction + `manual_export` (done when):
- `app/providers/` package exists with `base.py`, `manual_export.py`, `__init__.py`.
- `app/claude_client.py` is deleted.
- The `/refine` route calls `provider.refine_transcript()` instead of `call_claude()`.
- The review page shows the assembled request text when provider is `manual_export`.
- `GET /` no longer checks for `ANTHROPIC_API_KEY`.
- All 52 existing tests still pass.
- Manual walkthrough: form → refine → review shows assembled text → save works.

### Phase 3 — `llama_cpp_http` provider (done when):
- `app/providers/llama_cpp_http.py` exists.
- With llama-server running locally: full refine → review → save flow produces
  a polished entry.
- With llama-server stopped: review page shows a clear error message.
- `GET /provider-health` returns the correct status JSON.
- Error cases (connect error, timeout, bad status) return human-readable messages.

### Phase 4 — Provider settings UI (done when):
- A settings page lets the user switch between `manual_export` and `llama_cpp_http`.
- The `llama_cpp_http` settings form shows `base_url` and `max_tokens` fields.
- Saving the form persists to `provider_configs`.
- A "Test connection" button calls `/provider-health` and shows the result.

### Phase 5 — Remove Anthropic (done when):
- `anthropic` does not appear in `requirements.txt`.
- `anthropic` does not appear in any import in the codebase.
- `ANTHROPIC_API_KEY` does not appear in `.env.example`.
- `pip install -r requirements.txt` does not install the Anthropic SDK.
- The app starts and runs a full refine with no API key configured.

### Phase 6 — Tests (done when):
- `tests/test_providers.py` exists.
- `manual_export` provider: `refine_transcript` returns the assembled text.
- `llama_cpp_http` provider: all error-handling branches are tested with
  `httpx` mocked.
- `validate_config()` and `health_check()` have unit tests.
- Total test count is higher than 52 and all pass.

---

## Out of scope (this refactor)

The following are explicitly **not** in scope for this refactor and must not
be implemented even if they seem convenient:

| Item | Reason deferred |
|------|----------------|
| Paid API providers (Anthropic, OpenAI, etc.) | Defeats the purpose of the refactor |
| Automatic model downloads | Too complex for v1; requires managing disk space and file integrity |
| Embedded llama.cpp Python bindings (`llama-cpp-python`) | Heavy native dependency; harder to install than `httpx` |
| Starting or supervising `llama-server` as a subprocess | Process management adds significant complexity and error surface |
| Streaming responses from llama-server | Adds UI complexity; not needed for journal-length text |
| Whisper.cpp audio transcription | Separate feature; planned for a later phase |
| Multi-provider routing or fallback chains | YAGNI; manual fallback is sufficient for v1 |
| Model selection UI | Out of scope for v1; model is configured via llama-server startup flags |
