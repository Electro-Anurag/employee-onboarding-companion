"""Absolute-session and active-member guard; fail closed on database outages."""
import time
from django.contrib.auth import logout
from django.db import DatabaseError
from backend.accounts.models import Membership
from backend.common.http import transient_db_response

class SessionGuard:
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        try:
            if request.user.is_authenticated:
                started=request.session.get('m1_session_started')
                if (not isinstance(started,(float,int)) or time.time()-started>8*3600
                        or not request.user.is_active
                        or not Membership.objects.filter(user=request.user,active=True).exists()):
                    logout(request)
        except DatabaseError as exc:
            # No view/command has executed; never serve protected content after
            # live authorization cannot be checked.
            return transient_db_response(exc,preflight=True)
        return self.get_response(request)
