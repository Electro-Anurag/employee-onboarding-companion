from django.urls import path
from backend.foundation.views import index, health_live, health_ready
from backend.accounts import views as auth
from backend.onboarding import views as cases
from backend.onboarding import api_m2 as m2
from backend.templates import views as tmpl
from backend.forms import views as forms
from backend.provisioning import views as it
from backend.policies import views as policies
from backend.documents import views as docs
from backend.documents import quarantine_views as quarantine
from backend.documents import real_views as real_docs
from backend.training import views as training
from backend.activities import views as activities

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
    path('api/v1/cases',m2.cases_collection),
    path('api/v1/cases/<uuid:case_id>',cases.case_detail),
    path('api/v1/cases/<uuid:case_id>/assignments',cases.assignment),
    path('api/v1/owners',m2.available_owners),
    path('api/v1/templates',tmpl.collection),
    path('api/v1/templates/<uuid:template_id>',tmpl.detail),
    path('api/v1/templates/<uuid:template_id>/draft',tmpl.draft),
    path('api/v1/templates/<uuid:template_id>/publish',tmpl.publish),
    path('api/v1/templates/<uuid:template_id>/next-draft',tmpl.clone),
    path('api/v1/cases/<uuid:case_id>/activate',m2.activate),
    path('api/v1/cases/<uuid:case_id>/day-one',m2.day_one),
    path('api/v1/cases/<uuid:case_id>/timeline',m2.case_timeline),
    path('api/v1/cases/<uuid:case_id>/tasks',m2.tasks),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>',m2.task_detail),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/start',m2.task_start),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/attest-manager',m2.manager_attest),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/form-submissions',forms.submissions),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/form-submissions/<uuid:submission_id>/review',forms.review_submission),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/it-operation',it.operation_detail),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/it-operation/request',it.request_it),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/it-operation/simulate',it.simulate_it),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/it-operation/simulated-failure',it.simulated_failure),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/it-operation/confirm',it.confirm_it),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/equipment-receipt',it.receipt),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/equipment-receipt/source',it.equipment_receipt_source),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/assigned-policy',policies.assigned_policy),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/policy-acknowledge',policies.acknowledge_policy),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/document-revisions',docs.revisions),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/document-sample',docs.sample),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/quarantine-intake',quarantine.intake),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/quarantine-status',quarantine.status),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/secure-documents',real_docs.history),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/secure-documents/prepare',real_docs.prepare),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/secure-documents/<uuid:upload_id>/content',real_docs.receive),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/secure-documents/<uuid:upload_id>/review',real_docs.review),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/secure-documents/<uuid:upload_id>/download',real_docs.download),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/document-revisions/<uuid:revision_id>/download',docs.download),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/document-revisions/<uuid:revision_id>/review',docs.review),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/training-module',training.module),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/training-attempts',training.submit_attempt),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/activity-occurrences',activities.history),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/activity-occurrences/schedule',activities.schedule),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/activity-occurrences/<uuid:occurrence_id>/attendance',activities.attendance),
    path('api/v1/cases/<uuid:case_id>/tasks/<uuid:task_id>/activity-occurrences/<uuid:occurrence_id>/cancel',activities.cancel),
    path('api/v1/workspaces/me',m2.workspaces_me),
]
