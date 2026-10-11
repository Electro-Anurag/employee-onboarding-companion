#!/usr/bin/env python3
"""Read-only hosted HTTPS smoke; never sends credentials or consequential requests.

This intentionally does NOT qualify full hosted J01-J05, real AI, worker or S3.
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

HOST = "https://eoc-companion-web.onrender.com"
DEPLOYED_SHA = "ded82f9ca85213eb7bbc50ceb3eb81f4864b92f2"
RESULTS = []
TIMEOUT_SECONDS = 105


def check(condition, description):
    if not condition:
        raise AssertionError(description)


def fetch(path, *, expected=(200,), accept="application/json"):
    url = HOST + path
    check(url.startswith("https://"), "HTTPS required")
    last_error = None
    for attempt in range(3):
        try:
            req = Request(
                url, headers={"Accept": accept, "User-Agent": "EOC-hosted-readonly-smoke/1.0"},
                method="GET"
            )
            try:
                with urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                    status = response.status
                    resolved = response.url
                    headers = response.headers
                    body = response.read(500_001)
            except HTTPError as exc:
                status = exc.code
                resolved = exc.url
                headers = exc.headers
                body = exc.read(500_001)
            check(urlparse(resolved).scheme == "https" and
                  urlparse(resolved).netloc == urlparse(HOST).netloc,
                  "Redirected outside the verified HTTPS service")
            check(len(body) <= 500_000, "Unbounded HTTP response")
            if status in (502, 503, 504) and attempt < 2:
                time.sleep(5)
                continue
            check(status in expected, f"{path}: HTTP {status}, expected {expected}")
            RESULTS.append({
                "path": path, "status": status,
                "cache_control": headers.get("Cache-Control", ""),
            })
            print(f"HOSTED_READONLY_HTTP_PASS path={path} status={status}")
            return body, headers
        except (URLError, TimeoutError, OSError) as exc:
            last_error = type(exc).__name__
            if attempt < 2:
                time.sleep(5)
            else:
                raise AssertionError(f"{path}: network failure {last_error}") from exc
    raise AssertionError(f"{path}: retry limit reached")


def main():
    check(sys.version_info >= (3, 10), "Python 3.10+ required")
    for path in ("/health/live", "/health/ready"):
        body, _ = fetch(path)
        check(bool(body), f"{path}: empty health response")

    html, _ = fetch("/", accept="text/html")
    doc = html.decode("utf-8")
    check("<html" in doc.lower(), "Hosted root did not serve HTML")
    assets = sorted(set(re.findall(r'(?:src|href)="(/static/[^"]+)"', doc)))
    check(assets, "Production React static assets missing")
    for asset in assets:
        body, _ = fetch(asset, accept="*/*")
        check(bool(body), "An asset loaded without content")
    print(f"HOSTED_REACT_ASSETS_PASS count={len(assets)}")

    csrf_raw, csrf_headers = fetch("/api/v1/auth/csrf")
    csrf = json.loads(csrf_raw)
    check(isinstance(csrf.get("csrf_token"), str) and len(csrf["csrf_token"]) > 15,
          "CSRF route does not issue a token")
    check("no-store" in csrf_headers.get("Cache-Control", "").lower(),
          "Private CSRF API may be cached")

    me_raw, me_headers = fetch("/api/v1/auth/me", expected=(401,))
    me = json.loads(me_raw)
    check(me.get("error", {}).get("code") == "UNAUTHENTICATED",
          "No-session identity must be rejected")
    check("no-store" in me_headers.get("Cache-Control", "").lower(),
          "Unauthenticated identity response may be cached")

    for path in ("/api/v1/cases", "/api/v1/notifications"):
        body, headers = fetch(path, expected=(401, 403, 404))
        check("no-store" in headers.get("Cache-Control", "").lower(),
              f"{path}: private API response is cacheable")
        check(b"@hosted-onboarding-demo.invalid" not in body,
              f"{path}: synthetic account leaked to unauthenticated caller")

    report = {
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": HOST,
        "deployed_sha": DEPLOYED_SHA,
        "qualification_scope": "PUBLIC_READ_ONLY_SMOKE_NOT_J01_TO_J05",
        "checks": RESULTS,
        "result": "PASS",
        "unqualified": [
            "hosted demo account bootstrap and login", "J01", "J02", "J03", "J04", "J05",
            "live S3/ClamAV", "background worker", "real model inference"
        ],
    }
    print("EOC_PUBLIC_SMOKE_RESULT_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"EOC_PUBLIC_SMOKE_FAIL={type(exc).__name__}:{exc}", file=sys.stderr)
        raise
