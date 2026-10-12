# D4 PRD/Journey traceability — 12 October 2026

Scope: PRD v1.1 F01–F28; Business Journey v1.0 E01–E10 and hosted J01–J05. This is a source-path inventory, NOT individual FR acceptance. Last fully integrated application source 4cda23d3 PASS in GitHub runs 38197120335 attempt 2 (PostgreSQL/React/Docker/Chromium) and 38197120380 (6 real MinIO/ClamAV). D4 source candidate b91b01d7 at run 38204925335 remains pending.

| FR | Governing outcome | Existing code area | Still required |
|---|---|---|---|
F01 | Auth/RBAC | accounts, onboarding/services | hostile isolation + J05
F02 | HR case creation | onboarding/commands | hosted J01
F03 | Published task template | templates, onboarding/state_machine | hosted J01
F04 | Employee dashboard | onboarding/views, frontend/App | hosted all states
F05 | Document submission | documents, frontend/EvidenceWorkflows | hosted private S3 J02
F06 | HR review/clarification | documents | hosted rejection/replacement J02
F07 | Persisted forms | forms | hosted role correction J01
F08 | Policy/benefits guidance | policies, ai/offline_policy | J04
F09 | IT access/equipment fulfillment | provisioning | blocked→fulfilled J03
F10 | Meeting schedule/reschedule/missed | activities, browser/m4-overdue | D4 T04 real elapsed, hosted J01
F11 | Team introductions | activities, onboarding tasks | manager evidence J01
F12 | Mandatory training | training | role/retry J01
F13 | Dependency eligibility | onboarding/state_machine | multi-owner and J01/J02
F14 | Owner assignment | onboarding/services | E06 reassignment
F15 | Deduplicated reminders | notifications, jobs | hosted always-on J03
F16 | Owner-resolved exceptions | onboarding/exceptions | E01–E06
F17 | Scoped owner workspace | onboarding/portfolio,dashboard | hosted four roles
F18 | Case-grounded AI | ai/context,answers | real provider and J04
F19 | Policy-supported AI | ai/offline_policy,validator | independent semantics J04
F20 | Eligible next-best-action | ai/guidance | J04 source/owner
F21 | AI escalation assistance | ai/guidance,views | human-reviewed J04
F22 | Human command authority | ai/views, typed commands | security J05
F23 | Actor/reason audit | audit, command receipts | hosted J01–J05 and security
F24 | Persistent state | PostgreSQL models | hosted restart J01
F25 | Progress analytics | onboarding/dashboard,portfolio | accurate role metrics
F26 | HR evidence-gated closeout | onboarding/closeout | full hosted J01
F27 | Recovery/idempotence | jobs/recovery, document saga | interruption + J05
F28 | Synthetic seeded repeatability | accounts/management/commands | hosted reproducibility

Each item is a candidate source location, not 28 individually tested requirements. Final hosted acceptance remains 0/5.

| Exception | Code/acceptance checkpoint |
|---|---|
E01 missing document | document dependency owner, J02 open
E02 rejected document | scanned replacement + HR decision, J02 open
E03 delayed IT | blocked access, reminders, J03 open
E04 missed activity/training | manager actual elapsed MISSED→rescheduled ATTENDED and HR successor; D4 run 38204925335 pending
E05 joining-date change | onboarding/date_changes + M5 tests; hosted open
E06 unavailable owner | onboarding/services reassign; full handoff open
E07 unsupported policy | AI offline abstention; independently evaluated J04 open
E08 unauthorized case | M1 scoping; cross-tenant release/J05 open
E09 duplicate/conflicting write | receipts/locks; J05 open
E10 provider/integration outage | offline fail-closed; real hosted J04/J03 open

D3 local/source QUALIFIED; D4 T04 PENDING; D5 independent final security/migration/a11y OPEN; D6 hosted operations/real AI/demo OPEN. No authorized deployment, paid service or hosted data change. 70% conservative estimate (±10–15 points), J01–J05 0/5, production GO STOP.
