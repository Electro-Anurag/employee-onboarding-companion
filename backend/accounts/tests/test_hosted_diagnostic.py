"""Read-only synthetic auth diagnostic must not mutate accounts/throttles."""
from io import StringIO
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from backend.accounts.models import User, Membership, Organization, LoginThrottle


@pytest.fixture
def demo(monkeypatch):
    org = Organization.objects.create(name="Hosted Onboarding Synthetic Demo")
    users = {}
    for role in ("HR", "EMPLOYEE", "IT", "MANAGER"):
        password = role + "_TrustedSyntheticOnly2026!"
        user = User.objects.create_user(
            role.lower() + "@hosted-onboarding-demo.invalid", password,
            display_name="Synthetic " + role
        )
        Membership.objects.create(
            user=user, organization=org, role=role,
            can_manage_templates=(role == "HR"),
            can_coordinate_ownership=(role == "HR")
        )
        monkeypatch.setenv("EOC_DEMO_" + role + "_PASSWORD", password)
        users[role] = user
    monkeypatch.setenv("EOC_HOSTED_DEMO_CREDENTIAL_DIAGNOSE", "1")
    monkeypatch.setenv("EOC_HOSTED_DEMO_CREDENTIAL_ROTATE", "0")
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "0")
    return users


def diagnose():
    output = StringIO()
    with override_settings(DEBUG=False):
        call_command("diagnose_hosted_synthetic",
                     "--confirm-synthetic-diagnostic", stdout=output)
    return output.getvalue()


@pytest.mark.django_db
def test_readonly_matches_all_private_secrets_and_preserves_hashes(demo):
    previous = {role: u.password for role, u in demo.items()}
    result = diagnose()
    assert result.count("STATUS=SERVER_SIDE_PASSWORD_AND_ROLE_MATCH") == 4
    assert "EOC_SYNTHETIC_AUTH_DIAG=READ_ONLY_COMPLETE" in result
    assert "TrustedSynthetic" not in result
    assert LoginThrottle.objects.count() == 0
    for role, user in demo.items():
        user.refresh_from_db()
        assert user.password == previous[role]


@pytest.mark.django_db
def test_diagnostic_distinguishes_env_hash_mismatch_without_mutating(demo, monkeypatch):
    monkeypatch.setenv("EOC_DEMO_HR_PASSWORD", "WrongTrustedSynthetic!2026")
    before = demo["HR"].password
    result = diagnose()
    assert "EOC_SYNTHETIC_AUTH_DIAG_ROLE=HR STATUS=PRIVATE_ENV_SECRET_HASH_MISMATCH" in result
    assert result.count("STATUS=SERVER_SIDE_PASSWORD_AND_ROLE_MATCH") == 3
    demo["HR"].refresh_from_db()
    assert demo["HR"].password == before
    assert LoginThrottle.objects.count() == 0


@pytest.mark.django_db
def test_inactive_membership_fails_closed_without_password_check(demo):
    Membership.objects.filter(user=demo["HR"]).update(active=False)
    result = diagnose()
    assert "EOC_SYNTHETIC_AUTH_DIAG_ROLE=HR STATUS=IDENTITY_OR_MEMBERSHIP_INVALID" in result
    assert result.count("STATUS=SERVER_SIDE_PASSWORD_AND_ROLE_MATCH") == 3


@pytest.mark.django_db
def test_disabled_flag_debug_or_mutation_flags_refuse(demo, monkeypatch):
    monkeypatch.setenv("EOC_HOSTED_DEMO_CREDENTIAL_DIAGNOSE", "0")
    with pytest.raises(CommandError):
        diagnose()
    monkeypatch.setenv("EOC_HOSTED_DEMO_CREDENTIAL_DIAGNOSE", "1")
    with override_settings(DEBUG=True), pytest.raises(CommandError):
        call_command("diagnose_hosted_synthetic",
                     "--confirm-synthetic-diagnostic")
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "1")
    with pytest.raises(CommandError):
        diagnose()
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "0")
    monkeypatch.setenv("EOC_HOSTED_DEMO_CREDENTIAL_ROTATE", "1")
    with pytest.raises(CommandError):
        diagnose()


@pytest.mark.django_db
def test_missing_user_or_env_secret_does_not_create_account(demo, monkeypatch):
    monkeypatch.delenv("EOC_DEMO_HR_PASSWORD")
    result = diagnose()
    assert "EOC_SYNTHETIC_AUTH_DIAG_ROLE=HR STATUS=PRIVATE_ENV_SECRET_MISSING" in result
    assert User.objects.count() == 4
    assert LoginThrottle.objects.count() == 0
