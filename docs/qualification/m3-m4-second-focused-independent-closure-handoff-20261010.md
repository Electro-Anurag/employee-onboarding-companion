# Employee Onboarding Companion — M3–M4 Second Focused Independent Closure Handoff

**Created:** 2026-10-10 IST. **Developer handoff only — independent approval not claimed.**

## Exact source identity
- Authorized private repository/account: `Electro-Anurag/employee-onboarding-companion` / `Electro-Anurag`
- Branch: `feature/m3-m4-integrated-workflows`
- Original independent STOP code SHA: `0f1e6a26f1f22bc79c33de9d99e6b3cfdbfc5c9e`
- First correction independently reviewed SHA: `9313a4e9b3125545e08a07b1425beecbc62d01bc`
- Second independent reviewer disposition: **M3–M4 REVIEW STOP — CORRECTIONS REQUIRED**
- **Corrected implementation SHA for next independent review: `8d484498b4a51ac023e33a6af63cc51ba24c01bb`**
- Protected `main` baseline: `fc63b3dba2690f9989570ed6f98b84f112312283` (verify again at review)
- Earlier independent report `Employee_Onboarding_M3_M4_Correction_Review_20261009(1).md` is the direct source of remaining findings. Read it; this document cannot replace it.

## Confirmed review blockers and proposed closure

**R1 High — UI hides typed initialization after generic Start.** In `frontend/src/EvidenceWorkflows.tsx`, permit currently authorized IT to initialize a READY or IN_PROGRESS ACCESS/EQUIPMENT task when no operation has been loaded; permit an employee to submit confirmed EQUIPMENT_RECEIPT evidence in either READY or IN_PROGRESS. Server authority, dependencies and idempotent operation rules remain the sole enforcement. New isolated fixture `seed_m4_start_browser` creates a six-task synthetic case. `browser/m4-start.spec.cjs` exercises Start→real browser IT ACCESS failure/retry/confirmation, EQUIPMENT confirmation, employee Start→receipt after reload, and HR/MANAGER Start→schedule for ACTIVITY/INTRODUCTION/CHECK_IN. No ORM shortcut substitutes for those six initial typed actions. Existing browser tests remain.

**S1 Medium — active outline/bookmark actions bypass PDF inspection.** `backend/documents/pdf_worker.py` now traverses bounded nested outline /First and /Next links, rejects /AA and every action except a strictly local /GoTo action containing only /S and /D. Blocks JavaScript, Launch, GoToR and other external/chained actions. Preserves the subprocess CPU/memory/wall-time bounds. New real-byte tests `test_m3_outline_actions_fail_closed_before_s3_and_valid_correction_completes` exercise PDF validation, rejection before S3 evidence, auditable safe replacement, clean scan and separate HR acceptance. `test_m3_passive_local_pdf_outline_navigation_is_allowed` prevents over-rejection of a normal local bookmark. This remains bounded validation, not a full operating-system PDF sandbox.

## Previously partial closure evidence strengthened

**R5 manager historical provenance.** Additive `backend/onboarding/migrations/0019_restore_manager_actor_provenance.py` now fails installation with SQLSTATE 23514 when pre-existing MANAGER_PREPARATION TaskCompletion rows contradict attestation task or actor. No silent rewrite/deletion of historical evidence. `scripts/m4_manager_upgrade_qualification.py` and `.github/workflows/m3-m4-ci.yml` use **separate disposable PostgreSQL databases** at 0018, with current template/audit prerequisite migrations. One case verifies valid populated upgrade and preserved attribution; the other verifies contradictory existing attribution makes the 0019 upgrade fail, preserves rows and does not record migration. CI step at [run 37998259411](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37998259411) reported SUCCESS for the isolated upgrade step. Review migration/CI logs independently.

**R6 genuinely elapsed overdue activity recovery.** Added `test_overdue_cancelled_meeting_recovers_with_real_elapsed_reschedule` to `backend/activities/tests/test_activities.py`. It creates a *previously overdue* mandatory activity, schedules and cancels revision 1 through the commands, schedules revision 2 through the command, waits for the actual occurrence to elapse, records authorized ATTENDED, asserts immutable old deadline, typed TaskCompletion and successor dependency unlock. No replacement occurrence is inserted directly through ORM. This is **PostgreSQL command-level** proof; the equivalent complete elapsed sequence has not been exercised through Chromium.

## Qualification run pointers / precise limits

- [Browser with new six-kind Start scenario](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37997608515): SUCCESS, **4 Chromium scenarios passed**.
- **Final corrected code SHA `8d484498b4a51ac023e33a6af63cc51ba24c01bb`**: [backend and PostgreSQL CI](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37998317341) **SUCCESS** — 144 Python passed, 2 live-service tests skipped for separate S3/ClamAV execution, and 2 React tests passed. The CI independently ran a populated 0018→0019 manager migration on isolated valid and invalid evidence: `M4_MANAGER_UPGRADE_MATCHING_PASS` and `M4_MANAGER_UPGRADE_MISMATCH_FAIL_CLOSED_PASS`. Worker-recovery, Docker build, npm audit and runtime checks also succeeded.
- [Final corrected-code Chromium acceptance](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37998317405) **SUCCESS** — 4 passed, including R1 six-kind Start→typed-action browser acceptance.
- [Final corrected-code actual MinIO/S3, ClamAV and M3 worker recovery](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37998317407) **SUCCESS** — 2 live integration tests passed. Actual refreshed scanner signatures were required; no production AWS security is implied.
- [Prior substantive corrections backend](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37997803328), [browser](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37997803329), and [live services](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37997803351) also completed successfully.

## Still unqualified; keep these separate

- **R2 complete live browser S3** prepare→reload→same-ID resume, invalid-correction and post-S3/pre-finalize process interruption. Source supports bounded replay and checks, but composed browser/live evidence remains absent.
- **R3** full real worker outage/exhaustion→authorized replacement→healthy scan and HR approval; underlying original permanent domain dead-end was already independently closed.
- **R6** entire truly elapsed overdue cancellation/reschedule/attendance in Chromium, despite new genuine wall-clock PostgreSQL command test.
- PDF parser isolation beyond subprocess resource bounds; scanner and storage trust, transaction-held network I/O, earlier-than-post-commit M3 hard kills, storage orphan cleanup/retention, production AWS IAM/KMS/alerting, all hosted J01–J05 acceptance journeys.
- Separate M2 independent focused review; genuine identity-document data; external HRIS/calendar/IT fulfillment (synthetic only).

## Focused independent closure request

At exact corrected implementation SHA `8d484498b4a51ac023e33a6af63cc51ba24c01bb`, inspect actual source and CI logs, reproduce the previously confirmed R1 and S1 failures, verify that corrected UI actions and nested PDF validation now deny the original problems, review the populated 0018→0019 fail-closed evidence and real elapsed R6 recovery, and reassess whether R2/R6 remaining evidence qualifies as a SOURCE review STOP or a clearly bounded later acceptance gate.

Return independent **GO / STOP / INCONCLUSIVE** for *source review* with exact file/line/reproduction, separating code defects from untested operational claims. Do not assume this developer packet, GitHub green checks or partial browser paths justify production approval. No merge, production deploy, cloud provisioning, M5 or scope reductions are authorized.
