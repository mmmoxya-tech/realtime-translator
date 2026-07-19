from __future__ import annotations

import json
from pathlib import Path


class Terminology:
    """Apply optional, ordered literal corrections to translated text."""

    def __init__(self, paths=()):
        self.rules: list[tuple[str, str]] = []
        for configured_path in paths or ():
            path = Path(configured_path)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"无法读取术语配置 {path}：{exc}") from exc
            if not isinstance(data, dict) or not all(
                    isinstance(source, str) and source and
                    isinstance(target, str)
                    for source, target in data.items()):
                raise RuntimeError(
                    f"术语配置 {path} 必须是非空字符串到字符串的 JSON 对象")
            self.rules.extend(data.items())

    def apply(self, text: str) -> str:
        for source, target in self.rules:
            text = text.replace(source, target)
        return text
