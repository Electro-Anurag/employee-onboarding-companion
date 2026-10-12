# 12 October 2026 — mandatory AI and submission evidence packet

**Status: DRAFT / NOT SUBMITTED.** This file implements the owner's latest written competition instructions. **Submission cutoff: 12 October 2026; specific cutoff hour/timezone unknown. YouTube demo URL is MANDATORY. Hosting URL is OPTIONAL (if hosted, include it).** Do not submit an invented YouTube URL, fabricated metrics or a private GitHub link inaccessible to reviewers.

## 1. Project identity and judged value

**Selected business case:** Employee onboarding coordination across Employee, HR, IT and Manager.

**Business problem:** approvals, missing evidence, assignment handoffs, policy questions and scheduled activities are fragmented across owners; manual follow-up can hide blockers. The companion preserves an authoritative case, role-specific next steps, workflow dependencies and audit, with optional evidence-grounded model answers. Simulated external IT actions must be clearly identified.

**AI intervention (real-model candidate):** an explicit read-only, current-case question goes through role-authorized context assembly, local Ollama model inference, exact citation and question-relevance checks, failure fallback and sanitized audit. A deterministic policy quote or fallback is **not AI-generated**. Successful unit tests with mocked model responses do **not** prove a real model invocation.

## 2. Current verified engineering proof (no hosted claims)

Code/test revision **`caf34f2b629f2ad2786b63d63fc0e93844239d7b`**:

| Evidence | Exact run | Verified |
| --- | --- | --- |
| PostgreSQL 17, frontend, Docker, Chromium integration | [38262893788](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893788) | PASS — 271 Django tests, nine skips, 29 React tests, production Docker build, real four-role Chromium |
| PostgreSQL 18 and populated migrations | [38262893843](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893843) | PASS — 271 Django tests, nine skips, four populated migration histories |
| Focused AI schema/citations/authorization | [38262893785](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893785) | PASS — 36 Django, six additional and 29 React checks |
| Grounded answer contract | [38262893822](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893822) | PASS — 69 synthetic tests, one **real-Ollama test skipped** |
| Prior real UI screen capture | [38235666178](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38235666178) | Genuine local browser recording / eight screenshots; not a completed submission video |

The application may have more recent script/doc commits; **do not relabel these exact CI runs as passing at a later SHA**. They establish the application source at the specific revision above. The existing Render Free deployment is older and was not verified on this SHA.

## 3. Generate *real* AI proof — blocking action

On a machine with Docker, uv, Python, and an **already installed and serving** local Ollama model:

```bash
git switch feature/eoc-completion-development
git pull --ff-only
ollama list
EOC_OLLAMA_MODEL='gpt-oss:20b' bash scripts/run_evaluation_real_ai.sh
```

Replace `gpt-oss:20b` with a **verified installed model name**, not a guessed model. The script intentionally refuses `DATABASE_URL`, paid-provider mode, uncommitted tracked changes, missing Ollama, or unavailable Docker; creates and destroys only a disposable PostgreSQL container, records the real test output privately under the local temporary directory, and never pulls an additional model automatically. Its runtime has not been qualified on the owner's machine.

**Acceptance:** the real `backend/ai/tests/test_ollama_live_synthetic.py` test completes with explicit `MODEL_VALIDATED` + `ai_model_used=true` for at least one one-fact task answer with one citation, three logged model attempts, no mutating task completion, and safe handling of a bonus-guarantee question. If that question falls back, describe a **system-level refusal**, not a successful model-generated refusal. A passing test does not prove every policy question works or that hosted AI is enabled.

**Record privately:** model name/version, source SHA, local-only runtime, date, test PASS/FAIL, successful generated-answer type, citations count and any observed fallback. Record a short *actual screen capture* of the running application's model answer if feasible. A CLI test log is technical evidence, not a substitute for showing the actual app/user experience. Never show passwords, tokens, real employee records or raw secret files.

If the real inference fails, **report the failure and resulting limitation explicitly**; do not quietly label deterministic results as AI. Without at least one genuine AI response, the written requirement to demonstrate an AI-powered app remains a material elimination risk.

## 4. Produce required YouTube demo — blocking action

Capture real, unedited application interactions, ideally 4–7 minutes. Proposed outline (these are **instructions**, not a claim that the recording exists):

1. **Problem (0:00–0:30):** selected case, who struggles, intended measurable outcome.
2. **Working four-role journey (0:30–2:30):** HR publishes/activates fictional case; Manager records real typed evidence; Employee views/submits; IT demonstrates explicitly simulated external provisioning. Show persisted progress/dependency or HR review where accessible.
3. **Model inference (2:30–3:45):** one actual authorized case question with `MODEL_VALIDATED`, cited source and owner/status; an unsupported question with verified abstention or transparent fail-closed fallback. Show human authority boundary. If only a local model works, disclose that this portion is the local demo, not hosted Render.
4. **Business evidence (3:45–4:30):** a real blocker/owner handoff, and one measured before/after microexperiment below. No invented savings.
5. **Engineering (4:30–5:30):** architecture diagram, source/test SHA, real CI, limitations; point to GitHub documentation.

**Before upload:** verify that the video plays and audio is audible, captions/narration are intelligible, accounts/secrets are masked, any source labels are accurate, and the YouTube visibility allows evaluators to watch (Unlisted can provide link access). **Publishing/uploading is the owner's decision and action.** Copy the actual watch URL into the final submission after successfully verifying it. No video URL has been observed.

## 5. Measurable value — small, honest experiment

**Suggested low-cost protocol:** with fictional data, ask a tester to find the current owner and blocker of three predefined tasks using (A) a baseline manually curated task handoff list and (B) the working companion UI. Keep the same facts in both conditions and rotate task order to minimize learning effects.

Measure `seconds_to_identify_owner`, `correct_owner_out_of_3`, `correct_blocker_out_of_3`, method, timestamps and sample size. Show the actual raw observations and explicitly call the sample an illustrative evaluation rather than a production benchmark. Without observations, list this as a proposed metric, **not** measured value.

| Metric | Manual baseline | Companion | Evidence |
| --- | --- | --- | --- |
| Median time to identify owner | NOT MEASURED | NOT MEASURED | No timing log yet |
| Correct owners | NOT MEASURED | NOT MEASURED | No observation yet |
| Correct blockers | NOT MEASURED | NOT MEASURED | No observation yet |

## 6. Submission manifest — fill only with verified links

| Required artifact | Current value/status |
| --- | --- |
| Personal GitHub source | `https://github.com/Electro-Anurag/employee-onboarding-companion` — **PRIVATE; evaluator access NOT established** |
| Reference revision/branch | `feature/eoc-completion-development`; mark final immutable SHA after evidence finishes |
| Architecture/flow diagrams | [technical design](technical-design.md) — exists, final check pending |
| Setup/deploy | [README](../../README.md) and [hosting runbook](hosting-and-acceptance.md) — exists |
| Code explanation / assumptions | [technical design](technical-design.md) and [evaluation contract](evaluation-first-delivery-contract-20261012.md) — exists |
| Comprehensive unit test proof | Four exact-SHA CI links above — PASS within their tested scopes |
| Live model evidence | **MISSING** until opt-in real Ollama run passes |
| Actual YouTube demo watch URL | **MISSING — mandatory elimination risk** |
| Optional hosted app | `https://eoc-companion-web.onrender.com` — older deployment, limitations must be disclosed; hosting is optional under latest rubric |
| Reviewer-independent repository access | **MISSING** while repository stays private without authorized evaluator access |
| Final submission receipt/time | **MISSING** — no submission action evidenced |

**Do not submit or publish automatically.** Source access may require an approved sanitized public release or other reviewer-access mechanism that does not prompt evaluators for permissions. Decide this with the owner; do not expose a private company asset or change repository visibility silently.

## 7. Submission exit

A valid submission requires all three: (1) an accessible personal GitHub repository with required documentation/tests; (2) **a real, viewable YouTube demo URL**, not the local CI .webm; and (3) a demonstrated functioning business application with credible actual AI and measured/observable value. Optional hosted URL should be included only with accurate version/limitation disclosures.

As of this packet creation: **code verification strong; live AI absent; YouTube URL absent; reviewer source access unresolved; NOT READY TO SUBMIT**.
