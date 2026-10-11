"""Offline, credential-free bounded retry regression for hosted preflight."""
import unittest
from unittest.mock import patch
import hosted_journey_preflight as preflight


class SafePreloginGetTests(unittest.TestCase):
    @patch("hosted_journey_preflight.time.sleep")
    @patch("hosted_journey_preflight.request")
    def test_transient_transport_then_ready_retries_get_only(self, req, sleep):
        req.side_effect = [
            RuntimeError("Transport failure on /health/ready: TimeoutError"),
            (200, {"status": "ok"}, ""),
        ]
        body, _ = preflight.safe_prelogin_get(object(), "/health/ready")
        self.assertEqual(body["status"], "ok")
        self.assertEqual(req.call_count, 2)
        self.assertEqual(req.call_args.kwargs, {})
        sleep.assert_called_once_with(4)

    @patch("hosted_journey_preflight.time.sleep")
    @patch("hosted_journey_preflight.request")
    def test_503_during_wakeup_then_csrf_200(self, req, sleep):
        req.side_effect = [
            (503, {"error": {"code": "UNAVAILABLE"}}, ""),
            (200, {"csrf_token": "token-example"}, "private, no-store"),
        ]
        body, cache = preflight.safe_prelogin_get(object(), "/api/v1/auth/csrf")
        self.assertEqual(body["csrf_token"], "token-example")
        self.assertIn("no-store", cache)
        self.assertEqual(req.call_count, 2)
        sleep.assert_called_once_with(4)

    @patch("hosted_journey_preflight.time.sleep")
    @patch("hosted_journey_preflight.request")
    def test_denied_csrf_request_does_not_retry(self, req, sleep):
        req.return_value = (401, {}, "")
        with self.assertRaisesRegex(AssertionError, "401"):
            preflight.safe_prelogin_get(object(), "/api/v1/auth/csrf")
        self.assertEqual(req.call_count, 1)
        sleep.assert_not_called()

    @patch("hosted_journey_preflight.time.sleep")
    @patch("hosted_journey_preflight.request")
    def test_transport_failure_fails_after_exactly_three_gets(self, req, sleep):
        req.side_effect = RuntimeError(
            "Transport failure on /health/ready: TimeoutError"
        )
        with self.assertRaisesRegex(RuntimeError, "TimeoutError"):
            preflight.safe_prelogin_get(object(), "/health/ready")
        self.assertEqual(req.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("hosted_journey_preflight.request")
    def test_never_retry_login_or_business_post(self, req):
        with self.assertRaisesRegex(AssertionError, "restricted"):
            preflight.safe_prelogin_get(object(), "/api/v1/auth/login")
        with self.assertRaisesRegex(AssertionError, "restricted"):
            preflight.safe_prelogin_get(object(), "/api/v1/cases")
        req.assert_not_called()


if __name__ == "__main__":
    unittest.main()
