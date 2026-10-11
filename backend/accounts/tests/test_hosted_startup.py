"""The production shell entrypoint must not seed unless explicitly asked.

Synthetic executable stubs check orchestration only; the real database/command
semantic and role isolation are covered by test_hosted_seed.py.
"""
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "start_web.sh"


def _mock_binary(path, *, fail_seed=False):
    path.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$0 $*" >> "$EOC_STARTUP_CALLS"\n'
        + (
            'case "$*" in *seed_hosted_synthetic*) exit 8 ;; esac\n'
            if fail_seed else ""
        )
        + "exit 0\n"
    )
    path.chmod(0o700)


@pytest.mark.parametrize("flag,expected_seed", [
    (None, False),
    ("0", False),
    ("1", True),
])
def test_free_web_bootstrap_requires_explicit_flag(tmp_path, flag, expected_seed):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _mock_binary(bindir / "python")
    _mock_binary(bindir / "gunicorn")
    output = tmp_path / "calls"
    env = dict(os.environ)
    env.pop("EOC_HOSTED_DEMO_BOOTSTRAP", None)
    if flag is not None:
        env["EOC_HOSTED_DEMO_BOOTSTRAP"] = flag
    env["EOC_STARTUP_CALLS"] = str(output)
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    run = subprocess.run(
        ["/bin/sh", str(SCRIPT)],
        env=env, capture_output=True, text=True, timeout=15, check=False,
    )
    assert run.returncode == 0, run.stderr
    calls = output.read_text().splitlines()
    assert len(calls) == (3 if expected_seed else 2)
    assert calls[0].endswith("python manage.py migrate --noinput")
    if expected_seed:
        assert calls[1].endswith(
            "python manage.py seed_hosted_synthetic --confirm-synthetic"
        )
    assert calls[-1].split()[0].endswith("/gunicorn")
    assert "--bind" in calls[-1]


def test_failed_bootstrap_does_not_start_public_web(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _mock_binary(bindir / "python", fail_seed=True)
    _mock_binary(bindir / "gunicorn")
    output = tmp_path / "calls"
    env = dict(os.environ)
    env["EOC_HOSTED_DEMO_BOOTSTRAP"] = "1"
    env["EOC_STARTUP_CALLS"] = str(output)
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    run = subprocess.run(
        ["/bin/sh", str(SCRIPT)],
        env=env, capture_output=True, text=True, timeout=15, check=False,
    )
    assert run.returncode == 8
    lines = output.read_text().splitlines()
    assert len(lines) == 2
    assert "seed_hosted_synthetic" in lines[-1]
    assert not any("/gunicorn" in x for x in lines)
