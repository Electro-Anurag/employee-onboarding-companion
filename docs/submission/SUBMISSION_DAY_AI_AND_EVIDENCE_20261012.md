> **Update 12 October 2026 — Mac PostgreSQL STOP, proven log boundary:** `postgresql@17` Homebrew installation on macOS 27 lacks `dict_snowball.so` and `plpgsql.so`; `initdb` cannot complete. **Do not rerun the Mac `scripts/run_evaluation_real_ai.sh` or repair symlinks further.** Model `gpt-oss:20b` works on Mac Ollama 0.35.1. Use [the owner-opt-in ARM64 PostgreSQL real-model gate](../../.github/workflows/eoc-real-ollama-admission.yml) with **an SSH reverse tunnel on loopback** from macOS Ollama to the already-qualified private Ubuntu ARM64 self-hosted runner. This preserves real model inference on Mac and database/application execution on Ubuntu, with no Docker, Postgres service, or paid model on Mac. No model PASS has yet been observed. The earlier Docker/Homebrew command below is kept for historical reproducibility only.

## Current preferred owner-executed real-AI route (no Mac PostgreSQL)

**One-time prerequisite:** the owner's existing SSH login into Ubuntu runner as `ecoci` must work from the Mac. The SSH server must permit remote TCP forwarding; the port `11434` must be unused on Ubuntu. All traffic remains over SSH; Ollama is served on macOS `127.0.0.1:11434` and exposed only as Ubuntu `127.0.0.1:11434`, never on a public interface. Keep the Mac running and awake for the qualification.

In **Mac Terminal A**, open the tunnel using the exact hostname/SSH option normally used to log into Ubuntu; if the hostname `eco-ci` is resolvable, the command is:

```bash
ssh -o ExitOnForwardFailure=yes -N \\
  -R 127.0.0.1:11434:127.0.0.1:11434 \\
  ecoci@eco-ci
```

The shell appears idle while the SSH tunnel is open. Leave it open. With a second Mac Terminal verify through the same SSH destination:

```bash
ssh ecoci@eco-ci \\
  'curl -fsS --max-time 10 http://127.0.0.1:11434/api/version'
```

If the SSH host is not `eco-ci` use the actual existing private SSH destination; **do not** expose Ollama on `0.0.0.0` or open internet ports. If SSH forwarding fails, stop and report the exact error.

In **Mac Terminal B**, inside this GitHub repository and after `git pull --ff-only`, explicitly trigger the owner-only job (creates a text marker but no secrets):

```bash
cd ~/eoc-ai-demo
git pull --ff-only
date -u '+%Y-%m-%dT%H:%M:%SZ' > docs/submission/real_ollama_trigger.txt
git add docs/submission/real_ollama_trigger.txt
git commit -m 'eval(real-ai): run owner-approved SSH-tunneled Ollama admission'
git push origin feature/eoc-completion-development
```

Only a commit touching the marker with the `eval(real-ai):` prefix runs the true inference test on self-hosted Ubuntu CI. The workflow file creation itself does NOT initiate paid/real model calls. The job uses its own ephemeral PostgreSQL 17 service, fixed Ollama loopback `11434`, `gpt-oss:20b`, and the same `backend/ai/tests/test_ollama_live_synthetic.py` gate. Inspect GitHub Actions workflow **EOC owner-opt-in REAL Ollama admission (PostgreSQL ARM64)** and retain the run URL and exact source SHA. PASS is valid only when the real test says `EOC_REAL_OLLAMA_THREE_QUESTION_ADMISSION_PASS@` and the log shows at least one `MODEL_VALIDATED` supported fact. Stop the tunnel with Ctrl+C afterward.

**Model result is not yet observed.** If a supported question yields only deterministic fallback, report a genuine failed qualification and investigate provider schema/relevance rather than claiming AI success.

---

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

On a Mac with uv, Python, Homebrew PostgreSQL 17 (or an already running local Docker daemon), and an **already installed and serving** local Ollama model:

```bash
git switch feature/eoc-completion-development
git pull --ff-only
ollama list
EOC_OLLAMA_MODEL='gpt-oss:20b' bash scripts/run_evaluation_real_ai.sh
```

Replace `gpt-oss:20b` with a **verified installed model name**, not a guessed model. **Docker is optional**: if no functioning Docker daemon exists, first run `brew install postgresql@17`; the runner starts its own temporary SCRAM-authenticated loopback-only PostgreSQL 17 cluster and stops/deletes it automatically. With Docker it uses a disposable container instead. It refuses `DATABASE_URL`, paid-provider mode, uncommitted tracked changes or missing Ollama, records the real test output privately under a temporary evidence directory, and never pulls another model automatically. It does **not** use an existing PostgreSQL service/database. Its real-model runtime has not been qualified on the owner's machine.

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
