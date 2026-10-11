# Self-hosted Ubuntu ARM64 CI queue recovery — non-destructive diagnostic

**Scope:** private `Electro-Anurag/employee-onboarding-companion`, runner labels
`[self-hosted, linux, ARM64, eoc-mac-ci]`. This assumes the owner's
already-provisioned **Ubuntu ARM64 VM** on their own Mac; do not run on the
host macOS or an unrelated organization's machine.

GitHub source check on 11 Oct 2026: current branch has queued run
`38150383695` (M6), `38150383700` (M7), `38150225570`
(integrated), and `38146978776` (T02). **Queued status alone is not
proof that the runner is offline.** The chat connector does not have an
authorized runner-listing endpoint. The owner can read status from their
registered GitHub CLI without sharing tokens.

Run **inside the Ubuntu VM** as the already-authorized `ecoci` account:

```sh
gh api repos/Electro-Anurag/employee-onboarding-companion/actions/runners \
  --jq '.runners[] | {name, status, busy, labels: [.labels[].name]}'
pwd
uname -sm
pgrep -af 'Runner.Listener|Runner.Worker' || true
systemctl list-units --all --type=service 'actions.runner*' --no-pager
docker info --format 'Docker engine: {{.ServerVersion}} / {{.Architecture}}'
```

Expected: GitHub runner status `online`, matching `eoc-mac-ci` label; Linux
aarch64; working Docker engine; Runner.Listener active (busy may be
true during test execution). If the runner is **online/busy**, first
inspect current running jobs; do not restart it and abort evidence.

If it is **offline and installed as a systemd service**, locate the
original actions-runner directory (`~/actions-runner/actions-runner/actions-runner`
was used in prior EOC setup) and run:

```sh
cd ~/actions-runner/actions-runner/actions-runner
sudo ./svc.sh status
sudo ./svc.sh start
sudo ./svc.sh status
```

If `svc.sh` reports no installed service, do not create or
re-register an additional runner blindly. Inspect original setup and
manual `./run.sh` launch method first. Never paste GitHub registration
tokens, credentials, `.credentials` contents, env secrets or raw runner
diagnostic logs into chat. Redact account names and private paths from
any shared logs as appropriate.

A successful start is *not* a green application run. Verify the latest
exact-SHA Actions job statuses and logs, fix actual failures, re-run
targeted current-HEAD qualification, and only then revisit hosted J01–J05.

**Costs/permissions:** no GitHub-hosted runner fallback, paid Render worker,
third-party model calls or re-registration is authorized here.
