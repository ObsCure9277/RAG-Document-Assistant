# 06: Grounded streaming chat

**What to build:** A user can hold persistent conversations and receive streamed, grounded answers with citations through the React chat experience.

**Blocked by:** 05 — Hybrid retrieval and citations

**Status:** ready-for-agent

- [ ] Users can create conversations and load persisted message history.
- [ ] A message endpoint rewrites follow-up questions using bounded recent history.
- [ ] Retrieval evidence and a bounded conversation window are sent to the answer model.
- [ ] Answers stream from FastAPI over Server-Sent Events.
- [ ] The prompt requires evidence-only answers, explicit uncertainty, conflict reporting, and resistance to document prompt injection.
- [ ] User messages and completed assistant messages are persisted.
- [ ] Interrupted responses are marked incomplete.
- [ ] The UI renders streamed text, citations, insufficient-evidence responses, and optional document filters.
- [ ] Chat API and UI tests verify grounding, streaming, persistence, and citation behavior.
