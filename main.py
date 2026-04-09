"""
main.py

Entry point for Journal Refinery.

Run the app with:
    python main.py

Then open http://localhost:8000 in your browser.
"""

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from datetime import date as date_type

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sqlite3

import app.config as config
from app.claude_client import call_claude
from app.db import get_connection, init_db
from app.intake import (
    assemble_request,
    get_all_context_packs,
    get_all_prompt_profiles,
    get_context_pack,
    get_prompt_profile,
    resolve_transcript,
    seed_defaults,
)
from app.entries import get_all_entries, get_entry, get_entry_for_run, save_entry
from app.parser import parse_response
from app.runs import get_run, save_run
from app.packs import (
    get_all_packs,
    get_default_pack_id,
    set_default_pack,
    create_pack,
    update_pack,
    delete_pack,
    duplicate_pack,
    import_seed_pack,
    get_all_profiles,
    get_default_profile_id,
    set_default_profile,
    create_profile,
    update_profile,
    delete_profile,
    duplicate_profile,
    import_seed_profile,
)

ALLOWED_UPLOAD_EXTENSIONS = {".txt", ".md"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database and seed defaults on startup."""
    init_db()
    conn = get_connection()
    try:
        seed_defaults(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="Journal Refinery", lifespan=lifespan)

# Serve files in static/ at the /static URL prefix.
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

@app.get("/")
def home(request: Request):
    """Homepage — show the transcript intake form."""
    conn = get_connection()
    try:
        context_packs = get_all_context_packs(conn)
        prompt_profiles = get_all_prompt_profiles(conn)
        default_pack_id = get_default_pack_id(conn)
        default_profile_id = get_default_profile_id(conn)
    finally:
        conn.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "context_packs": context_packs,
        "prompt_profiles": prompt_profiles,
        "error": None,
        "form": {
            "context_pack_id": default_pack_id,
            "prompt_profile_id": default_profile_id,
        },
    })


# ---------------------------------------------------------------------------
# Refine — calls Claude and redirects to the review page
# ---------------------------------------------------------------------------

@app.post("/refine")
async def refine(
    request: Request,
    transcript: str = Form(default=""),
    transcript_file: UploadFile = File(default=None),
    context_pack_id: int = Form(...),
    prompt_profile_id: int = Form(...),
    notes: str = Form(default=""),
):
    """
    Validate the intake form, assemble the request, call Claude,
    save the run, and redirect to the review page.
    """
    conn = get_connection()
    try:
        context_packs = get_all_context_packs(conn)
        prompt_profiles = get_all_prompt_profiles(conn)

        form_state = {
            "context_pack_id": context_pack_id,
            "prompt_profile_id": prompt_profile_id,
            "notes": notes,
        }

        # --- Resolve transcript text -----------------------------------

        resolved_transcript, transcript_error = await resolve_transcript(
            transcript, transcript_file, ALLOWED_UPLOAD_EXTENSIONS
        )
        if transcript_error:
            return _home_with_error(
                request, templates, context_packs, prompt_profiles,
                transcript_error, form_state,
            )

        # --- Fetch chosen context pack and prompt profile --------------

        pack = get_context_pack(conn, context_pack_id)
        profile = get_prompt_profile(conn, prompt_profile_id)

        if pack is None or profile is None:
            return _home_with_error(
                request, templates, context_packs, prompt_profiles,
                "The selected Context Pack or Prompt Profile could not be found.",
                form_state,
            )

        # --- Check API key before proceeding ---------------------------

        if not config.ANTHROPIC_API_KEY:
            return _home_with_error(
                request, templates, context_packs, prompt_profiles,
                "ANTHROPIC_API_KEY is not set. "
                "Copy .env.example to .env and add your Anthropic API key.",
                form_state,
            )

        # --- Assemble the full request ---------------------------------

        assembled = assemble_request(
            transcript=resolved_transcript,
            context_pack_content=pack["content"],
            prompt_profile_content=profile["content"],
            notes=notes,
        )

        # --- Call Claude (sync SDK, run in thread so we don't block) ---

        response_text, api_error = await asyncio.to_thread(call_claude, assembled)

        # --- Save run and redirect to review ---------------------------

        if api_error:
            run_id = save_run(
                conn,
                transcript_raw=resolved_transcript,
                context_pack_id=pack["id"],
                prompt_profile_id=profile["id"],
                context_pack_version=pack["version"],
                prompt_profile_version=profile["version"],
                assembled_request=assembled,
                model=config.CLAUDE_MODEL,
                response_raw=None,
                output_polished=None,
                output_ambiguities=None,
                status="error",
                error_message=api_error,
            )
        else:
            polished, ambiguities = parse_response(response_text)
            run_id = save_run(
                conn,
                transcript_raw=resolved_transcript,
                context_pack_id=pack["id"],
                prompt_profile_id=profile["id"],
                context_pack_version=pack["version"],
                prompt_profile_version=profile["version"],
                assembled_request=assembled,
                model=config.CLAUDE_MODEL,
                response_raw=response_text,
                output_polished=polished,
                output_ambiguities=ambiguities,
                status="complete",
            )

    finally:
        conn.close()

    # 303 See Other: browser sends GET to /review/{run_id}.
    # This prevents re-submitting the form on page refresh.
    return RedirectResponse(f"/review/{run_id}", status_code=303)


# ---------------------------------------------------------------------------
# Review — shows the result of a run
# ---------------------------------------------------------------------------

@app.get("/review/{run_id}")
def review(request: Request, run_id: int):
    """Show the raw transcript and polished output side by side."""
    conn = get_connection()
    try:
        run = get_run(conn, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        pack = get_context_pack(conn, run["context_pack_id"])
        profile = get_prompt_profile(conn, run["prompt_profile_id"])
        # Check whether this run has already been saved as an entry.
        existing_entry = get_entry_for_run(conn, run_id)
    finally:
        conn.close()

    return templates.TemplateResponse("review.html", {
        "request": request,
        "run": run,
        "pack": pack,
        "profile": profile,
        "today": date_type.today().isoformat(),
        "existing_entry_id": existing_entry["id"] if existing_entry else None,
    })


# ---------------------------------------------------------------------------
# Save entry — creates a permanent journal entry from a completed run
# ---------------------------------------------------------------------------

@app.post("/entries")
def save_entry_route(
    request: Request,
    run_id: int = Form(...),
    entry_date: str = Form(...),
):
    """
    Save the polished output from a run as a permanent journal entry.

    If the run has already been saved, redirects to the existing entry
    rather than creating a duplicate.
    """
    conn = get_connection()
    try:
        # Guard: don't create a duplicate if already saved.
        existing = get_entry_for_run(conn, run_id)
        if existing:
            return RedirectResponse(f"/entries/{existing['id']}", status_code=303)

        run = get_run(conn, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        if run["status"] != "complete":
            raise HTTPException(status_code=400, detail="Only completed runs can be saved.")

        pack = get_context_pack(conn, run["context_pack_id"])
        profile = get_prompt_profile(conn, run["prompt_profile_id"])

        entry_id = save_entry(
            conn,
            run_id=run_id,
            entry_date=entry_date,
            transcript_raw=run["transcript_raw"],
            output_polished=run["output_polished"],
            output_ambiguities=run["output_ambiguities"],
            context_pack_id=run["context_pack_id"],
            prompt_profile_id=run["prompt_profile_id"],
            context_pack_version=run["context_pack_version"],
            prompt_profile_version=run["prompt_profile_version"],
            context_pack_name=pack["name"] if pack else "—",
            prompt_profile_name=profile["name"] if profile else "—",
        )
    finally:
        conn.close()

    return RedirectResponse(f"/entries/{entry_id}", status_code=303)


# ---------------------------------------------------------------------------
# Archive — list of all saved entries
# ---------------------------------------------------------------------------

@app.get("/archive")
def archive(request: Request):
    """Show all saved journal entries, newest first."""
    conn = get_connection()
    try:
        entries = get_all_entries(conn)
    finally:
        conn.close()

    return templates.TemplateResponse("archive.html", {
        "request": request,
        "entries": entries,
    })


# ---------------------------------------------------------------------------
# Entry detail — view a single saved entry
# ---------------------------------------------------------------------------

@app.get("/entries/{entry_id}")
def entry_detail(request: Request, entry_id: int):
    """Show a single saved journal entry."""
    conn = get_connection()
    try:
        entry = get_entry(conn, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found.")
    finally:
        conn.close()

    return templates.TemplateResponse("entry.html", {
        "request": request,
        "entry": entry,
    })


# ---------------------------------------------------------------------------
# Export — download a saved entry as a Markdown file
# ---------------------------------------------------------------------------

@app.get("/entries/{entry_id}/export")
def export_entry(entry_id: int):
    """
    Generate and serve a Markdown file for a saved entry.

    Filename format: YYYY-MM-DD-journal-entry.md
    If the user has multiple entries on the same date, the files will
    share a name — they can rename as needed. The entry id is not
    included in the filename to keep it clean.
    """
    conn = get_connection()
    try:
        entry = get_entry(conn, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found.")
    finally:
        conn.close()

    markdown = _build_markdown(entry)
    filename = f"{entry['entry_date']}-journal-entry.md"

    return Response(
        content=markdown,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Preview — shows assembled components before sending (debug / inspect tool)
# ---------------------------------------------------------------------------

@app.post("/preview")
async def preview(
    request: Request,
    transcript: str = Form(default=""),
    transcript_file: UploadFile = File(default=None),
    context_pack_id: int = Form(...),
    prompt_profile_id: int = Form(...),
    notes: str = Form(default=""),
):
    """
    Validate the intake form, assemble the request, and show a preview
    of all components before sending to Claude.

    This route is still available as an inspection tool. The main flow
    now goes through POST /refine.
    """
    conn = get_connection()
    try:
        context_packs = get_all_context_packs(conn)
        prompt_profiles = get_all_prompt_profiles(conn)

        form_state = {
            "context_pack_id": context_pack_id,
            "prompt_profile_id": prompt_profile_id,
            "notes": notes,
        }

        resolved_transcript, transcript_error = await resolve_transcript(
            transcript, transcript_file, ALLOWED_UPLOAD_EXTENSIONS
        )
        if transcript_error:
            return _home_with_error(
                request, templates, context_packs, prompt_profiles,
                transcript_error, form_state,
            )

        pack = get_context_pack(conn, context_pack_id)
        profile = get_prompt_profile(conn, prompt_profile_id)

        if pack is None or profile is None:
            return _home_with_error(
                request, templates, context_packs, prompt_profiles,
                "The selected Context Pack or Prompt Profile could not be found.",
                form_state,
            )

        assembled = assemble_request(
            transcript=resolved_transcript,
            context_pack_content=pack["content"],
            prompt_profile_content=profile["content"],
            notes=notes,
        )

    finally:
        conn.close()

    return templates.TemplateResponse("preview.html", {
        "request": request,
        "transcript": resolved_transcript,
        "pack": pack,
        "profile": profile,
        "notes": notes.strip(),
        "assembled": assembled,
    })


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Simple health check. Returns OK if the app is running."""
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_markdown(entry):
    """
    Build the Markdown string for an exported journal entry.

    Structure:
        # Journal Entry — YYYY-MM-DD
        metadata block
        ---
        polished text
        ---              ← only if ambiguities present
        ## Ambiguities   ← only if ambiguities present
        ambiguities text
    """
    pack_credit = f"{entry['context_pack_name']} (v{entry['context_pack_version']})"
    profile_credit = f"{entry['prompt_profile_name']} (v{entry['prompt_profile_version']})"

    lines = [
        f"# Journal Entry — {entry['entry_date']}",
        "",
        f"**Date:** {entry['entry_date']}  ",
        f"**Context Pack:** {pack_credit}  ",
        f"**Prompt Profile:** {profile_credit}",
        "",
        "---",
        "",
        entry["output_polished"],
    ]

    if entry["output_ambiguities"]:
        lines += [
            "",
            "---",
            "",
            "## Ambiguities",
            "",
            entry["output_ambiguities"],
        ]

    return "\n".join(lines) + "\n"


def _home_with_error(request, templates, context_packs, prompt_profiles, error, form):
    """Re-render the home page with an error message and the user's previous selections."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "context_packs": context_packs,
        "prompt_profiles": prompt_profiles,
        "error": error,
        "form": form,
    })


# ---------------------------------------------------------------------------
# Context Pack management
# ---------------------------------------------------------------------------

@app.get("/context-packs")
def context_packs_list(request: Request):
    """List all context packs."""
    conn = get_connection()
    try:
        packs = get_all_packs(conn)
        default_id = get_default_pack_id(conn)
    finally:
        conn.close()

    return templates.TemplateResponse("context_packs.html", {
        "request": request,
        "packs": packs,
        "default_id": default_id,
        "error": None,
    })


@app.get("/context-packs/new")
def context_pack_new(request: Request):
    """Show the blank create form for a context pack."""
    return templates.TemplateResponse("context_pack_form.html", {
        "request": request,
        "pack": None,
        "error": None,
    })


@app.post("/context-packs/new")
def context_pack_create(
    request: Request,
    name: str = Form(...),
    content: str = Form(...),
):
    """Create a new context pack and redirect to the list."""
    if not name.strip() or not content.strip():
        return templates.TemplateResponse("context_pack_form.html", {
            "request": request,
            "pack": None,
            "error": "Name and content are both required.",
        })

    conn = get_connection()
    try:
        create_pack(conn, name, content)
    finally:
        conn.close()

    return RedirectResponse("/context-packs", status_code=303)


@app.get("/context-packs/{pack_id}/edit")
def context_pack_edit(request: Request, pack_id: int):
    """Show the edit form for an existing context pack."""
    conn = get_connection()
    try:
        pack = get_context_pack(conn, pack_id)
    finally:
        conn.close()

    if pack is None:
        raise HTTPException(status_code=404, detail="Context pack not found.")

    return templates.TemplateResponse("context_pack_form.html", {
        "request": request,
        "pack": pack,
        "error": None,
    })


@app.post("/context-packs/{pack_id}/edit")
def context_pack_update(
    request: Request,
    pack_id: int,
    name: str = Form(...),
    content: str = Form(...),
):
    """Save edits to a context pack (increments version)."""
    if not name.strip() or not content.strip():
        conn = get_connection()
        try:
            pack = get_context_pack(conn, pack_id)
        finally:
            conn.close()
        return templates.TemplateResponse("context_pack_form.html", {
            "request": request,
            "pack": pack,
            "error": "Name and content are both required.",
        })

    conn = get_connection()
    try:
        update_pack(conn, pack_id, name, content)
    finally:
        conn.close()

    return RedirectResponse("/context-packs", status_code=303)


@app.post("/context-packs/{pack_id}/duplicate")
def context_pack_duplicate(pack_id: int):
    """Duplicate a context pack (new record, version 1)."""
    conn = get_connection()
    try:
        duplicate_pack(conn, pack_id)
    finally:
        conn.close()

    return RedirectResponse("/context-packs", status_code=303)


@app.post("/context-packs/{pack_id}/set-default")
def context_pack_set_default(pack_id: int):
    """Mark a context pack as the default selection on the home form."""
    conn = get_connection()
    try:
        set_default_pack(conn, pack_id)
    finally:
        conn.close()

    return RedirectResponse("/context-packs", status_code=303)


@app.post("/context-packs/{pack_id}/delete")
def context_pack_delete(request: Request, pack_id: int):
    """Delete a context pack. Shows an error if it is referenced by saved runs."""
    conn = get_connection()
    try:
        try:
            delete_pack(conn, pack_id)
        except sqlite3.IntegrityError:
            packs = get_all_packs(conn)
            default_id = get_default_pack_id(conn)
            return templates.TemplateResponse("context_packs.html", {
                "request": request,
                "packs": packs,
                "default_id": default_id,
                "error": (
                    "This context pack cannot be deleted because it is used by "
                    "one or more saved runs or entries."
                ),
            })
    finally:
        conn.close()

    return RedirectResponse("/context-packs", status_code=303)


@app.post("/context-packs/import-seed")
def context_pack_import_seed(request: Request):
    """Import the bundled seed context pack from the seed_files/ directory."""
    conn = get_connection()
    try:
        new_id, error = import_seed_pack(conn)
        if error:
            packs = get_all_packs(conn)
            default_id = get_default_pack_id(conn)
            return templates.TemplateResponse("context_packs.html", {
                "request": request,
                "packs": packs,
                "default_id": default_id,
                "error": error,
            })
    finally:
        conn.close()

    return RedirectResponse("/context-packs", status_code=303)


# ---------------------------------------------------------------------------
# Prompt Profile management
# ---------------------------------------------------------------------------

@app.get("/prompt-profiles")
def prompt_profiles_list(request: Request):
    """List all prompt profiles."""
    conn = get_connection()
    try:
        profiles = get_all_profiles(conn)
        default_id = get_default_profile_id(conn)
    finally:
        conn.close()

    return templates.TemplateResponse("prompt_profiles.html", {
        "request": request,
        "profiles": profiles,
        "default_id": default_id,
        "error": None,
    })


@app.get("/prompt-profiles/new")
def prompt_profile_new(request: Request):
    """Show the blank create form for a prompt profile."""
    return templates.TemplateResponse("prompt_profile_form.html", {
        "request": request,
        "profile": None,
        "error": None,
    })


@app.post("/prompt-profiles/new")
def prompt_profile_create(
    request: Request,
    name: str = Form(...),
    content: str = Form(...),
):
    """Create a new prompt profile and redirect to the list."""
    if not name.strip() or not content.strip():
        return templates.TemplateResponse("prompt_profile_form.html", {
            "request": request,
            "profile": None,
            "error": "Name and content are both required.",
        })

    conn = get_connection()
    try:
        create_profile(conn, name, content)
    finally:
        conn.close()

    return RedirectResponse("/prompt-profiles", status_code=303)


@app.get("/prompt-profiles/{profile_id}/edit")
def prompt_profile_edit(request: Request, profile_id: int):
    """Show the edit form for an existing prompt profile."""
    conn = get_connection()
    try:
        profile = get_prompt_profile(conn, profile_id)
    finally:
        conn.close()

    if profile is None:
        raise HTTPException(status_code=404, detail="Prompt profile not found.")

    return templates.TemplateResponse("prompt_profile_form.html", {
        "request": request,
        "profile": profile,
        "error": None,
    })


@app.post("/prompt-profiles/{profile_id}/edit")
def prompt_profile_update(
    request: Request,
    profile_id: int,
    name: str = Form(...),
    content: str = Form(...),
):
    """Save edits to a prompt profile (increments version)."""
    if not name.strip() or not content.strip():
        conn = get_connection()
        try:
            profile = get_prompt_profile(conn, profile_id)
        finally:
            conn.close()
        return templates.TemplateResponse("prompt_profile_form.html", {
            "request": request,
            "profile": profile,
            "error": "Name and content are both required.",
        })

    conn = get_connection()
    try:
        update_profile(conn, profile_id, name, content)
    finally:
        conn.close()

    return RedirectResponse("/prompt-profiles", status_code=303)


@app.post("/prompt-profiles/{profile_id}/duplicate")
def prompt_profile_duplicate(profile_id: int):
    """Duplicate a prompt profile (new record, version 1)."""
    conn = get_connection()
    try:
        duplicate_profile(conn, profile_id)
    finally:
        conn.close()

    return RedirectResponse("/prompt-profiles", status_code=303)


@app.post("/prompt-profiles/{profile_id}/set-default")
def prompt_profile_set_default(profile_id: int):
    """Mark a prompt profile as the default selection on the home form."""
    conn = get_connection()
    try:
        set_default_profile(conn, profile_id)
    finally:
        conn.close()

    return RedirectResponse("/prompt-profiles", status_code=303)


@app.post("/prompt-profiles/{profile_id}/delete")
def prompt_profile_delete(request: Request, profile_id: int):
    """Delete a prompt profile. Shows an error if it is referenced by saved runs."""
    conn = get_connection()
    try:
        try:
            delete_profile(conn, profile_id)
        except sqlite3.IntegrityError:
            profiles = get_all_profiles(conn)
            default_id = get_default_profile_id(conn)
            return templates.TemplateResponse("prompt_profiles.html", {
                "request": request,
                "profiles": profiles,
                "default_id": default_id,
                "error": (
                    "This prompt profile cannot be deleted because it is used by "
                    "one or more saved runs or entries."
                ),
            })
    finally:
        conn.close()

    return RedirectResponse("/prompt-profiles", status_code=303)


@app.post("/prompt-profiles/import-seed")
def prompt_profile_import_seed(request: Request):
    """Import the bundled seed prompt profile from the seed_files/ directory."""
    conn = get_connection()
    try:
        new_id, error = import_seed_profile(conn)
        if error:
            profiles = get_all_profiles(conn)
            default_id = get_default_profile_id(conn)
            return templates.TemplateResponse("prompt_profiles.html", {
                "request": request,
                "profiles": profiles,
                "default_id": default_id,
                "error": error,
            })
    finally:
        conn.close()

    return RedirectResponse("/prompt-profiles", status_code=303)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
