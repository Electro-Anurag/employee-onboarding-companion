"""Owner-gated preexisting synthetic demo password recovery guarantees."""
from io import StringIO
import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from backend.accounts.management.commands.rotate_hosted_synthetic import ROLES
from backend.accounts.models import Membership, OneTimeToken, Organization, User


def _four_role_fixture(monkeypatch):
    org = Organization.objects.create(name="Hosted Onboarding Synthetic Demo")
    users = {}
    for role in ROLES:
        user = User.objects.create_user(
            email=role.lower() + "@hosted-onboarding-demo.invalid",
            password=role + "_OldDemoPassword!2026", display_name=role,
        )
        Membership.objects.create(
            user=user, organization=org, role=role,
            can_manage_templates=role == "HR",
            can_coordinate_ownership=role == "HR",
        )
        monkeypatch.setenv(
            "EOC_DEMO_" + role + "_PASSWORD", role + "_NewDemoPassword!2026"
        )
        users[role] = user
    return org, users


def _rotate():
    with override_settings(DEBUG=False):
        call_command("rotate_hosted_synthetic",
                     "--confirm-synthetic-rotation", stdout=StringIO())


@pytest.mark.django_db(transaction=True)
def test_rotation_never_runs_without_owner_flag_or_in_debug(monkeypatch):
    _, users = _four_role_fixture(monkeypatch)
    monkeypatch.delenv("EOC_HOSTED_DEMO_CREDENTIAL_ROTATE", raising=False)
    with pytest.raises(CommandError):
        _rotate()
    monkeypatch.setenv("EOC_HOSTED_DEMO_CREDENTIAL_ROTATE", "1")
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "1")
    with pytest.raises(CommandError):
        _rotate()
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "0")
    with override_settings(DEBUG=True), pytest.raises(CommandError):
        call_command("rotate_hosted_synthetic",
                     "--confirm-synthetic-rotation", stdout=StringIO())
    with override_settings(DEBUG=False), pytest.raises(CommandError):
        call_command("rotate_hosted_synthetic", stdout=StringIO())
    for role, user in users.items():
        user.refresh_from_db()
        assert user.check_password(role + "_OldDemoPassword!2026")


@pytest.mark.django_db(transaction=True)
def test_existing_exact_demo_only_password_rotation_and_audit(monkeypatch):
    from backend.audit.models import AuditEvent
    org, users = _four_role_fixture(monkeypatch)
    other = User.objects.create_user(
        "real-unrelated-user@example.test", "LeaveAlone!2026"
    )
    monkeypatch.setenv("EOC_HOSTED_DEMO_CREDENTIAL_ROTATE", "1")
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "0")
    _rotate()
    for role, user in users.items():
        user.refresh_from_db()
        assert user.check_password(role + "_NewDemoPassword!2026")
        assert not user.check_password(role + "_OldDemoPassword!2026")
        assert Membership.objects.get(user=user).role == role
    other.refresh_from_db()
    assert other.check_password("LeaveAlone!2026")
    assert Organization.objects.get(pk=org.pk).name == "Hosted Onboarding Synthetic Demo"
    assert AuditEvent.objects.filter(
        event_type="SYNTHETIC_DEMO_CREDENTIAL_ROTATION"
    ).count() == 1
    _rotate()
    assert AuditEvent.objects.filter(
        event_type="SYNTHETIC_DEMO_CREDENTIAL_ROTATION"
    ).count() == 1


@pytest.mark.django_db(transaction=True)
def test_rotation_fails_closed_on_ambiguous_org_or_unexpected_member(monkeypatch):
    org, users = _four_role_fixture(monkeypatch)
    monkeypatch.setenv("EOC_HOSTED_DEMO_CREDENTIAL_ROTATE", "1")
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "0")
    Organization.objects.create(name="Hosted Onboarding Synthetic Demo")
    with pytest.raises(CommandError):
        _rotate()
    Organization.objects.exclude(pk=org.pk).filter(
        name="Hosted Onboarding Synthetic Demo"
    ).delete()
    outsider = User.objects.create_user(
        "outsider@hosted-onboarding-demo.invalid", "LeaveAlone!2026"
    )
    Membership.objects.create(user=outsider, organization=org, role="EMPLOYEE")
    with pytest.raises(CommandError):
        _rotate()
    for role, user in users.items():
        user.refresh_from_db()
        assert user.check_password(role + "_OldDemoPassword!2026")


@pytest.mark.django_db(transaction=True)
def test_rotation_rejects_wrong_role_and_missing_synthetic_user(monkeypatch):
    _, users = _four_role_fixture(monkeypatch)
    monkeypatch.setenv("EOC_HOSTED_DEMO_CREDENTIAL_ROTATE", "1")
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "0")
    Membership.objects.filter(user=users["HR"]).update(role="MANAGER")
    with pytest.raises(CommandError):
        _rotate()
    Membership.objects.filter(user=users["HR"]).update(role="HR")
    # Do not delete a user protected by FK membership/audit constraints.
    # Renaming the synthetic fixture identity proves exact allowlist checks.
    User.objects.filter(pk=users["IT"].pk).update(
        email="it-legacy@hosted-onboarding-demo.invalid"
    )
    with pytest.raises(CommandError):
        _rotate()
    for role in ("HR", "EMPLOYEE", "MANAGER"):
        users[role].refresh_from_db()
        assert users[role].check_password(role + "_OldDemoPassword!2026")
