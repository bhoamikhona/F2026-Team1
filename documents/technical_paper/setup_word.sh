#!/bin/sh
# Run once on macOS or Linux to install the Word export dependency.
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-word.txt
.venv/bin/python -c 'from docx import Document; print("Word exporter is ready.")'
