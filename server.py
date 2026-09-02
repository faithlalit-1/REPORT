#!/usr/bin/env python3
"""Authenticated web/API server for the RECORD application."""

import hmac
import os
from pathlib import Path, PurePosixPath

from flask import Flask, Response, jsonify, redirect, request, send_file


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


def safe_relative(raw, extensions=None, allow_empty=False):
    """Return a safe POSIX relative path, or None for traversal/invalid input."""
    value = (raw or "").strip().replace("\\", "/").strip("/")
    if not value:
        return PurePosixPath(".") if allow_empty else None
    rel = PurePosixPath(value)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        return None
    if extensions is not None and rel.suffix.lower() not in extensions:
        return None
    return rel


def disk_path(folder, rel):
    path = (folder / Path(*rel.parts)).resolve()
    try:
        path.relative_to(folder.resolve())
    except ValueError:
        return None
    return path


def valid_upload_name(name, extensions):
    return (
        bool(name)
        and name == Path(name).name
        and "/" not in name
        and "\\" not in name
        and "\x00" not in name
        and not any(ord(char) < 32 for char in name)
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
        (path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in extensions),
        key=str.casefold,
    )
    folders = sorted(
        (path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_dir()),
        key=str.casefold,
    )
    return jsonify(files=names, folders=folders)


@app.get("/api/files/<category>/<path:name>")
def download_file(category, name):
    config = category_config(category)
    if not config:
        return jsonify(error="Unknown category"), 404
    folder, extensions = config
    rel = safe_relative(name, extensions)
    if rel is None:
        return jsonify(error="Invalid filename or file type"), 400
    path = disk_path(folder, rel)
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
    target_rel = safe_relative(request.form.get("folder", ""), allow_empty=True)
    if target_rel is None:
        return jsonify(error="Invalid target folder"), 400
    target_folder = disk_path(folder, target_rel)
    if target_folder is None or not target_folder.is_dir():
        return jsonify(error="Target folder does not exist"), 400
    uploaded, skipped, rejected = [], [], []
    for incoming in request.files.getlist("files"):
        original = incoming.filename or ""
        name = original
        if not valid_upload_name(name, extensions):
            rejected.append(original)
            continue
        destination = target_folder / name
        relative_name = destination.relative_to(folder).as_posix()
        if destination.exists() and not replace:
            skipped.append(relative_name)
            continue
        incoming.save(destination)
        uploaded.append(relative_name)
    return jsonify(uploaded=uploaded, skipped=skipped, rejected=rejected)


@app.put("/api/files/<category>/<path:name>")
def update_file(category, name):
    config = category_config(category)
    if not config:
        return jsonify(error="Unknown category"), 404
    folder, extensions = config
    rel = safe_relative(name, extensions)
    if rel is None:
        return jsonify(error="Invalid filename or file type"), 400
    if category not in {"html", "text", "sql"}:
        return jsonify(error="This file type cannot be edited in the browser"), 405
    path = disk_path(folder, rel)
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
    rel = safe_relative(name, extensions)
    if rel is None:
        return jsonify(error="Invalid filename or file type"), 400
    path = disk_path(folder, rel)
    if not path.is_file():
        return jsonify(error="File not found"), 404
    path.unlink()
    return jsonify(deleted=name)


@app.post("/api/folders/<category>")
def create_folder(category):
    config = category_config(category)
    if not config:
        return jsonify(error="Unknown category"), 404
    folder, _extensions = config
    data = request.get_json(silent=True) or {}
    rel = safe_relative(data.get("path"))
    if rel is None:
        return jsonify(error="Invalid folder path"), 400
    path = disk_path(folder, rel)
    if path is None:
        return jsonify(error="Invalid folder path"), 400
    if path.exists() and not path.is_dir():
        return jsonify(error="A file already uses that name"), 409
    path.mkdir(parents=True, exist_ok=True)
    return jsonify(folder=rel.as_posix()), 201


@app.post("/api/move/<category>")
def move_files(category):
    config = category_config(category)
    if not config:
        return jsonify(error="Unknown category"), 404
    folder, extensions = config
    data = request.get_json(silent=True) or {}
    names = data.get("files")
    target_rel = safe_relative(data.get("folder", ""), allow_empty=True)
    target_folder = disk_path(folder, target_rel) if target_rel is not None else None
    if not isinstance(names, list) or not names:
        return jsonify(error="Select at least one file"), 400
    if target_folder is None or not target_folder.is_dir():
        return jsonify(error="Target folder does not exist"), 400

    moves = []
    seen = set()
    destinations = set()
    for name in names:
        if not isinstance(name, str) or name in seen:
            return jsonify(error="Invalid file selection"), 400
        seen.add(name)
        rel = safe_relative(name, extensions)
        source = disk_path(folder, rel) if rel is not None else None
        if source is None or not source.is_file():
            return jsonify(error=f"File not found: {name}"), 404
        destination = target_folder / source.name
        if source == destination:
            continue
        if destination in destinations or destination.exists():
            relative_destination = destination.relative_to(folder).as_posix()
            return jsonify(error=f"A file already exists at {relative_destination}"), 409
        destinations.add(destination)
        moves.append((source, destination))

    moved = []
    for source, destination in moves:
        old_name = source.relative_to(folder).as_posix()
        source.replace(destination)
        moved.append({"from": old_name, "to": destination.relative_to(folder).as_posix()})
    return jsonify(moved=moved)


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="Upload is larger than 50 MB"), 413


if __name__ == "__main__":
    if not os.environ.get("RECORD_USERNAME") or not os.environ.get("RECORD_PASSWORD"):
        raise SystemExit("Set RECORD_USERNAME and RECORD_PASSWORD before starting")
    app.run(host="127.0.0.1", port=int(os.environ.get("RECORD_PORT", "8090")))
