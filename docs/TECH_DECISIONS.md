# Journal Refinery — Tech Decisions

This document explains every significant technical choice and why it was made. The guiding principle is: use the simplest tool that works. Every decision here is intentionally boring.

---

## Language: Python

Python is readable, beginner-friendly, and has a rich standard library. It is the right default for a small local tool.

---

## Web Framework: FastAPI

FastAPI is a modern Python web framework that is easy to learn and produces clean, explicit route definitions. It handles form submissions, file uploads, and JSON responses without any ceremony. It is lighter than Django and more structured than raw WSGI. For a local app with a small number of routes, it is a good fit.

We are using it in its simplest form: plain HTTP routes with form-encoded POST bodies and Jinja2 template responses. No GraphQL, no WebSockets, no async complexity for now.

---

## Templates: Jinja2

Jinja2 is the standard template engine for Python web apps. FastAPI has first-class support for it. Templates let us write plain HTML with simple variable substitution and loops. No JavaScript build step, no component tree, no bundler. A beginner can read and edit a Jinja2 template without learning a new paradigm.

---

## Database: SQLite via plain sqlite3

SQLite is a single file on disk. There is nothing to install, configure, or run. For a local-first app used by one person, it is the correct choice.

We are using Python's built-in `sqlite3` module rather than an ORM. The schema is simple (four tables), the queries are straightforward, and the plain SQL is easy to read. An ORM would add learning overhead, magic behavior, and a new dependency without adding meaningful value here.

The database file lives in a `data/` directory in the project folder.

---

## Frontend: Plain HTML + minimal CSS

There is no JavaScript framework. No React, no Vue, no Svelte. No Tailwind. No npm. No build step.

Pages are rendered server-side by FastAPI + Jinja2 and returned as complete HTML. Forms use standard HTML form submission (GET and POST). The only JavaScript that might appear is small inline scripts for specific interactions (like confirming a delete), written in plain vanilla JS.

This is intentional. The app is used by one person on their own machine. A lightweight HTML page is fast, readable, and maintainable without a frontend build environment.

---

## Claude Integration: Anthropic Python SDK

We call the Claude API using the official `anthropic` Python package. The API key is stored in a `.env` file and loaded at startup — it never leaves the local machine except in the API request itself.

We assemble the full prompt in Python by concatenating: the Prompt Profile text, the Context Pack text, and the raw transcript. Claude returns the polished entry and optional Ambiguities section as a single text response. We parse the split in Python by looking for the `Ambiguities` header.

---

## Configuration: .env file

The Claude API key is the only configuration the app needs. It is stored in a `.env` file at the project root. The app reads it with Python's `python-dotenv` package (or directly with `os.environ` if we want to avoid a dependency). The `.env` file is never committed to version control.

---

## No Docker, No Electron, No Tauri

The app runs as a plain Python process. The user runs `python main.py` and opens `http://localhost:8000` in their browser. No container, no desktop packaging, no installer. This is the simplest possible distribution for a local developer tool.

---

## Dependency Summary

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server to run FastAPI |
| `jinja2` | HTML templates |
| `python-multipart` | Required by FastAPI for file upload handling |
| `anthropic` | Claude API client |
| `python-dotenv` | Load API key from `.env` |

That is six dependencies. All are small, stable, and widely used. The standard library handles everything else, including `sqlite3`.

---

## What We Are Deliberately Avoiding

| Thing | Reason avoided |
|-------|---------------|
| SQLAlchemy or any ORM | The schema is simple; plain SQL is clearer for a beginner |
| React / Vue / Svelte | No JS build step needed; server-rendered HTML is sufficient |
| Tailwind CSS | Unnecessary overhead; a small stylesheet is easier to read |
| PostgreSQL | Overkill for a single-user local app |
| Docker | Adds complexity; `python main.py` is sufficient |
| Electron / Tauri | Desktop packaging is unnecessary; the browser is the UI |
| Redis / Celery | No background jobs needed |
| WebSockets | Responses are fast enough to handle synchronously |
