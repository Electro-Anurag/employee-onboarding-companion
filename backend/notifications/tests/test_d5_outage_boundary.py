"""D5 private inbox fail-closed boundary, using real Django HTTP sessions.

These checks distinguish a read-only preflight failure from an unknowable
mark-read commit outcome. No worker, send, or external integration runs.
"""
import time
import uuid
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.test import Client

from backend.accounts.models import Membership, Organization, User


@pytest.fixture
def signed_in_employee(db):
    org = Organization.objects.create(name="D5 Synthetic Inbox", timezone="UTC")
    actor = User.objects.create_user(
        email="inbox@d5.invalid",password="D5SyntheticTestCredential!2026")
    Membership.objects.create(user=actor, organization=org, role="EMPLOYEE")
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    session = client.session
    session["m1_session_started"] = time.time()
    session.save()
    return client


@pytest.mark.django_db(transaction=True)
def test_inbox_database_failure_is_sanitized_and_does_not_claim_a_command(signed_in_employee):
    c = signed_in_employee
    with patch("backend.notifications.views.actor_context",
               side_effect=DatabaseError("private SQL database connection lost")):
        response = c.get("/api/v1/notifications")
    assert response.status_code == 503, response.content
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert response.json()["error"]["outcome"] == "NO_COMMAND_EXECUTED"
    assert "private SQL" not in response.content.decode()
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.django_db(transaction=True)
def test_mark_read_database_failure_is_sanitized_with_unknown_outcome(signed_in_employee):
    c = signed_in_employee
    csrf = c.get("/api/v1/auth/csrf").json()["csrf_token"]
    with patch("backend.notifications.views.actor_context",
               side_effect=DatabaseError("private SQL COMMIT state uncertain")):
        response = c.post("/api/v1/notifications/" + str(uuid.uuid4()) + "/read",
            data="{}", content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code == 503, response.content
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert response.json()["error"]["outcome"] == "UNKNOWN"
    assert response.json()["error"]["automatic_replay"] is False
    assert "private SQL" not in response.content.decode()
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.django_db(transaction=True)
def test_inbox_and_read_reject_invalid_actor_without_server_errors(signed_in_employee):
    c = signed_in_employee
    csrf = c.get("/api/v1/auth/csrf").json()["csrf_token"]
    with patch("backend.notifications.views.actor_context",
               side_effect=PermissionDenied("Synthetic ambiguous account")):
        denied = c.get("/api/v1/notifications")
        read = c.post("/api/v1/notifications/" + str(uuid.uuid4()) + "/read",
            data="{}", content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert denied.status_code == 404 and read.status_code == 404
    assert "Synthetic ambiguous" not in denied.content.decode()
    assert "Synthetic ambiguous" not in read.content.decode()
