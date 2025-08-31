#!/usr/bin/env bash
set -euo pipefail

# Ensure folders exist
mkdir -p "$JOBS_DIR"

# Show Blender version for logs
if [ -x "$BLENDER_BIN" ]; then
  "$BLENDER_BIN" -v || true
else
  echo "Blender binary not found at $BLENDER_BIN" >&2
fi

# Run API/UI
exec uvicorn app.server:app --host "$UVICORN_HOST" --port "$UVICORN_PORT"
