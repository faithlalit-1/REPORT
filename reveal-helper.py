#!/usr/bin/env python3
"""Tiny localhost helper for RECORD's "Go" button.

The browser cannot open Finder/Explorer by itself, so record.html pings this
small server, which reveals (and selects) the file in the native file manager:
  - macOS   -> open -R <file>     (Finder)
  - Windows -> explorer /select,  (File Explorer)
  - Linux   -> xdg-open <folder>  (no universal "select")

Run it from the RECORD folder and leave the window open:
    python3 reveal-helper.py
Then use the Go button in record.html. Press Ctrl+C to stop.

Safety: only paths inside this RECORD folder can be revealed, and it only ever
"reveals" files (it never opens/executes them).
"""
import os
import platform
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# On Windows the console defaults to a legacy code page (e.g. cp1252) that
# cannot encode non-ASCII characters. The RECORD folder name contains emoji,
# so printing its path would crash with UnicodeEncodeError. Force UTF-8 output
# (and never crash on a stray character) on every platform.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

PORT = 47615
ROOT = os.path.dirname(os.path.abspath(__file__))


def reveal(path):
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", "-R", path], check=False)
    elif system == "Windows":
        # Use the full path to explorer.exe: the Microsoft Store build of Python
        # can't resolve a bare "explorer" on its search path (raises WinError 2).
        explorer = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "explorer.exe")
        subprocess.run([explorer, "/select,", os.path.normpath(path)], check=False)
    else:
        target = path if os.path.isdir(path) else os.path.dirname(path)
        subprocess.run(["xdg-open", target], check=False)


def _inside_root(path):
    try:
        return os.path.commonpath([ROOT, path]) == ROOT
    except ValueError:
        return False


class Handler(BaseHTTPRequestHandler):
    def _send(self, code=200, body=b"ok"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/ping":
            return self._send(200, b"record-reveal-helper")
        if parsed.path != "/reveal":
            return self._send(404, b"not found")
        raw = (urllib.parse.parse_qs(parsed.query).get("path") or [""])[0]
        path = os.path.abspath(raw)
        if not _inside_root(path):
            return self._send(403, b"path outside RECORD folder")
        if not os.path.exists(path):
            return self._send(404, b"file not found")
        try:
            reveal(path)
            return self._send(200, b"revealed")
        except Exception as exc:  # noqa: BLE001
            return self._send(500, str(exc))

    def log_message(self, *args):  # keep the console quiet
        pass


if __name__ == "__main__":
    print("RECORD reveal helper running at http://127.0.0.1:%d" % PORT)
    print("Watching folder: %s" % ROOT)
    print("Leave this window open, then use the Go button in record.html. Ctrl+C to stop.")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
