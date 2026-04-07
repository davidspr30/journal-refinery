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
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
from app.parser import parse_response
from app.runs import get_run, save_run

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
    finally:
        conn.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "context_packs": context_packs,
        "prompt_profiles": prompt_profiles,
        "error": None,
        "form": {},
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
    finally:
        conn.close()

    return templates.TemplateResponse("review.html", {
        "request": request,
        "run": run,
        "pack": pack,
        "profile": profile,
    })


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

def _home_with_error(request, templates, context_packs, prompt_profiles, error, form):
    """Re-render the home page with an error message and the user's previous selections."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "context_packs": context_packs,
        "prompt_profiles": prompt_profiles,
        "error": error,
        "form": form,
    })


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
