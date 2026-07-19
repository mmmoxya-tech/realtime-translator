#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from rttranslate.translator import LocalTranslator  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glossary", action="append", default=[])
    args = parser.parse_args()
    samples = json.loads(
        (PROJECT / "benchmarks/translation_samples.json").read_text())
    translator = LocalTranslator(glossary_paths=args.glossary)
    translator.warmup()
    durations = []
    print("domain\tlatency_ms\tsource\ttranslation\treference")
    for sample in samples:
        started_at = time.perf_counter()
        translated = translator.translate(sample["source"])
        duration = (time.perf_counter() - started_at) * 1000
        durations.append(duration)
        print(
            f'{sample["domain"]}\t{duration:.1f}\t{sample["source"]}\t'
            f'{translated}\t{sample["reference"]}'
        )
    ordered = sorted(durations)
    p95_index = min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))
    print(
        f"samples={len(durations)} mean_ms={statistics.mean(durations):.1f} "
        f"p95_ms={ordered[p95_index]:.1f} max_ms={max(durations):.1f}"
    )


if __name__ == "__main__":
    main()
