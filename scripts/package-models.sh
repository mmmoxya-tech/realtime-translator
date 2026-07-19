#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(<"$PROJECT_DIR/VERSION")"
ASSET="realtime-translator-models-$VERSION.tar.zst"
OUTPUT_DIR="${1:-$PROJECT_DIR/dist}"

cd "$PROJECT_DIR"
sha256sum --check MODEL_SHA256SUMS
mkdir -p "$OUTPUT_DIR"
tar --zstd -cf "$OUTPUT_DIR/$ASSET" models MODEL_SHA256SUMS
(
    cd "$OUTPUT_DIR"
    sha256sum "$ASSET" > "$ASSET.sha256"
)
echo "模型资产：$OUTPUT_DIR/$ASSET"
echo "校验文件：$OUTPUT_DIR/$ASSET.sha256"
