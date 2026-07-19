#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_PYTHON="${ENGINE_PYTHON:-$PROJECT_DIR/.venv/bin/python3}"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/realtime-translator"
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/realtime-translator.lock"
LOG_FILE="$CACHE_DIR/realtime-translator.log"

if [[ ! -x "$ENGINE_PYTHON" ]]; then
    echo "缺少项目虚拟环境。运行：python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi
LAYER_SHELL_LIB="${GTK4_LAYER_SHELL_LIB:-$($ENGINE_PYTHON -c 'import ctypes.util; print(ctypes.util.find_library("gtk4-layer-shell") or "")')}"
if [[ -z "$LAYER_SHELL_LIB" ]]; then
    echo "缺少 GTK4 layer-shell 动态库。" >&2
    exit 1
fi
cd "$PROJECT_DIR"
if [[ "${1:-}" == "--diagnose" || "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    exec "$ENGINE_PYTHON" main.py "$@"
fi

mkdir -p "$CACHE_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "实时翻译已经在运行。" >&2
    exit 1
fi

echo "[$(date --iso-8601=seconds)] starting" >> "$LOG_FILE"
"$ENGINE_PYTHON" main.py "$@" \
    2> >(tee -a "$LOG_FILE" >&2) | \
    LD_PRELOAD="$LAYER_SHELL_LIB" /usr/bin/python3 overlay.py "$@" \
    2> >(tee -a "$LOG_FILE" >&2)
