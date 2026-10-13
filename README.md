# MindVault — Your Second Brain

MindVault is a student-focused knowledge workspace. This first milestone is a working vertical slice: Flask serves the page and JSON API, SQLite stores notes, the browser supports note CRUD/search/filter, and an optional C executable calculates a small collection score.

## Architecture

```text
Browser (HTML, CSS, vanilla JS)
	| fetch() JSON
Flask routes and validation (app.py)
	| parameterized SQL
SQLite file (instance/mindvault.sqlite3)

Flask stats route -> bounded C subprocess -> integer score
		   -> Python fallback if C is unavailable
```

| Path | Responsibility |
| --- | --- |
| `app.py` | Flask page, REST endpoints, input validation, and score-engine fallback |
| `database.py` | SQLite connection and non-destructive table initialization |
| `templates/index.html` | Accessible page structure and note editor dialog |
| `static/css/style.css` | Responsive sci-fi theme, motion, and reduced-motion rules |
| `static/js/app.js` | Search, filters, note actions, API calls, and starfield canvas |
| `c_engine/knowledge_engine.c` | Small standalone C score calculator |
| `Makefile` | Build and clean commands for the C executable |
| `tests/test_app.py` | Isolated API, validation, persistence, and page tests |
| `instance/mindvault.sqlite3` | Local persistent notes database; ignored by Git |

## First Milestone

Implemented and covered by tests: dashboard note/subject counts, note creation/edit/deletion, subject and tag storage, title/content/tag search, subject filtering, SQLite persistence, input validation, a responsive notes interface, and C score calculation with a Python fallback. The score is only a lightweight collection index (`3 × notes + 8 × subjects`, capped at 100); it is not a measure of mastery.

Knowledge Graph, spaced repetition, flashcards, review history, progress reporting, JSON import/export, and user accounts are later milestones. Their sidebar entries are marked as planned and do not pretend to be functional.

## GitHub Codespaces Setup

In the Codespaces terminal, from this repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make
python -m unittest discover -s tests -v
python app.py
```

Open the forwarded port 5000 shown by Codespaces. The development server binds to `0.0.0.0` and runs with debug mode disabled. If `make` or a C compiler is unavailable, skip that step: Flask will calculate the same simple score in Python. On Ubuntu, install a compiler with `sudo apt update && sudo apt install build-essential` if you have permission.

The API routes are `GET /api/notes` (optional `q` and `subject` query parameters), `POST /api/notes`, `PUT /api/notes/<id>`, `DELETE /api/notes/<id>`, `GET /api/subjects`, and `GET /api/stats`.

## C Module

`make` compiles `c_engine/knowledge_engine.c` into `c_engine/knowledge_engine`. Flask invokes it with two validated integer arguments using `subprocess.run([...], shell=False)` semantics, captures output, and enforces a two-second timeout. No note text is passed to C. If the executable is missing, exits unsuccessfully, times out, or returns invalid output, the same score formula is computed in Python. `make clean` removes only the generated executable.

## Deploying

The frontend is served by Flask, so deploy the Flask application as one web service rather than as a separate static site. For example, on a Python host that supports persistent disks and build commands, use:

```text
Build: pip install -r requirements.txt && make
Start: gunicorn --bind 0.0.0.0:$PORT app:app
```

Mount a persistent volume and set `MINDVAULT_DATABASE` to a SQLite file on that volume, for example `/var/data/mindvault.sqlite3`. Without persistent storage, a host may erase SQLite data when the instance restarts or is redeployed. Confirm the provider's current disk and port configuration before deploying.

GitHub Pages only serves static files; it cannot run Flask, compile/run this C program, or provide SQLite storage. A static frontend also cannot securely use a developer's local SQLite file. If a separate static host is chosen later, it must call a deployed, secured Flask API.

This first milestone has no login or multi-user isolation. Do not expose it as a public service containing private notes until authentication and authorization are implemented. Keep secrets out of the repository, disable Flask debug mode in production, and restrict access while it is a single-user app.

To commit the project without staging local data, add only source files:

```bash
git add README.md app.py database.py requirements.txt Makefile c_engine/knowledge_engine.c templates/index.html static/css/style.css static/js/app.js tests/test_app.py .gitignore
git commit -m "Build MindVault first milestone"
git push origin main
```