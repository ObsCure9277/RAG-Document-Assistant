import uuid

from app.chat import SYSTEM_PROMPT, build_grounded_prompt, sse
from app.retrieval import Citation


def test_grounded_prompt_contains_untrusted_evidence_rules_and_bounded_history():
    history = [{"role": "user", "content": str(index)} for index in range(12)]
    citation = Citation(uuid.uuid4(), uuid.uuid4(), "notes.md", 2, "Intro", "evidence", 0.8, 0.2, 0.8)
    prompt = build_grounded_prompt("What is true?", history, [citation])
    assert prompt.messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert len(prompt.messages) == 12
    assert "untrusted" in prompt.messages[-1]["content"]
    assert "[1] notes.md" in prompt.messages[-1]["content"]
    assert str(citation.chunk_id) not in prompt.messages[-1]["content"]


def test_sse_serializes_structured_events():
    output = sse("token", {"text": "hello"})
    assert output.startswith("event: token\ndata:")
    assert output.endswith("\n\n")
