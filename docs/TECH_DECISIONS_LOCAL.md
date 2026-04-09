# Technical Decisions — Local Provider Refactor

Each entry records the decision made, the alternatives that were considered, and
why this option was chosen. Decisions are numbered for easy cross-reference.

---

## TD-L1: HTTP client — `httpx` over `requests` or `urllib`

**Decision:** Use `httpx` for all HTTP calls to the local llama-server.

**Alternatives considered:**

| Option | Notes |
|--------|-------|
| `requests` | Synchronous only; requires `asyncio.to_thread` inside an async route (same pattern as the old Anthropic SDK call — exactly what we want to avoid) |
| `urllib` (stdlib) | Verbose; no keep-alive connection pooling; no async support |
| `aiohttp` | Async-native but heavier; `httpx` has a cleaner API and is already a transitive dependency of FastAPI's testing utilities |
| `httpx` ✓ | Async-native with `httpx.AsyncClient`; simple API; compatible with FastAPI's async routes without a thread pool |

**Why it matters:** The `/refine` route is `async def`. Using `httpx.AsyncClient`
means `await client.post(...)` runs natively in the event loop without blocking.
No `asyncio.to_thread` needed, and no thread pool overhead.

---

## TD-L2: Provider configuration storage — SQLite over `.env`

**Decision:** Store provider configuration (base URL, max tokens) in the
`provider_configs` table in SQLite. Store the active provider selection in the
existing `settings` table.

**Alternatives considered:**

| Option | Notes |
|--------|-------|
| `.env` file | Requires a text editor to change; needs app restart to re-read; no UI possible without file I/O from the server |
| In-memory config at startup | Lost on restart; can't persist user changes |
| A separate JSON config file | Another file format to manage; doesn't fit the existing all-in-SQLite approach |
| SQLite (`settings` + `provider_configs`) ✓ | Editable through a UI form; persists across restarts; consistent with how defaults (context pack, prompt profile) are already stored |

**Why it matters:** A beginner user should be able to change the llama-server
URL without opening a terminal. Storing it in the database enables a settings
page with a regular web form.

---

## TD-L3: Provider abstraction style — `typing.Protocol` over ABC

**Decision:** Define `ProviderProtocol` using `typing.Protocol` (structural
subtyping), not `abc.ABC` (nominal subtyping).

**Alternatives considered:**

| Option | Notes |
|--------|-------|
| `abc.ABC` with `@abstractmethod` | Requires providers to explicitly inherit from the base class; couples the implementation to the abstraction |
| Duck typing (no protocol at all) | Works at runtime but provides no type-checker support; hard for a beginner to understand what a provider must implement |
| `typing.Protocol` ✓ | No inheritance required; any class with the right attributes and methods satisfies it; type-checker (mypy/pyright) verifiable; idiomatic modern Python (3.8+) |
| `dataclasses.dataclass` with ABC | Adds mutable state management to what should be a behaviour interface |

**Why it matters:** With `Protocol`, adding a third provider later requires zero
changes to the base class or any existing provider. Each provider is a standalone
module with no imported dependencies on the others.

---

## TD-L4: llama-server API format — OpenAI-compatible endpoint

**Decision:** Call `POST /v1/chat/completions` on llama-server using the
OpenAI-compatible JSON format.

**Alternatives considered:**

| Option | Notes |
|--------|-------|
| llama-server native `/completion` endpoint | Slightly simpler JSON, but non-standard; would require a custom adapter if another server is used |
| `/v1/chat/completions` (OpenAI-compatible) ✓ | llama.cpp ships this endpoint by default; widely documented; same format used by many other local model servers (Ollama, LM Studio, etc.) |

**Request body used:**
```json
{
  "messages": [{"role": "user", "content": "<assembled_request>"}],
  "max_tokens": 2048
}
```

**Why it matters:** Using the OpenAI-compatible format means the same provider
implementation works with any server that speaks OpenAI's API — not just
llama.cpp. Users who prefer Ollama or LM Studio can point the `base_url` at
those instead, with no code changes.

---

## TD-L5: Active provider stored in `settings` table

**Decision:** Store `active_provider_type` as a key/value row in the existing
`settings` table, not as a new column or dedicated table.

**Alternatives considered:**

| Option | Notes |
|--------|-------|
| New `active_provider` column on an existing table | No natural home; feels forced |
| Dedicated `active_provider` table | Overkill for one value |
| `settings` table, key = `"active_provider_type"` ✓ | Matches the existing pattern for `default_context_pack_id` and `default_prompt_profile_id`; no schema additions needed |

**Why it matters:** Consistency. Anyone reading the code already knows the
`settings` table is used for app-wide defaults. Finding the active provider
there is unsurprising.

---

## TD-L6: `manual_export` as a real provider (not a special case)

**Decision:** Implement `manual_export` as a fully conforming `ProviderProtocol`
implementation rather than a conditional branch in the route.

**Alternatives considered:**

| Option | Notes |
|--------|-------|
| `if active_provider == "manual_export": ...` branch in the route | Works but adds provider-specific logic into the route handler; harder to extend |
| `ManualExportProvider` implementing `ProviderProtocol` ✓ | The route calls `refine_transcript()` identically regardless of provider; the review template handles the display difference based on `provider_type` |

**Why it matters:** The route does not need to know about the details of any
provider. `manual_export` returning the assembled text as `(text, None)` is a
clean, honest implementation of `refine_transcript` — the "refinement" is a
no-op that hands the text back to the user.

---

## TD-L7: No embedded llama.cpp Python bindings

**Decision:** Do not use `llama-cpp-python` or any Python package that compiles
llama.cpp native code.

**Alternatives considered:**

| Option | Notes |
|--------|-------|
| `llama-cpp-python` | Requires a C++ compiler toolchain at install time; binary wheel availability varies by platform and Python version; dramatically harder for a beginner to install |
| `llama-server` over HTTP ✓ | User starts llama-server separately; the Python app just makes HTTP calls; no compilation required; `httpx` is the only new dependency |

**Why it matters:** The app is described as beginner-friendly. Adding a native
extension dependency would break `pip install -r requirements.txt` on many
systems and introduce a confusing installation troubleshooting path. The HTTP
approach keeps the Python environment simple.

---

## TD-L8: No process supervision of `llama-server`

**Decision:** The app does not start, stop, monitor, or restart `llama-server`.
The user is responsible for running it separately.

**Alternatives considered:**

| Option | Notes |
|--------|-------|
| `subprocess.Popen` to start llama-server | Requires knowing the model path; managing the process lifecycle; handling crashes and restarts; platform differences (Windows vs Mac vs Linux) |
| `asyncio.create_subprocess_exec` | Same issues; async complexity added |
| User runs llama-server separately ✓ | Simple; user has full control over model choice, context size, and startup flags; the app only needs to know the URL |

**Why it matters:** Process supervision is a hard problem. For v1, a clear
error message ("Could not connect to llama-server — is it running?") is far
simpler and more reliable than attempting to manage an external process.

---

## TD-L9: Keep `parse_response()` unchanged

**Decision:** `app/parser.py` is not modified. Local models are expected to
follow the same `Ambiguities` heading convention as the existing Prompt Profile
instructs Claude to use.

**Rationale:** The parser looks for a specific heading in the model's output. If
the local model follows the Prompt Profile (which instructs it to use an
`Ambiguities` heading), the parser works without changes. If the local model
produces no Ambiguities section, `parse_response()` returns `None` for
ambiguities — which is fine.

The Prompt Profile already says "list ambiguities under a heading called
Ambiguities". No local-model-specific prompting changes are needed.

---

## TD-L10: `httpx` timeout default

**Decision:** Set a 60-second timeout on `httpx` requests to llama-server.

**Rationale:** Local model inference on CPU can be slow (30–90 seconds for a
medium-length transcript on an average machine). A 60-second timeout is long
enough for most hardware but short enough to avoid hanging indefinitely if the
server crashes mid-generation. This is configurable as a named constant in
`llama_cpp_http.py`, not a magic number.

---

## Summary table

| # | Decision | Choice |
|---|----------|--------|
| TD-L1 | HTTP client | `httpx` |
| TD-L2 | Provider config storage | SQLite (`settings` + `provider_configs`) |
| TD-L3 | Provider abstraction style | `typing.Protocol` |
| TD-L4 | llama-server API format | OpenAI-compatible `/v1/chat/completions` |
| TD-L5 | Active provider setting | `settings` table key/value |
| TD-L6 | `manual_export` implementation | Full `ProviderProtocol` implementation |
| TD-L7 | llama.cpp embedding | Rejected — HTTP only |
| TD-L8 | Process supervision | Rejected — user runs llama-server separately |
| TD-L9 | Response parser | Keep `parse_response()` unchanged |
| TD-L10 | Request timeout | 60 seconds (named constant) |
