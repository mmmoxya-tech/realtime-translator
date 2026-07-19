#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/.venv"
COMMAND="$HOME/.local/bin/translate"

for dependency in pw-record wpctl flock sha256sum; do
    if ! command -v "$dependency" >/dev/null; then
        echo "缺少系统命令：$dependency" >&2
        exit 1
    fi
done
if ! python3 -c 'import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Gtk4LayerShell", "1.0")' 2>/dev/null; then
    echo "缺少系统组件：GTK4、PyGObject 或 GTK4 layer-shell" >&2
    exit 1
fi
cd "$PROJECT_DIR"
if ! sha256sum --check MODEL_SHA256SUMS; then
    echo "模型缺失或损坏。请先运行：scripts/install-models.sh RELEASE_ASSET_URL" >&2
    exit 1
fi
python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
mkdir -p "$(dirname "$COMMAND")"
ln -sfn "$PROJECT_DIR/translate" "$COMMAND"

echo "安装完成：$COMMAND"
echo "启动：translate"
echo "诊断：translate --diagnose"
