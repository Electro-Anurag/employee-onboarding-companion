# Mac-hosted GitHub Actions runner migration

Target branch: `feature/m5-m6-parallel-development`. The **13 workflow files** now require `runs-on: [self-hosted, linux, ARM64, eoc-mac-ci]` without a GitHub-hosted fallback.

## Why not native macOS

Existing workflows use PostgreSQL service containers plus Docker-hosted MinIO and ClamAV. GitHub supports service-container jobs only on **Linux runners with Docker**. Run an isolated **Ubuntu 24.04 ARM64 VM on the owner's Apple Silicon Mac** rather than converting or weakening the integration tests.

## Setup: owner action required

1. Use a trusted virtualization app to provision Ubuntu 24.04 ARM64. Starting VM budget on a 24-GB Mac: 4 vCPU, 10 GB RAM, 70–90 GB virtual disk. Keep the VM isolated from the host's keychain, home directory, PIOS project and employer material.
2. Install Git, curl, CA certificates, **Docker Engine** and configure the daemon inside Ubuntu. Use a dedicated Linux runner account with Docker access confined to the VM.
3. Clone the authorized repository inside the VM and run `bash scripts/mac-runner-doctor.sh`. It verifies Linux ARM64 and Docker, not application qualification.
4. In the **Electro-Anurag** GitHub account, open repository **Settings → Actions → Runners → New self-hosted runner → Linux → ARM64**. Follow the version-pinned download/verification and registration commands GitHub displays **inside the VM**. Register against this repository with the additional custom label **`eoc-mac-ci`**; retain the default `self-hosted`, `linux`, and `ARM64` labels. Never paste the registration token into code or chat.
5. Install the official runner as a systemd service following GitHub instructions (`svc.sh install`, `svc.sh start`, `svc.sh status`). Verify **Online/Idle** in GitHub. Ensure the VM runs when the Mac is available, with automatic start as appropriate.
6. Only then qualify the current SHA with real PostgreSQL/React integration, M3–M4/R3 Chromium, M5 Chromium/worker, and M3 S3 crash-recovery workflows. Record exact SHA and self-hosted runner name. **No green qualification may be claimed from a queued job.**

## Constraints and limitations

- **Not installed or qualified by repository changes.** The connected GitHub integration cannot access or control the owner's Mac or register runners. If the runner is offline, workflow jobs remain queued (GitHub normally expires queued jobs after 24 hours). No automatic GitHub-hosted fallback is permitted.
- Do not enable untrusted fork PRs on this persistent self-hosted runner. Treat Docker access as root-equivalent within the guest; run synthetic/anonymized data only. Never mount host private directories, credentials or production employee data into the VM.
- A single runner processes one job at a time; workflows using fixed PostgreSQL/MinIO/ClamAV ports must not run concurrently. Manage disk usage, logs and cleanup, and keep both VM OS and runner patched.
- GitHub currently documents that self-hosted runner compute does **not consume GitHub-hosted runner minutes** (the previously announced self-hosted platform charge was postponed). Artifact/cache storage and local hardware/network costs are separate. Verify account-specific billing.
- GitHub branch scope: this switch is committed on **M5–M6 only**. The original M3–M4 branch and protected `main` remain unchanged and still contain their own historical workflow files.

GitHub references: https://docs.github.com/en/actions/reference/runners/self-hosted-runners ; https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow ; https://docs.github.com/en/billing/concepts/product-billing/github-actions
