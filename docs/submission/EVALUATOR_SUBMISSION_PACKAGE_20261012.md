# Employee Onboarding Companion — evaluator submission package
**Submission target: 12 October 2026 | Owner: Electro-Anurag | Personal engineering assignment**

> **Submission note:** This document describes the complete product design and the working implementation candidly. A feature in the target experience is not automatically a demonstrated, deployed, tested feature. The code is a living repository; if the evaluator reviews a fixed SHA or downloadable snapshot, later changes will not alter that snapshot. A functioning video and reviewer-accessible GitHub source must be provided at submission time; these cannot be backfilled as if they had existed earlier.

## Project / selected business case

**Track:** AI-powered employee onboarding, operational coordination and governed next-best-action assistance.

A new hire's first days span employee forms, HR evidence approval, IT access, manager readiness, documents, policies, scheduled meetings and training. In fragmented processes, task dependencies and responsibility are hard to see; stakeholders chase updates without a verified source of truth. Employee Onboarding Companion unifies those handoffs into a case-scoped, auditable workflow.

### Full intended user journey

1. **HR** selects a versioned onboarding template, activates a fictional employee case, monitors ownership, due dates, pending evidence, exceptions and handoffs.
2. **Employee** signs in with role-limited visibility, views assigned steps, submits authorized evidence/forms, reads assigned policy editions, and tracks what happens next.
3. **Manager** checks first-week readiness, records required task/meeting/training outcomes and resolves permitted steps while blocked dependencies remain enforced.
4. **IT** receives provisioning tasks, performs **simulated external access-provisioning** actions and records typed evidence/audited outcomes.
5. **HR** reviews evidence, approves or requests correction when allowed, observes blockers/escalations and closes the case only when engine-enforced prerequisites are complete.
6. **Optional AI assistant** receives a bounded, authorized, current-case snapshot for a question. It can propose grounded answers or next actions, but it cannot execute case mutations or invent authorized source citations. A strict server-side gate rejects stale/uncited/irrelevant responses, with an explicitly labeled deterministic fallback.

**Distinctive engineering approach:** deterministic workflow authority + evidence-bounded AI, rather than letting the model become the HR decision-maker. Synthetic HR/IT systems and employees are intentionally used for this evaluation; external live provisioning is not claimed.

### Architecture in brief

React + TypeScript single-origin UI → Django 5.2 APIs with role/case authorization → PostgreSQL authoritative workflow and append-only audit → transactional Procrastinate worker for notifications and retry/recovery. Private storage scanning is gated and does not justify uploading real documents. The optional AI layer is read-only and validates current roles, context digests, allowed facts, citations and task/question relevance before returning any model-produced response. Local Ollama is an experimental model adapter; paid OpenAI is opt-in, never assumed enabled.

Full diagrams, tables and design rationale: [technical design](technical-design.md). Setup and deployment: [README](../../README.md) and [hosting/acceptance](hosting-and-acceptance.md). Requirements: [F01–F28 and E01–E10 traceability](../qualification/d4-requirements-exception-traceability-20261012.md).

## Verification evidence available for the submission baseline

The exact-code **`caf34f2b629f2ad2786b63d63fc0e93844239d7b`** passed:
- [PostgreSQL 17 + Django/React + production Docker build + real four-role Chromium journey](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893788): 271 backend tests passed, 9 skipped; 29 React tests passed.
- [PostgreSQL 18 and populated-migration compatibility](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893843): 271 passed, 9 skipped.
- [Grounded AI/relevance test contracts](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893822): 69 synthetic tests passed; one optional live Ollama test skipped.
- [Focused AI test contracts](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893785): PASS.
- [Earlier actual local Chromium capture](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38235666178): genuine local four-role browser evidence, **not a published narrated YouTube showcase**.

These CI results are historical and exact-SHA-scoped. More recent branch changes must be qualified separately before claimed PASS.

## Working product experience versus next 48-hour qualification

| Feature / evidence | Source/CI baseline today | Target for demo qualification (13–14 Oct, only if later changes may be reviewed) |
| --- | --- | --- |
| HR/Employee/IT/Manager integrated workflow | Role-aware source, local Chromium end-to-end journey passed at baseline | Rehearse one complete persisted fictional case in evaluators' environment, record proof of all important handoffs |
| Templates, policies, task dependencies, audit | Source and regression coverage present | Verify use of the **same case** across all demo screens and explicit prerequisite denial |
| Forms, documents and reviews | Source paths and CI; restricted external storage/scanning | Show only features running on actual demo runtime; label synthetic document paths clearly |
| Background processing | Implementation/tests exist; no continuously running worker on Free Render qualified | Real worker+PostgreSQL scheduling/retry evidence in separately controlled environment |
| Model-generated AI | Mock-contract CI verified; **real model validation NOT YET PASSED** | Complete real `gpt-oss:20b` opt-in case-bound admission; at least one supported cited model answer plus unsupported-claim handling |
| Accessible demo | Existing Render HTTPS address is an **older revision** | Bring demo forward at stable URL if approved; verify actual deployed SHA and login, four roles and persistence |
| Value experiment | Business rationale and measurement protocol documented, no measured before/after | Time real synthetic owner/blocker identification against manual baseline; publish sample size, raw observations and method |
| YouTube demo | Previous short CI browser recording, **not mandatory final upload** | **MANDATORY BY SUBMISSION CUTOFF:** real watchable URL; cannot be represented as published retroactively |
| Personal GitHub | This private repo exists | **MANDATORY BY SUBMISSION CUTOFF:** reviewer must be able to access source without requesting further permission |

**Risk:** The rubric's “no submissions after 12 October” might mean the submitted artifact is evaluated as it existed at cutoff, even if code/hosting changes afterward. Do not assume post-submission commits or replaced videos count. Prioritize a credible, accessible and minimally functional submission package today; subsequent improvements are engineering upgrades, not backdated evidence.

## Engineer-to-evaluator summary (copy/edit after verification)

> **Employee Onboarding Companion** is a full-stack, AI-enabled onboarding coordination system for HR, new hires, managers and IT. It addresses fragmented ownership, pending submissions, blocked prerequisites and first-week readiness through a shared, versioned and role-authorized case workflow. The application uses React, Django, PostgreSQL, transaction-backed background processing, human-controlled approvals and auditable actions. An optional, bounded AI subsystem is designed to answer case-specific questions using only authorized evidence; model-produced output must pass source, relevance and version validation and cannot change workflow state. External HR/IT effects use clearly labeled simulations. The repository includes architecture and deployment documentation, unit and browser tests, and reproducible synthetic walkthroughs.
>
> **Repository:** [PERSONAL GITHUB REPOSITORY ACCESSIBLE TO REVIEWERS]
>
> **Technical design:** [DIRECT LINK TO docs/submission/technical-design.md]
>
> **YouTube demo:** [ACTUAL WORKING YOUTUBE WATCH URL — REQUIRED]
>
> **Hosted experience if available:** [CURRENT VERIFIED URL + DEPLOYED VERSION + KNOWN LIMITATIONS]
>
> **Verification:** [EXACT SHA AND SELECTED GREEN RUN LINKS]. Integration proof is separate from live model/hosting proof; any unqualified runtime feature is explicitly identified in the technical appendix.

Do not replace placeholders with imaginary evidence; do not upload credentials or real HR files. After submission, use a separate development branch for improvement and preserve the submitted reference commit.

## Why this is differentiated

- **Real business workflow**, not a generic HR chatbot; task dependencies, role ownership, human reviews and evidence flow govern the process.
- **Governed AI intervention**, not a freeform model output trusted as operational truth: citations and current-case authorization are independently checked.
- **Recoverability and traceability:** explicit audit, retry and safe failure boundaries, rather than unaudited silent changes.
- **Evaluation-grade engineering:** database migration compatibility, frontend unit tests, Chromium four-role acceptance, and reproducible synthetic fixtures.

## Submission-time finalization checklist

- [ ] Put the correct accessible source branch/commit at the top of GitHub README
- [ ] Verify evaluators can access the personal GitHub repository without asking for permission
- [ ] Upload a genuine demonstration to YouTube and verify its watch URL from an unsigned-in session
- [ ] Include an actual technical-design diagram/document and setup/deployment instructions
- [ ] Link the best exact-SHA test runs and make exclusions clear
- [ ] Provide the hosted URL only if it genuinely works for the described experience
- [ ] Enter the actual submission confirmation/receipt and submission timestamp into private tracking

**This document is not proof of a completed submission.**
