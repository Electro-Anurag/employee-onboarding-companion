"""Opt-in synthetic local account bootstrap must not run in production mode."""
from io import StringIO
import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from backend.accounts.models import User,Membership,Organization

@pytest.mark.django_db(transaction=True)
def test_seed_m2_demo_requires_debug_and_confirmation():
    with override_settings(DEBUG=False):
        with pytest.raises(CommandError):
            call_command('seed_m2_demo','--confirm-synthetic',stdout=StringIO())
    with override_settings(DEBUG=True):
        with pytest.raises(CommandError):
            call_command('seed_m2_demo',stdout=StringIO())
    assert User.objects.count()==0
    assert Organization.objects.count()==0
    with override_settings(DEBUG=True):
        out=StringIO()
        call_command('seed_m2_demo','--confirm-synthetic',stdout=out)
        with pytest.raises(CommandError):
            call_command('seed_m2_demo','--confirm-synthetic',stdout=StringIO())
    assert User.objects.count()==4
    assert Membership.objects.count()==4
    assert Organization.objects.count()==1
    assert Membership.objects.get(role='HR').can_manage_templates is True
    assert 'synthetic local accounts created' in out.getvalue().lower()
    for role in ['HR','EMPLOYEE','IT','MANAGER']:
        assert (role.lower()+'@demo.aster-vale.invalid') in out.getvalue()
        assert User.objects.get(email=role.lower()+'@demo.aster-vale.invalid').has_usable_password()
