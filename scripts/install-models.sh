#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(<"$PROJECT_DIR/VERSION")"
ASSET="realtime-translator-models-$VERSION.tar.zst"
URL="${1:-${MODEL_BUNDLE_URL:-}}"

if [[ -z "$URL" ]]; then
    ORIGIN="$(git -C "$PROJECT_DIR" remote get-url origin 2>/dev/null || true)"
    if [[ "$ORIGIN" =~ github\.com[:/]([^/]+/[^/.]+)(\.git)?$ ]]; then
        REPOSITORY="${BASH_REMATCH[1]}"
        URL="https://github.com/$REPOSITORY/releases/download/models-$VERSION/$ASSET"
    else
        echo "无法推导模型地址。请传入 Release 资产 URL：" >&2
        echo "  scripts/install-models.sh https://.../$ASSET" >&2
        exit 1
    fi
fi

for dependency in curl tar zstd sha256sum; do
    if ! command -v "$dependency" >/dev/null; then
        echo "缺少系统命令：$dependency" >&2
        exit 1
    fi
done

TEMP_DIR="$(mktemp -d)"
trap 'rm -rf -- "$TEMP_DIR"' EXIT
curl -L --fail --output "$TEMP_DIR/$ASSET" "$URL"
curl -L --fail --output "$TEMP_DIR/$ASSET.sha256" "$URL.sha256"
(
    cd "$TEMP_DIR"
    sha256sum --check "$ASSET.sha256"
    tar --zstd -xf "$ASSET"
    sha256sum --check MODEL_SHA256SUMS
)
mkdir -p "$PROJECT_DIR/models"
cp -a "$TEMP_DIR/models/." "$PROJECT_DIR/models/"
cd "$PROJECT_DIR"
sha256sum --check MODEL_SHA256SUMS
echo "模型安装完成。"
