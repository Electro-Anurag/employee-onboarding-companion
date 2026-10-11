#!/usr/bin/env python3
"""Private-terminal hosted role verification. Read-only except login/logout.

The operator enters four passwords via hidden terminal prompts. Passwords are
never saved, printed, emailed, sent to GitHub Actions or injected into logs.
The app is tested via real HTTPS, real login, CSRF, per-role sessions and
authorized resource reads against the public hosted *synthetic* deployment.
This is NOT completion of J01-J05 or permission for real employee data.
"""
import getpass
import http.cookiejar
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import (
    HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener,
)

HOST = "https://eoc-companion-web.onrender.com"
# App commit identity must be attested using Render deployment evidence,
# not a locally hardcoded copy of an earlier SHA.
ROLES = ("HR", "EMPLOYEE", "IT", "MANAGER")
MAX_BYTES = 120_000


class HostOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme != "https" or parsed.netloc != urlparse(HOST).netloc:
            raise RuntimeError("HTTPS request redirected away from EOC host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def request(opener, path, method="GET", data=None, csrf=None):
    if not path.startswith("/") or path.startswith("//"):
        raise RuntimeError("Invalid request path")
    url = HOST + path
    headers = {"Accept": "application/json", "User-Agent": "EOC-private-role-gate/1.0"}
    payload = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if csrf is not None:
        headers["X-CSRFToken"] = csrf
        headers["Referer"] = HOST + "/"
    req = Request(url, headers=headers, data=payload, method=method)
    try:
        try:
            rsp = opener.open(req, timeout=35)
        except HTTPError as exc:
            rsp = exc
        with rsp:
            status = rsp.status
            end_url = rsp.url
            raw = rsp.read(MAX_BYTES + 1)
            cache_control = rsp.headers.get("Cache-Control", "")
        if urlparse(end_url).scheme != "https" or urlparse(end_url).netloc != urlparse(HOST).netloc:
            raise RuntimeError("HTTP request escaped the expected host")
        if len(raw) > MAX_BYTES:
            raise RuntimeError("Oversized API response")
        try:
            body = json.loads(raw) if raw else {}
        except (UnicodeError, ValueError) as exc:
            raise RuntimeError(f"Non-JSON response to {path}") from exc
        if not isinstance(body, dict):
            raise RuntimeError(f"Malformed response to {path}")
        return status, body, cache_control
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Transport failure on {path}: {type(exc).__name__}") from exc


def assert_private(header, label):
    if "no-store" not in header.lower():
        raise AssertionError(f"{label}: missing private no-store cache control")


def one_role(role):
    pw = getpass.getpass(f"{role} existing hosted demo password (hidden): ")
    if not pw or len(pw) > 256:
        raise RuntimeError(f"{role}: missing or invalid password length")
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar), HostOnlyRedirect())
    csrf_status, csrf, cache = request(opener, "/api/v1/auth/csrf")
    if csrf_status != 200 or not csrf.get("csrf_token"):
        raise AssertionError(f"{role}: CSRF token not available: HTTP {csrf_status}")
    assert_private(cache, role + " CSRF")
    login_status, _, _ = request(
        opener, "/api/v1/auth/login", method="POST",
        data={"email": role.lower() + "@hosted-onboarding-demo.invalid", "password": pw},
        csrf=csrf["csrf_token"]
    )
    del pw
    if login_status != 200:
        # Never print passwords, response bodies or potentially user-specific
        # diagnostic data. Do not retry blindly (login admission is rate-limited).
        raise AssertionError(f"{role}: live sign-in HTTP {login_status}; no automatic retry")
    status, me, cache = request(opener, "/api/v1/auth/me")
    assert_private(cache, role + " identity")
    if status != 200 or me.get("role") != role or not me.get("organization_id"):
        raise AssertionError(f"{role}: actor-bound current identity not verified")
    org = me["organization_id"]
    status, cases, cache = request(opener, "/api/v1/cases")
    assert_private(cache, role + " authorized cases")
    if status != 200 or not isinstance(cases.get("results"), list):
        raise AssertionError(f"{role}: cases HTTP/shape invalid: {status}")
    status, _, cache = request(opener, "/api/v1/templates")
    assert_private(cache, role + " template access")
    if status != (200 if role == "HR" else 403):
        raise AssertionError(f"{role}: incorrect template authorization status {status}")
    status, _, cache = request(opener, "/api/v1/portfolio")
    assert_private(cache, role + " portfolio access")
    if status != (200 if role == "HR" else 404):
        raise AssertionError(f"{role}: incorrect portfolio authorization status {status}")
    status, inbox, cache = request(opener, "/api/v1/notifications")
    assert_private(cache, role + " inbox")
    if status != 200 or inbox.get("delivery") != "IN_APP_ONLY":
        raise AssertionError(f"{role}: notification inbox HTTP/shape invalid: {status}")
    new_status, new_csrf, _ = request(opener, "/api/v1/auth/csrf")
    if new_status != 200 or not new_csrf.get("csrf_token"):
        raise AssertionError(f"{role}: post-login CSRF refresh unavailable")
    status, _, _ = request(
        opener, "/api/v1/auth/logout", method="POST", data={},
        csrf=new_csrf["csrf_token"])
    if status != 200:
        raise AssertionError(f"{role}: logout failed: {status}")
    status, _, cache = request(opener, "/api/v1/auth/me")
    assert_private(cache, role + " post-logout identity")
    if status != 401:
        raise AssertionError(f"{role}: logout did not clear access")
    print(f"HOSTED_ROLE_PASS={role} LOGIN=200 CASES=200 TEMPLATES={'200' if role=='HR' else '403'} PORTFOLIO={'200' if role=='HR' else '404'} INBOX=200 LOGOUT=200")
    return org


def main():
    if not sys.stdin.isatty():
        raise RuntimeError("Requires a private interactive terminal, not CI/logging")
    print("Read-only synthetic hosted role verification (plus login/logout).")
    print("Ensure Render EOC_HOSTED_DEMO_BOOTSTRAP=0 and deployment LIVE.")
    print("Do not paste credentials into chat or run inside recorded shell sessions.")
    orgs = []
    for role in ROLES:
        orgs.append(one_role(role))
    if len(set(orgs)) != 1:
        raise AssertionError("The four synthetic roles are not scoped to one organization")
    print("HOSTED_FOUR_ROLE_READ_ONLY_PASS")
    print("DEPLOYED_APP_SHA=NOT_OBSERVED_BY_THIS_HTTP_PROBE")
    print("UTC=" + datetime.now(timezone.utc).isoformat())
    print("QUALIFICATION_SCOPE=AUTHENTICATED_READ_ONLY_AND_LOGIN_LOGOUT_NOT_J01_TO_J05")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError) as exc:
        print("HOSTED_FOUR_ROLE_READ_ONLY_FAIL=" + str(exc), file=sys.stderr)
        raise SystemExit(1)
