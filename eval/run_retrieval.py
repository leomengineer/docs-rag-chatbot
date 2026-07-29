#!/usr/bin/env python3
"""Run retrieval eval against labeled Q&A cases and print precision/recall metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from eval.metrics import format_report, run_eval

CASES_PATH = Path(__file__).resolve().parent / "retrieval_cases.json"


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Evaluate hybrid retrieval on labeled Q&A cases.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=CASES_PATH,
        help="Path to retrieval_cases.json",
    )
    parser.add_argument("-k", type=int, default=5, help="Top-k chunks to retrieve")
    parser.add_argument(
        "--min-hit-rate",
        type=float,
        default=None,
        help="Exit 1 if in-scope hit@k falls below this threshold (e.g. 0.9)",
    )
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    report = run_eval(cases, k=args.k)
    print(format_report(report))

    if args.min_hit_rate is not None and report.hit_at_k < args.min_hit_rate:
        print(
            f"\nFAIL: hit@{args.k} {report.hit_at_k:.1%} < {args.min_hit_rate:.1%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
