# M6 bounded offline policy retrieval — implementation candidate

Base: `d5de797df0faf5c1a0a7da2ec1c389e922d1512b`. Active branch: `feature/eoc-completion-development`.

The current answer endpoint previously discarded a legitimate explicit policy
request when the optional external-model provider was not configured. It returned
only generic deterministic task guidance despite an already authorized, verified
policy text being available. This change adds a zero-cost, **non-AI** answer
path while keeping the same HTTP endpoint, no external calls, and no workflow
actions. It accepts only complete, unambiguous explicit requests for a single
assigned conduct/privacy/benefits policy; any extra clause or unsupported
question goes to existing guidance fallback. It maps the requested policy key
to the task's authorized `POLICY:<task-id>:<digest-prefix>` source, creates the
entire canonical full-edition quotation (never an excerpt), and re-runs the
existing validator against a refreshed snapshot before publication. The mode
`DETERMINISTIC_SOURCE_ANSWER` has `ai_model_used=false`. The UI renders the
same citations but labels it correctly as a verified source, not model output.

Role scope is unchanged: Employee and HR may view their assigned editions,
IT and Manager never receive policy body, cross-case reads remain forbidden.
No provider quotas/audit events are incurred; no new data is sent elsewhere.
Missing, ambiguous, stale, too-long and modified requests fail closed.
This is not semantic question answering, real-model safety qualification, or
an authorization to deploy. Prior queued policy-quotation run 38146123757
at `6481876a...` is NOT yet PASS; source-level tests for this slice will
require their own exact-SHA CI execution.

Adversarial tests cover ambiguous requests, unauthorized roles, nonexistent
policy, fabricated monetary claim, source text integrity and stale context.
Actual runtime or browser validation is pending.
