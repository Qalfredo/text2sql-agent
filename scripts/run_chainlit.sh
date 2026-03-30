#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.13; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "No supported Python found (tried python3.12, python3.11, python3.13)." >&2
  exit 1
fi

if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate

PY_VER=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [ "$PY_VER" != "3.12" ] && [ "$PY_VER" != "3.11" ] && [ "$PY_VER" != "3.13" ]; then
  echo "Unsupported Python in .venv: $PY_VER. Recreate with Python 3.12, 3.11, or 3.13." >&2
  exit 1
fi

# Some local shell setups export DEBUG=release, which Chainlit parses as --debug.
unset DEBUG || true

PORT="${CHAINLIT_PORT:-8001}"

python -m chainlit run app.py -w --headless --port "$PORT"
