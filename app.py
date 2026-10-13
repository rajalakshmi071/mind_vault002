import json
import os
import subprocess
from pathlib import Path

from flask import Flask, current_app, jsonify, render_template, request

from database import connect_db, init_db


BASE_DIR = Path(__file__).resolve().parent


def validate_note(payload):
    if not isinstance(payload, dict):
        return None, "A JSON object is required."

    title = payload.get("title")
    content = payload.get("content", "")
    subject = payload.get("subject", "General")
    tags = payload.get("tags", [])

    if not isinstance(title, str) or not title.strip():
        return None, "Title is required."
    if len(title.strip()) > 120:
        return None, "Title must be 120 characters or fewer."
    if not isinstance(content, str) or len(content) > 12000:
        return None, "Content must be text with 12,000 characters or fewer."
    if not isinstance(subject, str) or not subject.strip() or len(subject.strip()) > 60:
        return None, "Subject must be 1 to 60 characters."
    if not isinstance(tags, list) or len(tags) > 10:
        return None, "Tags must be a list with no more than 10 items."

    clean_tags = []
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > 30:
            return None, "Each tag must be 1 to 30 characters."
        clean_tag = tag.strip()
        if clean_tag.lower() not in {item.lower() for item in clean_tags}:
            clean_tags.append(clean_tag)

    return {
        "title": title.strip(),
        "content": content.strip(),
        "subject": subject.strip(),
        "tags": clean_tags,
    }, None


def serialize_note(row):
    try:
        tags = json.loads(row["tags"])
    except (TypeError, json.JSONDecodeError):
        tags = []
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "subject": row["subject"],
        "tags": tags if isinstance(tags, list) else [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def calculate_learning_score(note_count, subject_count):
    engine = Path(current_app.config["KNOWLEDGE_ENGINE_PATH"])
    try:
        result = subprocess.run(
            [str(engine), str(note_count), str(subject_count)],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        score = int(result.stdout.strip())
        if 0 <= score <= 100:
            return score, "c"
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return min(100, note_count * 3 + subject_count * 8), "python"


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "MINDVAULT_DATABASE", str(BASE_DIR / "instance" / "mindvault.sqlite3")
        ),
        KNOWLEDGE_ENGINE_PATH=os.environ.get(
            "MINDVAULT_KNOWLEDGE_ENGINE", str(BASE_DIR / "c_engine" / "knowledge_engine")
        ),
        MAX_CONTENT_LENGTH=256 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    init_db(app.config["DATABASE"])

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/notes")
    def list_notes():
        search = request.args.get("q", "").strip()
        subject = request.args.get("subject", "").strip()
        conditions = []
        values = []
        if search:
            conditions.append("(title LIKE ? OR content LIKE ? OR tags LIKE ?)")
            pattern = f"%{search}%"
            values.extend([pattern, pattern, pattern])
        if subject:
            conditions.append("subject = ?")
            values.append(subject)

        sql = "SELECT * FROM notes"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY updated_at DESC, id DESC LIMIT 200"
        with connect_db() as db:
            rows = db.execute(sql, values).fetchall()
        return jsonify([serialize_note(row) for row in rows])

    @app.get("/api/subjects")
    def list_subjects():
        with connect_db() as db:
            rows = db.execute(
                "SELECT DISTINCT subject FROM notes ORDER BY subject COLLATE NOCASE"
            ).fetchall()
        return jsonify([row["subject"] for row in rows])

    @app.post("/api/notes")
    def create_note():
        note, error = validate_note(request.get_json(silent=True))
        if error:
            return jsonify({"error": error}), 400
        with connect_db() as db:
            cursor = db.execute(
                "INSERT INTO notes (title, content, subject, tags) VALUES (?, ?, ?, ?)",
                (note["title"], note["content"], note["subject"], json.dumps(note["tags"])),
            )
            row = db.execute("SELECT * FROM notes WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(serialize_note(row)), 201

    @app.put("/api/notes/<int:note_id>")
    def update_note(note_id):
        note, error = validate_note(request.get_json(silent=True))
        if error:
            return jsonify({"error": error}), 400
        with connect_db() as db:
            cursor = db.execute(
                "UPDATE notes SET title = ?, content = ?, subject = ?, tags = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (note["title"], note["content"], note["subject"], json.dumps(note["tags"]), note_id),
            )
            if cursor.rowcount == 0:
                return jsonify({"error": "Note not found."}), 404
            row = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        return jsonify(serialize_note(row))

    @app.delete("/api/notes/<int:note_id>")
    def delete_note(note_id):
        with connect_db() as db:
            cursor = db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Note not found."}), 404
        return jsonify({"deleted": True})

    @app.get("/api/stats")
    def stats():
        with connect_db() as db:
            counts = db.execute(
                "SELECT COUNT(*) AS note_count, COUNT(DISTINCT subject) AS subject_count "
                "FROM notes"
            ).fetchone()
            recent = db.execute(
                "SELECT * FROM notes ORDER BY updated_at DESC, id DESC LIMIT 4"
            ).fetchall()
        note_count = counts["note_count"]
        subject_count = counts["subject_count"]
        score, engine = calculate_learning_score(note_count, subject_count)
        return jsonify({
            "note_count": note_count,
            "subject_count": subject_count,
            "review_count": 0,
            "learning_score": score,
            "score_engine": engine,
            "recent_notes": [serialize_note(row) for row in recent],
        })

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "Request is too large."}), 413

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
