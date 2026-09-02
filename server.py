#!/usr/bin/env python3
"""Authenticated web/API server for the RECORD application."""

import hmac
import os
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request, send_file
from werkzeug.utils import secure_filename


ROOT = Path(__file__).resolve().parent
MAX_UPLOAD = 50 * 1024 * 1024
CATEGORIES = {
    "html": (ROOT / "html", {".html", ".htm"}),
    "text": (ROOT / "text", {".txt", ".md", ".markdown", ".log", ".csv", ".json", ".text", ".sql", ".xml", ".yml", ".yaml"}),
    "sql": (ROOT / "sql", {".sql"}),
    "docx": (ROOT / "word", {".docx"}),
    "excel": (ROOT / "excel", {".xlsx", ".xlsm", ".csv"}),
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD


def credentials_ok():
    auth = request.authorization
    username = os.environ.get("RECORD_USERNAME", "")
    password = os.environ.get("RECORD_PASSWORD", "")
    return bool(
        username
        and password
        and auth
        and hmac.compare_digest(auth.username or "", username)
        and hmac.compare_digest(auth.password or "", password)
    )


@app.before_request
def require_login():
    if credentials_ok():
        return None
    return Response(
        "Authentication required", 401,
        {"WWW-Authenticate": 'Basic realm="RECORD", charset="UTF-8"'},
    )


@app.after_request
def secure_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


def category_config(key):
    config = CATEGORIES.get(key)
    if not config:
        return None
    folder, extensions = config
    folder.mkdir(parents=True, exist_ok=True)
    return folder, extensions


def valid_name(name, extensions):
    return (
        bool(name)
        and name == Path(name).name
        and name not in {".", ".."}
        and Path(name).suffix.lower() in extensions
    )


@app.get("/")
def index():
    return send_file(ROOT / "record.html")


@app.get("/login")
def login():
    return redirect("/", code=302)


@app.get("/api/files/<category>")
def list_files(category):
    config = category_config(category)
    if not config:
        return jsonify(error="Unknown category"), 404
    folder, extensions = config
    names = sorted(
        (path.name for path in folder.iterdir() if path.is_file() and path.suffix.lower() in extensions),
        key=str.casefold,
    )
    return jsonify(files=names)


@app.get("/api/files/<category>/<path:name>")
def download_file(category, name):
    config = category_config(category)
    if not config:
        return jsonify(error="Unknown category"), 404
    folder, extensions = config
    if not valid_name(name, extensions):
        return jsonify(error="Invalid filename or file type"), 400
    path = folder / name
    if not path.is_file():
        return jsonify(error="File not found"), 404
    return send_file(path, as_attachment=False, download_name=name)


@app.post("/api/files/<category>")
def upload_files(category):
    config = category_config(category)
    if not config:
        return jsonify(error="Unknown category"), 404
    folder, extensions = config
    replace = request.form.get("replace") == "true"
    uploaded, skipped, rejected = [], [], []
    for incoming in request.files.getlist("files"):
        original = incoming.filename or ""
        name = secure_filename(original)
        if name != original or not valid_name(name, extensions):
            rejected.append(original)
            continue
        destination = folder / name
        if destination.exists() and not replace:
            skipped.append(name)
            continue
        incoming.save(destination)
        uploaded.append(name)
    return jsonify(uploaded=uploaded, skipped=skipped, rejected=rejected)


@app.put("/api/files/<category>/<path:name>")
def update_file(category, name):
    config = category_config(category)
    if not config:
        return jsonify(error="Unknown category"), 404
    folder, extensions = config
    if not valid_name(name, extensions):
        return jsonify(error="Invalid filename or file type"), 400
    if category not in {"html", "text", "sql"}:
        return jsonify(error="This file type cannot be edited in the browser"), 405
    path = folder / name
    if not path.is_file():
        return jsonify(error="File not found"), 404
    path.write_bytes(request.get_data(cache=False))
    return jsonify(saved=name)


@app.delete("/api/files/<category>/<path:name>")
def delete_file(category, name):
    config = category_config(category)
    if not config:
        return jsonify(error="Unknown category"), 404
    folder, extensions = config
    if not valid_name(name, extensions):
        return jsonify(error="Invalid filename or file type"), 400
    path = folder / name
    if not path.is_file():
        return jsonify(error="File not found"), 404
    path.unlink()
    return jsonify(deleted=name)


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="Upload is larger than 50 MB"), 413


if __name__ == "__main__":
    if not os.environ.get("RECORD_USERNAME") or not os.environ.get("RECORD_PASSWORD"):
        raise SystemExit("Set RECORD_USERNAME and RECORD_PASSWORD before starting")
    app.run(host="127.0.0.1", port=int(os.environ.get("RECORD_PORT", "8090")))
