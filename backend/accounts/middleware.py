"""Absolute-session and live-account deactivation guard, independent of UI claims."""
import time
from django.contrib.auth import logout
from backend.accounts.models import Membership

class SessionGuard:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.user.is_authenticated:
            started=request.session.get('m1_session_started')
            if not isinstance(started,(float,int)) or time.time()-started>8*3600 or not request.user.is_active or not Membership.objects.filter(user=request.user,active=True).exists():
                logout(request)
        return self.get_response(request)
