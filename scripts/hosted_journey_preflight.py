#!/usr/bin/env python3
"""Hosted read-only synthetic journey inventory, run only in a private TTY.

Uses existing account sessions and verifies real case/template/owner/task
readiness without creating or mutating onboarding records. The only POST
requests are CSRF-protected login and logout. No secrets or PII are printed.
This is a readiness inventory, NOT J01-J05 acceptance.
"""
import getpass
import hashlib
import http.cookiejar
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from urllib.request import HTTPCookieProcessor, build_opener

from hosted_role_verify import (
    HOST, HostOnlyRedirect, ROLES, request, assert_private,
)


def ensure(condition, message):
    if not condition:
        raise AssertionError(message)


def prompt_session(role):
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar), HostOnlyRedirect())
    status, csrf, cache = request(opener, "/api/v1/auth/csrf")
    ensure(status == 200 and isinstance(csrf.get("csrf_token"), str),
           f"{role}: CSRF preflight unavailable")
    assert_private(cache, "csrf")
    password = getpass.getpass(f"{role} password (hidden): ")
    ensure(0 < len(password) <= 256, f"{role}: invalid password length")
    code, _, _ = request(
        opener, "/api/v1/auth/login", method="POST",
        data={
            "email": role.lower() + "@hosted-onboarding-demo.invalid",
            "password": password,
        },
        csrf=csrf["csrf_token"],
    )
    del password
    ensure(code == 200, f"{role}: sign-in HTTP {code}; no automatic retry")
    status, me, cache = request(opener, "/api/v1/auth/me")
    ensure(status == 200 and me.get("role") == role,
           f"{role}: current identity/role mismatch")
    assert_private(cache, "identity")
    return opener, me["organization_id"]


def read(opener, path, status=200):
    code, data, cache = request(opener, path)
    ensure(code == status, f"{path}: HTTP {code}, expected {status}")
    assert_private(cache, "read " + path.split("?")[0])
    return data


def summary_for_cases(rows):
    return dict(sorted(Counter(str(row.get("status", "UNDEFINED")) for row in rows).items()))


def case_marker(case_id):
    # Case UUID never printed. Fingerprint is only to correlate read results.
    return hashlib.sha256(case_id.encode("ascii")).hexdigest()[:12]


def main():
    ensure(sys.stdin.isatty(), "Requires private interactive terminal; do not run in CI")
    print("EOC_HOSTED_JOURNEY_PREFLIGHT_BEGIN")
    print("PUBLIC_URL=" + HOST)
    print("THIS_IS_READ_ONLY_PREFLIGHT_NOT_J01_TO_J05")
    sessions, orgs, actors = {}, set(), {}
    try:
        for role in ROLES:
            opener, org_id = prompt_session(role)
            sessions[role] = opener
            orgs.add(org_id)
            actors[role] = read(opener, "/api/v1/cases").get("results")
            ensure(isinstance(actors[role], list),
                   role + ": case collection response is not a list")
            ensure(len(actors[role]) <= 100,
                   role + ": case collection hit truncation boundary")
            print("ROLE_INVENTORY=" + json.dumps({
                "role": role,
                "cases": len(actors[role]),
                "case_states": summary_for_cases(actors[role]),
            }, sort_keys=True))
        ensure(len(orgs) == 1, "Synthetic accounts span multiple organizations")

        hr = sessions["HR"]
        templates = read(hr, "/api/v1/templates").get("results")
        ensure(isinstance(templates, list), "HR template inventory malformed")
        states = Counter(str(t.get("state", "UNKNOWN")) for t in templates)
        published_default = [
            t for t in templates
            if t.get("key") == "employee_first_month" and t.get("state") == "PUBLISHED"
        ]
        print("TEMPLATE_INVENTORY=" + json.dumps({
            "total": len(templates),
            "by_state": dict(sorted(states.items())),
            "published_default_candidates": len(published_default),
        }, sort_keys=True))

        for role in ROLES:
            data = read(hr, "/api/v1/owners?role=" + role)
            rows = data.get("results")
            ensure(data.get("role") == role and isinstance(rows, list),
                   "Owner selection shape invalid for " + role)
            print("OWNER_INVENTORY=" + json.dumps({
                "role": role, "available_count": len(rows),
            }, sort_keys=True))

        for row in actors["HR"][:8]:
            case_id = row.get("id")
            ensure(isinstance(case_id, str) and len(case_id) == 36,
                   "HR case has invalid UUID")
            tasks = read(hr, "/api/v1/cases/" + case_id + "/tasks")
            ensure(isinstance(tasks.get("tasks"), list),
                   "HR task graph response malformed")
            progress = tasks.get("progress") or {}
            print("CASE_READINESS=" + json.dumps({
                "case_marker": case_marker(case_id),
                "case_status": tasks.get("case_status"),
                "task_total": len(tasks["tasks"]),
                "mandatory_completed": progress.get("mandatory_completed"),
                "mandatory_total": progress.get("mandatory_total"),
                "task_states": dict(sorted(Counter(str(
                    t.get("state", "UNKNOWN")) for t in tasks["tasks"]).items())),
            }, sort_keys=True))

        if not published_default:
            print("J01_PRECONDITION=BLOCKED_NO_PUBLISHED_DEFAULT_TEMPLATE")
        elif len(actors["HR"]) > 8:
            print("J01_PRECONDITION=REQUIRES_PAGINATION_AWARE_ISOLATION")
        else:
            print("J01_PRECONDITION=ROLE_AND_TEMPLATE_READINESS_OBSERVED")
        print("J02=NOT_EXECUTED_LIVE_S3_SCANNER_DISABLED")
        print("J03=NOT_EXECUTED_PERSISTENT_WORKER_ABSENT")
        print("J04=NOT_EXECUTED_REAL_MODEL_DISABLED")
        print("J05=NOT_EXECUTED_FULL_CROSS_EMPLOYEE_RETRY_AUDIT")
    finally:
        for role, opener in sessions.items():
            try:
                _, csrf, _ = request(opener, "/api/v1/auth/csrf")
                if csrf.get("csrf_token"):
                    status, _, _ = request(
                        opener, "/api/v1/auth/logout", method="POST",
                        data={}, csrf=csrf["csrf_token"])
                    print("ROLE_LOGOUT=" + role + ":" + str(status))
            except Exception:
                print("ROLE_LOGOUT=" + role + ":UNVERIFIED")
    print("EOC_HOSTED_JOURNEY_PREFLIGHT_PASS")
    print("UTC=" + datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never serialize unexpected response data, cookie jar or passwords.
        print("EOC_HOSTED_JOURNEY_PREFLIGHT_FAIL="
              + type(exc).__name__ + ":" + str(exc), file=sys.stderr)
        raise SystemExit(1)
