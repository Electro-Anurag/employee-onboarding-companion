"""CI-only extra HR in a distinct synthetic organization for session-isolation checks."""
import secrets
from backend.accounts.models import User,Organization,Membership
from django.conf import settings
if not settings.DEBUG:
    raise RuntimeError('Cross-organization browser fixture is local/CI only')
password=secrets.token_urlsafe(22)+'Ab1!'
email='hr-b@second-organization.invalid'
org=Organization.objects.create(name='Second Synthetic Organization',timezone='Asia/Kolkata')
user=User.objects.create_user(email=email,password=password,
                              display_name='Second Synthetic HR')
Membership.objects.create(user=user,organization=org,role='HR',active=True,
                          can_manage_templates=True,can_coordinate_ownership=True)
print('HR_B '+email+' '+password)
