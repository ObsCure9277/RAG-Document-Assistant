from pathlib import Path

import pytest

from app.evaluation import citation_accuracy, estimated_openai_cost, faithfulness, load_golden_dataset, retrieval_recall
from app.reliability import retry_async


def test_golden_dataset_has_representative_questions():
    cases = load_golden_dataset(Path("evaluation/golden.jsonl"))
    assert len(cases) == 30


def test_evaluation_metrics_are_bounded():
    assert retrieval_recall({"a"}, {"a", "b"}) == 1.0
    assert citation_accuracy({"a"}, {"a", "b"}) == 0.5
    assert 0 < faithfulness("known fact", "known fact from evidence") <= 1
    assert estimated_openai_cost(1000, 500) == 0.00045


@pytest.mark.asyncio
async def test_retry_async_uses_bounded_attempts():
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("transient")
        return "ok"

    assert await retry_async(operation, attempts=3, base_delay=0, max_delay=0) == "ok"
    assert calls == 3
