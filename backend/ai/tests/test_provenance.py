"""Offline M6 claim-to-evidence red-team, using real scoped PostgreSQL case state.

These are deterministic *contract* evaluations. They do not measure model
reasoning quality, real-provider accuracy or natural-language entailment.
No external requests and no paid inference.
"""
import uuid
import pytest
from backend.ai.context import authorized_context
from backend.ai.validator import validate_answer,UnsafeAIAnswer
from backend.ai.answers import answer_question
from backend.audit.models import AuditEvent
from backend.onboarding.models import OnboardingCase,TaskCompletion
from backend.onboarding.commands import activate_case
from backend.onboarding.tests.test_m2_workflow import world,published,create


@pytest.fixture
def active_case(world):
    _,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    case.refresh_from_db()
    return case,actors


def proposed(ctx,*,citations=None,actions=None,blockers=None,kind='SUPPORTED',
             limitations=None):
    return {
        'answer_type':kind,
        'answer':'Synthetic example: use the referenced task evidence.',
        'citations':citations if citations is not None else [ctx['sources'][0]],
        'recommended_actions':actions if actions is not None else [],
        'blockers':blockers if blockers is not None else [],
        'clarification':None,'escalation_draft':None,
        'limitations':limitations if limitations is not None else [],
    }


@pytest.mark.django_db(transaction=True)
def test_actions_require_citation_to_their_own_task_not_any_valid_source(active_case):
    case,actors=active_case
    user=actors['MANAGER'][0]
    ctx=authorized_context(user,case.pk)
    action=next(a for a in ctx['eligible_actions'] if a['task_id'] in {
        t['id'] for t in ctx['tasks']})
    own_source='TASK:'+action['task_id']
    other_source=next(s for s in ctx['sources'] if s!=own_source)
    bad=proposed(ctx,citations=[other_source],actions=[action['id']])
    with pytest.raises(UnsafeAIAnswer,match='ACTION_TASK_CITATION_REQUIRED'):
        validate_answer(bad,ctx,actor=user,case_id=case.pk)
    good={**bad,'citations':[own_source]}
    assert validate_answer(good,ctx,actor=user,case_id=case.pk)[
        'recommended_actions']==[action['id']]
    assert 'TASK:'+action['task_id'] in ctx['sources']


@pytest.mark.django_db(transaction=True)
def test_blockers_require_citation_to_blocked_task_not_unrelated_case_task(active_case):
    case,actors=active_case
    user=actors['MANAGER'][0]
    ctx=authorized_context(user,case.pk)
    blocker=ctx['blockers'][0]
    own='TASK:'+blocker['task_id']
    unrelated=next(s for s in ctx['sources'] if s!=own)
    bad=proposed(ctx,citations=[unrelated],blockers=[blocker['id']])
    with pytest.raises(UnsafeAIAnswer,match='BLOCKER_TASK_CITATION_REQUIRED'):
        validate_answer(bad,ctx,actor=user,case_id=case.pk)
    assert validate_answer({**bad,'citations':[own]},ctx,actor=user,
        case_id=case.pk)['blockers']==[blocker['id']]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('missing',[[],[' ']])
def test_partial_answers_explain_limits_and_preserve_valid_sources(active_case,missing):
    case,actors=active_case
    user=actors['EMPLOYEE'][0]
    ctx=authorized_context(user,case.pk)
    bad=proposed(ctx,kind='PARTIAL',limitations=missing)
    with pytest.raises(UnsafeAIAnswer,match='PARTIAL_LIMITATION_REQUIRED'):
        validate_answer(bad,ctx,actor=user,case_id=case.pk)
    good={**bad,'limitations':['The available sources do not cover every question.']}
    assert validate_answer(good,ctx,actor=user,case_id=case.pk)[
        'answer_type']=='PARTIAL'


@pytest.mark.django_db(transaction=True)
def test_cross_role_policy_citation_cannot_be_laundered_as_manager_evidence(active_case):
    case,actors=active_case
    employee=authorized_context(actors['EMPLOYEE'][0],case.pk)
    private_source=next(s for s in employee['sources'] if s.startswith('POLICY:'))
    manager=actors['MANAGER'][0]
    ctx=authorized_context(manager,case.pk)
    assert private_source not in ctx['sources']
    forged=proposed(ctx,citations=[private_source])
    with pytest.raises(UnsafeAIAnswer,match='UNSUPPORTED_CITATIONS'):
        validate_answer(forged,ctx,actor=manager,case_id=case.pk)


@pytest.mark.django_db(transaction=True)
def test_stale_case_revision_denies_previously_grounded_action(active_case):
    case,actors=active_case
    user=actors['MANAGER'][0]
    ctx=authorized_context(user,case.pk)
    action=ctx['eligible_actions'][0]
    grounded=proposed(ctx,citations=['TASK:'+action['task_id']],
                      actions=[action['id']])
    case.version+=1
    case.save(update_fields=['version'])
    with pytest.raises(UnsafeAIAnswer,match='STALE_OR_UNAUTHORIZED_CONTEXT'):
        validate_answer(grounded,ctx,actor=user,case_id=case.pk)


@pytest.mark.django_db(transaction=True)
def test_laundered_valid_citation_falls_back_without_mutation_or_raw_output(
        active_case,monkeypatch):
    case,actors=active_case
    user=actors['MANAGER'][0]
    before=TaskCompletion.objects.count()
    monkeypatch.setenv('EOC_AI_PROVIDER','OPENAI')
    monkeypatch.setenv('OPENAI_API_KEY','offline-synthetic-no-billing-token')
    def fake_infer(ctx,_question):
        a=ctx['eligible_actions'][0]
        other=next(s for s in ctx['sources'] if s!='TASK:'+a['task_id'])
        data=proposed(ctx,citations=[other],actions=[a['id']])
        return data,{'model':'offline-mock','response_id':'synthetic',
            'input_tokens':2,'output_tokens':2}
    monkeypatch.setattr('backend.ai.answers.infer',fake_infer)
    result=answer_question(user,case.pk,'Which task can I begin?')
    assert result['mode']=='DETERMINISTIC_FALLBACK'
    assert not result['ai_model_used']
    assert result['error_code']=='MODEL_OUTPUT_REJECTED'
    assert TaskCompletion.objects.count()==before
    assert AuditEvent.objects.filter(event_type='AI_MODEL_ATTEMPT').count()==1
    failures=AuditEvent.objects.filter(event_type='AI_MODEL_FAILED')
    assert failures.count()==1
    assert not AuditEvent.objects.filter(event_type='AI_MODEL_VALIDATED').exists()
    assert 'offline-mock' not in str(list(failures.values('sanitized_change')))
