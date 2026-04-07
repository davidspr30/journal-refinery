"""
main.py

Entry point for Journal Refinery.

Run the app with:
    python main.py

Then open http://localhost:8000 in your browser.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import get_connection, init_db
from app.intake import (
    assemble_request,
    get_all_context_packs,
    get_all_prompt_profiles,
    get_context_pack,
    get_prompt_profile,
    seed_defaults,
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
# Preview
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
    Validate the intake form, resolve the transcript text, assemble the
    full request, and render the preview page.

    Precedence rule: if the user fills in the textarea AND uploads a file,
    the textarea wins. The textarea is the visible input — what you see in
    the box is what you intend to submit. A file upload alongside existing
    textarea text is almost certainly accidental.
    """
    conn = get_connection()
    try:
        context_packs = get_all_context_packs(conn)
        prompt_profiles = get_all_prompt_profiles(conn)

        # --- Resolve transcript text -----------------------------------

        file_provided = (
            transcript_file is not None
            and transcript_file.filename != ""
        )

        if transcript.strip():
            # Textarea has content — use it regardless of any uploaded file.
            resolved_transcript = transcript.strip()

        elif file_provided:
            # No textarea content, but a file was uploaded — validate and read it.
            suffix = _file_extension(transcript_file.filename)
            if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
                return _home_with_error(
                    request, templates, context_packs, prompt_profiles,
                    f"Uploaded file must be .txt or .md, got '{suffix or transcript_file.filename}'.",
                    {"context_pack_id": context_pack_id, "prompt_profile_id": prompt_profile_id, "notes": notes},
                )
            raw_bytes = await transcript_file.read()
            resolved_transcript = raw_bytes.decode("utf-8", errors="replace").strip()

        else:
            # Neither textarea nor file — cannot proceed.
            return _home_with_error(
                request, templates, context_packs, prompt_profiles,
                "Please paste a transcript or upload a .txt or .md file.",
                {"context_pack_id": context_pack_id, "prompt_profile_id": prompt_profile_id, "notes": notes},
            )

        if not resolved_transcript:
            return _home_with_error(
                request, templates, context_packs, prompt_profiles,
                "The transcript was empty. Please add some text.",
                {"context_pack_id": context_pack_id, "prompt_profile_id": prompt_profile_id, "notes": notes},
            )

        # --- Fetch chosen context pack and prompt profile --------------

        pack = get_context_pack(conn, context_pack_id)
        profile = get_prompt_profile(conn, prompt_profile_id)

        if pack is None or profile is None:
            return _home_with_error(
                request, templates, context_packs, prompt_profiles,
                "The selected Context Pack or Prompt Profile could not be found.",
                {"context_pack_id": context_pack_id, "prompt_profile_id": prompt_profile_id, "notes": notes},
            )

        # --- Assemble the full request ---------------------------------

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

def _file_extension(filename):
    """Return the lowercase extension of a filename, e.g. '.txt'."""
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


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
