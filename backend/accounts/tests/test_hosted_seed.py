"""Hosted bootstrap is explicitly opt-in, synthetic-only and never logs secrets."""
from io import StringIO
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from backend.accounts.models import User, Membership, Organization


@pytest.mark.django_db(transaction=True)
def test_hosted_synthetic_bootstrap_requires_explicit_gate_and_no_debug(monkeypatch):
    monkeypatch.delenv("EOC_HOSTED_DEMO_BOOTSTRAP", raising=False)
    with override_settings(DEBUG=False), pytest.raises(CommandError):
        call_command("seed_hosted_synthetic", "--confirm-synthetic")
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "1")
    with override_settings(DEBUG=True), pytest.raises(CommandError):
        call_command("seed_hosted_synthetic", "--confirm-synthetic")
    assert not Organization.objects.filter(name="Hosted Onboarding Synthetic Demo").exists()


@pytest.mark.django_db(transaction=True)
def test_hosted_synthetic_creates_one_isolated_four_role_demo_without_secret_output(monkeypatch):
    monkeypatch.setenv("EOC_HOSTED_DEMO_BOOTSTRAP", "1")
    for role in ("HR", "EMPLOYEE", "IT", "MANAGER"):
        monkeypatch.setenv("EOC_DEMO_" + role + "_PASSWORD",
                           role + "_SyntheticStrongSecret!2026")
    out = StringIO()
    with override_settings(DEBUG=False):
        call_command("seed_hosted_synthetic", "--confirm-synthetic", stdout=out)
    org = Organization.objects.get(name="Hosted Onboarding Synthetic Demo")
    members = Membership.objects.filter(organization=org).select_related("user")
    assert members.count() == 4
    assert set(m.role for m in members) == {"HR", "EMPLOYEE", "IT", "MANAGER"}
    assert all(m.user.email.endswith("@hosted-onboarding-demo.invalid") for m in members)
    assert all(m.user.has_usable_password() for m in members)
    assert all(m.can_manage_templates == (m.role == "HR") for m in members)
    assert "SyntheticStrongSecret" not in out.getvalue()
    before = User.objects.count()
    with override_settings(DEBUG=False), pytest.raises(CommandError):
        call_command("seed_hosted_synthetic", "--confirm-synthetic", stdout=StringIO())
    assert User.objects.count() == before
