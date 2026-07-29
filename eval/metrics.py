"""Retrieval eval metrics for labeled Q&A cases."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from rag.answer import SIMILARITY_FLOOR
from rag.retrieve import hybrid_search


@dataclass
class CaseResult:
    case_id: str
    question: str
    expected: set[str]
    retrieved: list[str]
    hit: bool
    recall: float
    precision: float
    reciprocal_rank: float
    best_dense: float
    should_refuse: bool
    gate_refused: bool
    gate_correct: bool


@dataclass
class EvalReport:
    k: int
    similarity_floor: float
    results: list[CaseResult] = field(default_factory=list)

    @property
    def in_scope(self) -> list[CaseResult]:
        return [r for r in self.results if not r.should_refuse]

    @property
    def out_of_scope(self) -> list[CaseResult]:
        return [r for r in self.results if r.should_refuse]

    @property
    def recall_at_k(self) -> float:
        scoped = self.in_scope
        if not scoped:
            return 0.0
        return sum(r.recall for r in scoped) / len(scoped)

    @property
    def precision_at_k(self) -> float:
        scoped = [r for r in self.in_scope if r.retrieved]
        if not scoped:
            return 0.0
        return sum(r.precision for r in scoped) / len(scoped)

    @property
    def hit_at_k(self) -> float:
        scoped = self.in_scope
        if not scoped:
            return 0.0
        return sum(1 for r in scoped if r.hit) / len(scoped)

    @property
    def mrr(self) -> float:
        scoped = self.in_scope
        if not scoped:
            return 0.0
        return sum(r.reciprocal_rank for r in scoped) / len(scoped)

    @property
    def gate_accuracy(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.gate_correct) / len(self.results)

    @property
    def in_scope_gate_accuracy(self) -> float:
        scoped = self.in_scope
        if not scoped:
            return 0.0
        return sum(1 for r in scoped if r.gate_correct) / len(scoped)

    @property
    def out_of_scope_gate_accuracy(self) -> float:
        scoped = self.out_of_scope
        if not scoped:
            return 0.0
        return sum(1 for r in scoped if r.gate_correct) / len(scoped)


def _reciprocal_rank(retrieved: list[str], expected: set[str]) -> float:
    for rank, filename in enumerate(retrieved, start=1):
        if filename in expected:
            return 1.0 / rank
    return 0.0


def evaluate_case(case: dict, k: int = 5, similarity_floor: float | None = None) -> CaseResult:
    floor = similarity_floor if similarity_floor is not None else SIMILARITY_FLOOR
    question = case["question"]
    expected = set(case.get("expected_filenames") or [])
    should_refuse = bool(case.get("should_refuse", False))

    chunks, best_dense = hybrid_search(question, k=k)
    retrieved = [c["source_filename"] for c in chunks]
    retrieved_unique = list(dict.fromkeys(retrieved))

    hits = expected.intersection(retrieved_unique)
    recall = len(hits) / len(expected) if expected else 0.0
    precision = len(hits) / len(retrieved_unique) if retrieved_unique else 0.0
    gate_refused = best_dense < floor or not chunks

    return CaseResult(
        case_id=case["id"],
        question=question,
        expected=expected,
        retrieved=retrieved_unique,
        hit=bool(hits),
        recall=recall,
        precision=precision,
        reciprocal_rank=_reciprocal_rank(retrieved, expected),
        best_dense=best_dense,
        should_refuse=should_refuse,
        gate_refused=gate_refused,
        gate_correct=gate_refused == should_refuse,
    )


def run_eval(cases: list[dict], k: int = 5, similarity_floor: float | None = None) -> EvalReport:
    floor = similarity_floor if similarity_floor is not None else SIMILARITY_FLOOR
    report = EvalReport(k=k, similarity_floor=floor)
    for case in cases:
        report.results.append(evaluate_case(case, k=k, similarity_floor=floor))
    return report


def format_report(report: EvalReport) -> str:
    lines = [
        f"Retrieval eval (k={report.k}, similarity_floor={report.similarity_floor})",
        "",
        "Aggregate metrics",
        f"  Hit@{report.k} (in-scope):     {report.hit_at_k:.1%}  ({sum(1 for r in report.in_scope if r.hit)}/{len(report.in_scope)} cases)",
        f"  Recall@{report.k} (in-scope):  {report.recall_at_k:.1%}",
        f"  Precision@{report.k} (in-scope): {report.precision_at_k:.1%}",
        f"  MRR (in-scope):            {report.mrr:.3f}",
        f"  Gate accuracy (all):       {report.gate_accuracy:.1%}  ({sum(1 for r in report.results if r.gate_correct)}/{len(report.results)} cases)",
        f"    in-scope gate:           {report.in_scope_gate_accuracy:.1%}",
        f"    out-of-scope gate:       {report.out_of_scope_gate_accuracy:.1%}",
        "",
        "Per-case results",
    ]

    for r in report.results:
        status = "OK" if (r.hit or r.should_refuse) and r.gate_correct else "MISS"
        if r.should_refuse:
            detail = f"gate={'refuse' if r.gate_refused else 'answer'} dense={r.best_dense:.3f}"
        else:
            top = r.retrieved[0] if r.retrieved else "—"
            detail = f"top={top} hit={r.hit} dense={r.best_dense:.3f}"
        lines.append(f"  [{status}] {r.case_id}: {detail}")

    misses = [r for r in report.results if not ((r.hit or r.should_refuse) and r.gate_correct)]
    if misses:
        lines.append("")
        lines.append("Misses")
        for r in misses:
            lines.append(f"  {r.case_id}: expected={sorted(r.expected)} got={r.retrieved}")

    return "\n".join(lines)
