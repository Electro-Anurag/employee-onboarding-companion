# M6 adversarial answer provenance evaluation — offline contract qualification

Scope: `backend/ai/validator.py`, `backend/ai/tests/test_provenance.py`. This is an offline, mocked-provider and PostgreSQL-backed adversarial evaluation; no user data, external model invocation, expense or autonomous write is permitted.

## Fixed evaluation objectives

- Only exact currently authorized case source IDs may be cited.
- A proposed eligible task action must cite the specific corresponding `TASK:<task_id>`, not an unrelated but otherwise valid source.
- A reported blocked task must cite its own `TASK:<task_id>` source, not an unrelated task.
- Partial answers must disclose a nonblank limitation; abstentions remain fail-closed with explanatory limitations.
- Context changes and role-specific policy access must not be bypassed.
- On deliberately rejected model output, fall back to deterministic guidance with sanitized failure audit and without task completion.

The test code contains the explicit expected accept/reject outcomes. Exact GitHub Actions results must be recorded after execution; source changes alone are not a PASS.

## Limitations and release gates

Citation-to-task ID consistency is **not** natural-language entailment or factuality. A model could still attach the correct source to an unsupported free-form claim. These tests cannot establish model accuracy, retrieval relevance, resistance to all prompt injection, latency, cost, or real hosted J04. Separate labeled semantic cases reviewed against full source facts, real-provider admission after owner approval, private data review, Chromium multi-role acceptance, and hosted J01–J05 remain mandatory. Until they are complete, describe model output as structurally and provenance validated, not independently fact-checked.
