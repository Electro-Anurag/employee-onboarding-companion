"""M7 read-only HR portfolio page, limited to currently assigned cases.

Each page reports only its own counts. Never advertise page-local totals as
organization-wide metrics or leak cases assigned to another HR member.
"""
from django.utils import timezone
from backend.accounts.models import Membership
from backend.accounts.security import actor_context
from backend.onboarding.models import Task,CaseException
from backend.onboarding.services import CommandFailure,scoped_cases
from backend.onboarding.state_machine import case_progress

MAX_PORTFOLIO_PAGE = 25


def portfolio_page(actor,*,after=None,limit=25):
    member=actor_context(actor)
    if member.role!=Membership.HR or not member.available:
        raise CommandFailure("NOT_FOUND",404)
    if type(limit) is not int or not 1<=limit<=MAX_PORTFOLIO_PAGE:
        raise CommandFailure("INVALID_PORTFOLIO_LIMIT",422)
    now=timezone.now()
    # Scoped at the current HR assignment, not the whole organization.
    qs=scoped_cases(actor).select_related("employee__user").order_by("pk")
    if after is not None:
        qs=qs.filter(pk__gt=after)
    page=list(qs[:limit+1])
    more=len(page)>limit
    rows=[]
    for case in page[:limit]:
        work=Task.objects.filter(case=case,required=True,applicable=True)
        late=(work.filter(due_at__lt=now)
            .exclude(execution_state="CANCELLED")
            .exclude(execution_state="COMPLETED",completion__isnull=False)
            .count())
        open_episodes=CaseException.objects.filter(
            case=case,status__in=("OPEN","ASSIGNED","RESOLVED")).count()
        rows.append({
            "case_id":str(case.pk),"employee_name":case.employee.user.display_name,
            "joining_date":case.joining_date.isoformat(),
            "status":case.status,"case_version":case.version,
            "progress":case_progress(case),
            "overdue_mandatory":late,"unclosed_exceptions":open_episodes,
        })
    return {
        "as_of":now.isoformat(),"scope":"CURRENT_HR_ASSIGNMENTS_PAGE",
        "page_count":len(rows),
        "has_more":more,
        "next_cursor":rows[-1]["case_id"] if rows and more else None,
        "results":rows,
    }
