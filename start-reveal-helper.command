#!/bin/bash
# Double-click this file to start the RECORD "Go" helper (macOS).
cd "$(dirname "$0")" || exit 1
echo "Starting RECORD reveal helper…"
python3 reveal-helper.py
