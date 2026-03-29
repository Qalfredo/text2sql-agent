#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "python3.12 not found. Install Python 3.12 first." >&2
  exit 1
fi

if [ ! -d .venv ]; then
  python3.12 -m venv .venv
fi

source .venv/bin/activate

PY_VER=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [ "$PY_VER" != "3.12" ] && [ "$PY_VER" != "3.11" ]; then
  echo "Unsupported Python in .venv: $PY_VER. Recreate with Python 3.12." >&2
  exit 1
fi

python -m chainlit run app.py -w
