# 07: Reliability and evaluation

**What to build:** The complete personal assistant is observable, resilient, and measurable against a representative document-question dataset.

**Blocked by:** 04 — Document lifecycle controls; 06 — Grounded streaming chat

**Status:** ready-for-agent

- [ ] Structured logs include document/version/job identifiers, step durations, counts, retries, retrieval statistics, and chat latency.
- [ ] Logs do not contain API keys or raw document text by default.
- [ ] File, page/token, concurrency, context, timeout, retry, and history limits are configurable.
- [ ] Transient OpenAI failures use bounded exponential backoff.
- [ ] Docker restart and migration tests verify data persistence and recoverability.
- [ ] A 30–50 question golden dataset records expected supporting documents or chunks.
- [ ] Evaluation records retrieval recall, citation accuracy, answer faithfulness, latency, and OpenAI cost.
- [ ] API, worker, retrieval, and chat tests pass together as a release gate.
