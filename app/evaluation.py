from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class EvaluationCase:
    question: str
    expected_documents: frozenset[str]
    expected_chunks: frozenset[str]


def load_golden_dataset(path: Path) -> list[EvaluationCase]:
    return [
        EvaluationCase(row["question"], frozenset(row.get("expected_documents", [])), frozenset(row.get("expected_chunks", [])))
        for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    ]


def retrieval_recall(expected: set[str], retrieved: set[str]) -> float:
    return 1.0 if expected and expected <= retrieved else 0.0


def citation_accuracy(expected_chunks: set[str], cited_chunks: set[str]) -> float:
    return len(expected_chunks & cited_chunks) / len(cited_chunks) if cited_chunks else 0.0


def faithfulness(answer: str, evidence: str) -> float:
    """Offline proxy: evidence overlap, intended for trend tracking not truth adjudication."""
    answer_terms = {term.lower() for term in answer.split() if len(term) > 3}
    evidence_terms = {term.lower() for term in evidence.split() if len(term) > 3}
    return len(answer_terms & evidence_terms) / len(answer_terms) if answer_terms else 0.0


def estimated_openai_cost(input_tokens: int, output_tokens: int, input_price_per_million: float = 0.15, output_price_per_million: float = 0.60) -> float:
    return round(input_tokens * input_price_per_million / 1_000_000 + output_tokens * output_price_per_million / 1_000_000, 8)
