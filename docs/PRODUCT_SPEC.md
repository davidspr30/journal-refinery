# Journal Refinery — Product Spec (v1)

## What It Is

Journal Refinery is a local-first desktop web app. You paste or upload a raw voice-journal transcript, select a Context Pack and a Prompt Profile, hit Refine, and Claude returns a polished journal entry. You review it side by side with the raw transcript, save what you accept, and export it as Markdown.

That is the whole product.

---

## What It Is Not

- Not a general journaling platform
- Not a second-brain or PKM app
- Not a note-taking suite
- Not a transcription app (v1 assumes you already have a transcript)
- Not a cloud app (no accounts, no sync, no remote storage)
- Not an AI agent platform
- Not a mobile app

---

## Success Criteria for v1

A v1 release is complete when a user can:

1. Paste or upload a raw transcript
2. Select a Context Pack and a Prompt Profile from saved options
3. Send the assembled request to Claude and receive a polished entry
4. Review the raw and polished text side by side
5. See any Ambiguities returned by Claude in a dedicated section
6. Save the accepted result locally
7. Browse saved entries in an archive
8. Export any saved entry as a Markdown file
9. Create, edit, and delete Context Packs
10. Create, edit, and delete Prompt Profiles

---

## Required Screens

| Screen | Purpose |
|--------|---------|
| Home / New Entry | Paste or upload transcript, choose Context Pack and Prompt Profile, trigger refinement |
| Review | Side-by-side view of raw transcript and polished output; Ambiguities section if present; Save button |
| Archive | List of all saved entries with date, title/preview, and export button |
| Entry Detail | View a single saved entry (raw + polished) |
| Context Packs | List, create, edit, delete context packs |
| Prompt Profiles | List, create, edit, delete prompt profiles |

---

## Required Data Objects

### Run
A single refinement attempt. Created when the user hits Refine.

| Field | Type | Notes |
|-------|------|-------|
| id | integer | primary key |
| created_at | datetime | UTC |
| transcript_raw | text | the original input |
| context_pack_id | integer | FK to context_packs |
| prompt_profile_id | integer | FK to prompt_profiles |
| context_pack_version | integer | snapshot of version at time of run |
| prompt_profile_version | integer | snapshot of version at time of run |
| output_polished | text | Claude's returned journal text |
| output_ambiguities | text | Claude's returned ambiguities (nullable) |
| status | text | `pending`, `complete`, `error` |

### Entry
A saved, accepted result. Created when the user saves from the Review screen.

| Field | Type | Notes |
|-------|------|-------|
| id | integer | primary key |
| created_at | datetime | UTC |
| entry_date | date | the journal date (user-supplied or inferred) |
| run_id | integer | FK to runs |
| transcript_raw | text | copied from run |
| output_polished | text | copied from run |
| output_ambiguities | text | nullable |
| context_pack_id | integer | reference |
| prompt_profile_id | integer | reference |
| context_pack_version | integer | version at time of run |
| prompt_profile_version | integer | version at time of run |

### Context Pack
A named, versioned blob of context text (names, relationships, recurring references).

| Field | Type | Notes |
|-------|------|-------|
| id | integer | primary key |
| name | text | user-chosen name |
| content | text | full text of the context pack |
| version | integer | increments on each edit |
| created_at | datetime | UTC |
| updated_at | datetime | UTC |

### Prompt Profile
A named, versioned editorial prompt that tells Claude how to refine the transcript.

| Field | Type | Notes |
|-------|------|-------|
| id | integer | primary key |
| name | text | user-chosen name |
| content | text | full prompt text |
| version | integer | increments on each edit |
| created_at | datetime | UTC |
| updated_at | datetime | UTC |

---

## In-Scope Features (v1)

- Paste or file-upload for transcript input
- Context Pack selector on Home screen
- Prompt Profile selector on Home screen
- Assemble context pack + prompt profile + transcript into a single Claude request
- Streaming or standard Claude API response display
- Side-by-side review layout
- Dedicated Ambiguities section (shown only when Claude returns one)
- Save accepted entry to SQLite
- Archive list screen with entry date and short preview
- Single-entry detail view
- Markdown export (downloads a `.md` file)
- Create / edit / delete Context Packs via a simple form
- Create / edit / delete Prompt Profiles via a simple form
- Version numbers recorded on runs and entries
- Seed the default Context Pack from `seed_files/correct names w context.md`
- Seed the default Prompt Profile from `seed_files/transcript prompt.md`
- Claude API key configurable via `.env` file

---

## Out-of-Scope for v1

- Voice recording or transcription
- Cloud storage or sync
- User accounts or authentication
- Multiple users
- Full-text search across entries
- Tags or categories
- PDF or HTML export (Markdown only)
- Entry editing after save
- Undo / redo
- Themes or dark mode
- Mobile layout

---

## Acceptance Criteria

Each item below must be true for v1 to be considered done.

- [ ] The app starts with `python main.py` (or equivalent single command) and opens in a local browser
- [ ] A user can paste a transcript and click Refine; the polished entry appears
- [ ] A user can upload a `.txt` file as a transcript
- [ ] Context Pack and Prompt Profile are both selectable before refinement
- [ ] Claude's response is displayed in a two-column layout (raw | polished)
- [ ] If Claude returns an Ambiguities section, it appears below the polished text in a distinct block
- [ ] Saving an entry writes it to the SQLite database
- [ ] The Archive page lists all saved entries, newest first
- [ ] A saved entry can be exported as a `.md` file via a button
- [ ] Context Packs can be created, edited, and deleted through the UI
- [ ] Prompt Profiles can be created, edited, and deleted through the UI
- [ ] Version numbers are stored on every run and every saved entry
- [ ] The default Context Pack and Prompt Profile are seeded from the files in `seed_files/`
- [ ] No data leaves the machine except the Claude API call
- [ ] The app works with no internet connection except for the Claude API call itself
