# M6 — Model-answer safety and source relevance

## Scope and capability
This is a *candidate source implementation*, not authorization for live model inference or hosted J04 qualification. `EOC_AI_PROVIDER` remains `DISABLED` on Free Render. No external OpenAI API requests are made by the CI tests. EOC remains a synthetic demo with no private employee data sent to a model.

### Existing, preserved controls

1. `authorized_context` is role-scoped, bounded to a single case and derived from source-validated current case/task/assigned policy state. It excludes identity documents, uploads, private forms, employee emails, reviewer notes, API secrets and unapproved policies.
2. `provider.infer` is opt-in, fixed HTTPS OpenAI Responses endpoint, bounded 16KB context, 650 output tokens, 12-second timeout, 64KB response, JSON schema, `store:false`. Provider output cannot call tools or write onboarding state.
3. The backend audits an inference attempt **before** the external call, with per-user maximum three attempts in rolling 24 hours; transport/refusal/schema/validation failures return `DETERMINISTIC_FALLBACK` and a sanitized audit event, not a fabricated AI answer.
4. `validate_answer` refreshes current authorization/version and only admits exact server-derived canonical facts, one corresponding current source citation, valid action/blocker identity, byte-for-byte short policy quotation, or uniform unsupported abstention. It rejects invented claims, action/citation mismatch and freeform advice.
5. An explicit exact single-edition user request is handled locally by the hash-verified policy reader; the provider is not called or billed.

### New question-to-evidence response admission

Even a true, validly cited fact can be **irrelevant to what the user asked**. `ensure_question_relevance` now runs **after** canonical-source verification and before publishing a model answer. Supported factual answers require exactly one unambiguous, fully matched question of a known kind:
- **Owner**: `Who owns Manager Preparation?`
- **State**: `What is the status of Manager Preparation?`
- **Due**: `When is Manager Preparation due?`
- **Eligible action**: `Can I start Manager Preparation?` (only an actual `START` action for that task)
- **Current blocker**: `Why is Team Introduction blocked?` (only matching exact blocker)
- **Named policy edition**: `Which benefits policy edition is available?`
- **Whole short assigned-policy quote**: `Quote the assigned benefits policy verbatim`; `PARTIAL` with precise limitation only.

The grammar is **deliberately conservative**, not a general language-understanding or semantic entailment solution. Named-task requests must map to a *single* current task; policy requests to the matching authorized edition. Unrelated sources, wrong fact class, bonus/compensation, compound/injected requests, ambiguous policy requests, and unnamed source requests cannot be labeled `SUPPORTED` or `PARTIAL`. A model may return the exact uniform `UNSUPPORTED` abstention instead. Inference failures, including rejection of an unrelated but true fact, are counted and audited.

No question text, provider response body, password, token or document data is persisted as audit evidence. Audit stores only cryptographic digests, source citation IDs, bounded usage and sanitized status.

### Honest evaluation scope and next gates

**Source integration gates** (self-hosted no-billing): Django/PostgreSQL canonical provenance and adversarial relevance tests, malformed provider-envelope/HTTP-error and timeout tests, frontend/production Docker and role-browser integration at an exact commit. Use the current GitHub Actions run verdicts, not code existence, to mark PASS.

**Not yet established:** real provider semantics, real response quality/accuracy metrics from independently labeled prompts, actual provider token usage/billing under an approved synthetic-only account, full-context prompt-injection campaign, live timeout/reliability, or J04 hosted acceptance. Those require explicit owner authorization of provider/API account and any financial cost. Do not set `EOC_AI_PROVIDER=OPENAI` or `OPENAI_API_KEY` in Render without approval. Do not claim the current deterministic fallback is a real model.

**Success condition for hosted J04:** provider opt-in approved and configured privately, real model produces source-grounded and appropriately abstaining answers under a bounded evaluation plan; observable sanitized audit usage and failure handling are confirmed; cross-role/policy isolation, no unintended mutations, and reasonable real-world failure/cost behavior pass. Source-only tests are insufficient.

## M6 final integrated source candidate — 12 October 2026

- [**Full application CI 38180256254**](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38180256254) **PASS** on immutable **`c2e0d8b323fcbb3b7f84ad78bad5a570c38dbd30`**: **253 backend tests PASS, 2 live-storage tests SKIP, 26 frontend tests PASS**, production Docker PASS, compiled frontend assets PASS, real four-role Chromium PASS.
- Earlier [M6 focused new relevance/transport suite 38179953152](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38179953152) **PASS** at `e65cd7936ddb8020ebc441925be0d06ee9da0807`: 60 tests PASS. [Prior M6 established contract suite 38179953115](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38179953115) **PASS**, 36 backend contract, 6 frontend source and 26 React tests. The complete integration run above also covers the newer source.
- **M6 offline source admission/transport hardening: QUALIFIED.** Narrow exact question-to-evidence relevance admission blocks true-but-unrelated canonical answers, and provider transport malformed envelopes fail closed. This remains a deliberately limited task/policy assistant; neither independent real-model semantics nor broad natural-language relevance has been demonstrated.
- **M6 hosted J04: BLOCKED.** No owner approval for paid inference or real external model provider, no live model semantic/adversarial dataset evaluation, no hosted provider cost/reliability evidence. The current Free Render web continues running its older qualified application and `EOC_AI_PROVIDER=DISABLED`; new source commits were NOT deployed. Hosted J01–J05 0/5 complete PASS.
