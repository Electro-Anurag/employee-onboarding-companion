# M6: canonical evidence-backed claim admission — initial implementation

Branch: `feature/eoc-completion-development`. Based on parent SHA `a95a39fa172b09f1ec4aa7f4a8f5c1843cdbc42c`.

The validator previously allowed arbitrary generated answer, clarification,
escalation and limitation prose once citation IDs were valid. The candidate
boundary now admits only one exact server-derived task, active action,
blocked-task, exception status or verified policy edition statement per reply.
Task/action/blocker identity, source scope, context digest and case revision
remain checked. UNSUPPORTED uses a fixed abstention and limitation. Conflict
assertions, policy paraphrases, invented benefits, and other non-canonical
text fail closed. This does not approve or mutate workflow state.

The unchanged developer-labeled 12-example semantic fixture must now reject
all seven intentionally unsupported candidates while admitting four canonical
supported facts and one fixed abstention. Additional adversarial tests cover
unrelated valid citations, injected claims, free-text leakage via secondary
fields, scope, stale version and policy fabrication. CI results and SHA are
not established until the self-hosted workflow runs.

This is **CANDIDATE_ONLY** even after an expected focused PASS; it is not a
proof that a model selects relevant facts for a user's question, nor
independent semantic evaluation. It does not qualify a real external model,
performance, private-data boundaries, usability or hosted J04. No actual
provider call or deployment was authorized. This conservative interface
may abstain on legitimate questions not covered by exact canonical facts.

## Focused verification at exact source revision

Corrected code/test commit: `be72be322ce6e15258f5da574f5ce5686d2d0871` (parent implementation `84c4cd448e974d98450893dcb953103f8f51480e`). Ubuntu ARM64 self-hosted [workflow 38133071154](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38133071154) completed SUCCESS: 24 PostgreSQL AI contract tests, 4 semantic/adversarial tests, 20 React tests, and Vite/TypeScript build passed. Offline labeled examples: 4/4 supported admitted, 0/7 unsupported admitted, 1/1 fixed abstention admitted, verdict **CANDIDATE_ONLY**. Previous run 38133019704 failed in test scaffolding; corrected test fixture and rerun passed. These results do not admit any real provider or hosted journey.
