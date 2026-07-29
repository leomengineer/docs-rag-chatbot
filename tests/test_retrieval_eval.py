"""Integration tests for retrieval eval harness (requires Postgres + ingested docs)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.metrics import run_eval
from rag import db

CASES_PATH = Path(__file__).resolve().parent.parent / "eval" / "retrieval_cases.json"


def _db_ready() -> bool:
    try:
        db.fetchall("SELECT 1")
        rows = db.fetchall("SELECT COUNT(*) AS n FROM chunks")
        return rows and rows[0]["n"] > 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_ready(), reason="Postgres not running or docs not ingested")


@pytest.fixture(scope="module")
def cases():
    return json.loads(CASES_PATH.read_text())


def test_retrieval_hit_rate(cases):
    report = run_eval(cases, k=5)
    assert report.hit_at_k >= 0.85, format_misses(report)


def test_retrieval_gate_accuracy(cases):
    report = run_eval(cases, k=5)
    assert report.gate_accuracy >= 0.85, format_misses(report)


def test_out_of_scope_refused(cases):
    report = run_eval(cases, k=5)
    assert report.out_of_scope_gate_accuracy >= 1.0, format_misses(report)


def format_misses(report):
    lines = [
        f"hit@{report.k}={report.hit_at_k:.1%} gate={report.gate_accuracy:.1%}",
    ]
    for r in report.results:
        if not r.gate_correct or (not r.should_refuse and not r.hit):
            lines.append(f"  {r.case_id}: expected={sorted(r.expected)} got={r.retrieved}")
    return "\n".join(lines)
