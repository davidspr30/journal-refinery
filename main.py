"""
main.py

Entry point for Journal Refinery.

Run the app with:
    python main.py

Then open http://localhost:8000 in your browser.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on startup."""
    init_db()
    yield


app = FastAPI(title="Journal Refinery", lifespan=lifespan)

# Serve files in static/ at the /static URL prefix.
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/")
def home(request: Request):
    """Homepage — the starting point for refining a transcript."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    """Simple health check. Returns OK if the app is running."""
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
