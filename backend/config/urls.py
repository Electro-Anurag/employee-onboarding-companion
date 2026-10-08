from django.urls import path
from backend.foundation.views import index, health_live, health_ready
from backend.accounts import views as auth
from backend.onboarding import views as cases

urlpatterns = [
    path('', index),path('health/live', health_live),path('health/ready', health_ready),
    path('api/v1/auth/csrf', auth.csrf),
    path('api/v1/auth/login', auth.login_view),
    path('api/v1/auth/logout', auth.logout_view),
    path('api/v1/auth/me', auth.me),
    path('api/v1/auth/password/change',auth.password_change),
    path('api/v1/auth/invitations',auth.issue_invitation),
    path('api/v1/auth/invitations/redeem',auth.redeem_invitation),
    path('api/v1/auth/password-reset-tokens',auth.issue_reset),
    path('api/v1/auth/password-reset-tokens/redeem',auth.redeem_reset),
    path('api/v1/cases',cases.cases),
    path('api/v1/cases/<uuid:case_id>',cases.case_detail),
    path('api/v1/cases/<uuid:case_id>/assignments',cases.assignment),
]
