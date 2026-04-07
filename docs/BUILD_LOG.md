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
