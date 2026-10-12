"""D5 cross-tenant and same-organization employee isolation at the real HTTP API.

No ORM-only access assumption: enforce actual Django sessions, CSRF and all
case-dependent reads/writes in a disposable PostgreSQL test database.
"""
import json
import time
import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from backend.accounts.models import Membership, Organization, User
from backend.audit.models import AuditEvent, CommandReceipt
from backend.onboarding.commands import activate_case, create_case
from backend.onboarding.models import OnboardingCase, Task
from backend.templates.services import create_default, publish_template


@pytest.fixture
def isolated_tenants(db):
    tenants = {}
    for tenant_name in ("north", "south"):
        org = Organization.objects.create(
            name="D5 Synthetic " + tenant_name, timezone="UTC")
        people = {}
        for role in ("HR", "EMPLOYEE", "IT", "MANAGER"):
            user = User.objects.create_user(
                email=role.lower() + "@" + tenant_name + ".d5.invalid",
                password="SyntheticD5Only!2026",
                display_name="D5 " + tenant_name + " " + role)
            member = Membership.objects.create(
                user=user, organization=org, role=role,
                can_manage_templates=(role == "HR"),
                can_coordinate_ownership=(role == "HR"))
            people[role] = (user, member)
        draft = create_default(actor=people["HR"][0])
        published = publish_template(actor=people["HR"][0],
            template_id=uuid.UUID(draft["id"]), revision=1)
        tenants[tenant_name] = {
            "org": org, "people": people,
            "template_id": uuid.UUID(published["version_id"])
        }

    def make_case(tenant, employee_member, *, offset=28):
        t = tenants[tenant]
        created, status = create_case(
            actor=t["people"]["HR"][0], employee_id=employee_member.pk,
            template_version_id=t["template_id"],
            joining_date=timezone.localdate()+timedelta(days=offset),
            owner_ids={
                "IT": t["people"]["IT"][1].pk,
                "MANAGER": t["people"]["MANAGER"][1].pk},
            key=uuid.uuid4())
        assert status == 201
        cid = uuid.UUID(created["case_id"])
        activated, status = activate_case(
            actor=t["people"]["HR"][0], case_id=cid,
            key=uuid.uuid4(), expected_version=1)
        assert status == 200 and activated["result"]["status"] == "PRE_JOINING"
        return OnboardingCase.objects.get(pk=cid)

    north = tenants["north"]
    south = tenants["south"]
    primary = make_case("north", north["people"]["EMPLOYEE"][1])
    another_user = User.objects.create_user(
        email="another.employee@north.d5.invalid",
        password="SyntheticD5Only!2026",
        display_name="D5 NORTH OTHER EMPLOYEE SECRET")
    another_member = Membership.objects.create(
        user=another_user, organization=north["org"], role="EMPLOYEE")
    secondary = make_case("north", another_member)
    foreign = make_case("south", south["people"]["EMPLOYEE"][1])
    return {
        "tenants": tenants, "primary": primary,
        "secondary": secondary, "foreign": foreign,
        "other_employee": another_user,
    }


def session(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    s = client.session
    s["m1_session_started"] = time.time()
    s.save()
    return client


def read_paths(case):
    root = "/api/v1/cases/" + str(case.pk)
    ids = {t.key: t.pk for t in Task.objects.filter(case=case)}
    def task(key, extension=""):
        return root + "/tasks/" + str(ids[key]) + extension
    return [
        root,
        root + "/tasks",
        task("manager_preparation"),
        root + "/dashboard",
        root + "/closeout-readiness",
        root + "/timeline",
        root + "/exceptions",
        root + "/companion/guidance",
        task("personal_details", "/form-submissions"),
        task("identity_document", "/document-revisions"),
        task("identity_document", "/secure-documents"),
        task("identity_document", "/document-sample"),
        task("team_introduction", "/activity-occurrences"),
        task("workspace_access", "/it-operation"),
        task("workspace_access", "/equipment-receipt/source"),
        task("security_training", "/training-module"),
        task("conduct_ack", "/assigned-policy"),
    ]


@pytest.mark.django_db(transaction=True)
def test_d5_case_api_reads_deny_other_employee_and_foreign_org(isolated_tenants):
    state = isolated_tenants
    north = state["tenants"]["north"]["people"]
    south = state["tenants"]["south"]["people"]
    primary = state["primary"]
    other_clients = {
        "same_org_other_employee": session(state["other_employee"]),
        "foreign_employee": session(south["EMPLOYEE"][0]),
        "foreign_hr": session(south["HR"][0]),
        "foreign_it": session(south["IT"][0]),
        "foreign_manager": session(south["MANAGER"][0]),
    }
    paths = read_paths(primary)
    forbidden_identifiers = [str(primary.pk), str(north["EMPLOYEE"][1].pk)]
    for label, client in other_clients.items():
        for path in paths:
            result = client.get(path)
            assert result.status_code == 404, (
                label, path, result.status_code, result.content[:300])
            assert result["Cache-Control"] == "private, no-store", path
            assert not any(token.encode() in result.content
                           for token in forbidden_identifiers), path

    # Positive control: the legitimate employee and assigned HR can access
    # the case, and each employee sees only their own case in collection.
    employee = session(north["EMPLOYEE"][0])
    hr = session(north["HR"][0])
    assert employee.get("/api/v1/cases/" + str(primary.pk)).status_code == 200
    assert hr.get("/api/v1/cases/" + str(primary.pk)).status_code == 200
    emp_cases = employee.get("/api/v1/cases").json()["results"]
    assert [x["id"] for x in emp_cases] == [str(primary.pk)]
    other_cases = other_clients["same_org_other_employee"].get("/api/v1/cases").json()["results"]
    assert [x["id"] for x in other_cases] == [str(state["secondary"].pk)]
    foreign_cases = other_clients["foreign_hr"].get("/api/v1/cases").json()["results"]
    assert [x["id"] for x in foreign_cases] == [str(state["foreign"].pk)]


@pytest.mark.django_db(transaction=True)
def test_d5_cross_tenant_writes_and_csrf_fail_without_audit_mutation(isolated_tenants):
    state = isolated_tenants
    north = state["tenants"]["north"]["people"]
    south = state["tenants"]["south"]["people"]
    case = state["primary"]
    target = Task.objects.get(case=case,key="manager_preparation")
    hr = session(north["HR"][0])
    foreign = session(south["HR"][0])
    root = "/api/v1/cases/" + str(case.pk)
    assignment = root + "/assignments"
    body = {"role":"IT", "new_member_id":str(north["IT"][1].pk),
            "reason":"Denied unauthorized target alteration"}
    headers = {"HTTP_IDEMPOTENCY_KEY":str(uuid.uuid4()),
        "HTTP_IF_MATCH":f'"case:{case.pk}:v{case.version}"'}
    audit_before = AuditEvent.objects.count()
    receipts_before = CommandReceipt.objects.count()
    versions_before = (case.version, target.version)

    # Authentication without a CSRF token cannot mutate even an authorized case.
    no_csrf = hr.post(assignment, data=json.dumps(body),
        content_type="application/json", **headers)
    assert no_csrf.status_code == 403, no_csrf.content[:300]

    # With a valid CSRF header, foreign-HR scope must fail rather than leak
    # whether a target employee has a case, or generate an audit receipt.
    foreign_csrf = foreign.get("/api/v1/auth/csrf").json()["csrf_token"]
    denied = foreign.post(assignment, data=json.dumps(body),
        content_type="application/json", HTTP_X_CSRFTOKEN=foreign_csrf, **headers)
    assert denied.status_code == 404, denied.content[:300]

    start_route = root + "/tasks/" + str(target.pk) + "/start"
    start = foreign.post(start_route, data="{}", content_type="application/json",
        HTTP_X_CSRFTOKEN=foreign_csrf,
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v{case.version}"')
    assert start.status_code == 404, start.content[:300]

    exception = foreign.post(root + "/exceptions/open",
        data=json.dumps({"task_id":str(target.pk),"cause":"TASK_OVERDUE",
            "note":"Synthetic external unauthorized injection"}),
        content_type="application/json",HTTP_X_CSRFTOKEN=foreign_csrf,
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v{case.version}"')
    assert exception.status_code == 404, exception.content[:300]

    case.refresh_from_db()
    target.refresh_from_db()
    assert (case.version,target.version) == versions_before
    assert AuditEvent.objects.count() == audit_before
    assert CommandReceipt.objects.count() == receipts_before
