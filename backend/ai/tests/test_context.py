"""M6 source/eligibility validator tests: never claims real model qualification."""
import uuid
import pytest
from backend.onboarding.models import OnboardingCase
from backend.onboarding.commands import activate_case
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.ai.context import authorized_context
from backend.ai.validator import validate_answer,UnsafeAIAnswer
from backend.onboarding.services import CommandFailure


@pytest.mark.django_db(transaction=True)
def test_m6_authorized_context_validated_no_writes_or_invented_citations(world):
    org,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    context=authorized_context(actors['MANAGER'][0],case.pk)
    assert context['case_version']==2
    assert len(context['tasks'])==17
    assert context['sources'] and all(x.startswith('TASK:') for x in context['sources'])
    assert 'employee_email' not in str(context)
    assert 'document_bytes' not in str(context)
    payload={'answer_type':'SUPPORTED','answer':'The assigned owner can begin the currently ready work.',
        'citations':[context['sources'][0]],'recommended_actions':[],
        'blockers':[],'clarification':None,'escalation_draft':None,'limitations':[]}
    assert validate_answer(payload,context,actor=actors['MANAGER'][0],case_id=case.pk)['answer_type']=='SUPPORTED'
    with pytest.raises(UnsafeAIAnswer,match='UNSUPPORTED_CITATIONS'):
        validate_answer({**payload,'citations':['TASK:untrusted']},context,
            actor=actors['MANAGER'][0],case_id=case.pk)
    with pytest.raises(UnsafeAIAnswer,match='UNSUPPORTED_RECOMMENDED_ACTIONS'):
        validate_answer({**payload,'recommended_actions':['ACTION:make-up:approve']},context,
            actor=actors['MANAGER'][0],case_id=case.pk)
    with pytest.raises(UnsafeAIAnswer,match='INVALID_OUTPUT_SHAPE'):
        validate_answer({**payload,'tool_call':'auto_accept_document'},context,
            actor=actors['MANAGER'][0],case_id=case.pk)
    # A workflow mutation invalidates the approved context at publication.
    case.refresh_from_db()
    case.version+=1
    case.save(update_fields=['version'])
    with pytest.raises(UnsafeAIAnswer,match='STALE_OR_UNAUTHORIZED_CONTEXT'):
        validate_answer(payload,context,actor=actors['MANAGER'][0],case_id=case.pk)
    with pytest.raises(CommandFailure):
        authorized_context(actors['IT'][0],uuid.uuid4())


@pytest.mark.django_db(transaction=True)
def test_m6_current_guidance_uses_real_prerequisites_and_denies_unassigned_user(world):
    from backend.ai.guidance import current_guidance
    from backend.accounts.models import User,Membership
    from backend.onboarding.models import Task,TaskCompletion
    from django.test import Client
    _,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
        key=uuid.uuid4(),expected_version=1)
    before=TaskCompletion.objects.count()
    data=current_guidance(actors['MANAGER'][0],case.pk)
    assert data['mode']=='DETERMINISTIC_ONLY' and data['ai_model_used'] is False
    assert data['case_version']==2
    assert any(x['task_title']=='Manager Preparation' for x in data['actionable'])
    intro=next(x for x in data['blockers'] if x['task_title']=='Team Introduction')
    assert any(p['task_title']=='Manager Preparation'
               for p in intro['unmet_prerequisites'])
    assert TaskCompletion.objects.count()==before
    outsider=User.objects.create_user(email='noncase@example.test',
        password='VerifiedStrongPassword!2026',display_name='Not assigned')
    Membership.objects.create(user=outsider,organization=case.organization,role='IT')
    with pytest.raises(CommandFailure):
        current_guidance(outsider,case.pk)
    c=Client()
    c.post('/api/v1/auth/login',
        data=__import__('json').dumps({'email':actors['MANAGER'][0].email,
             'password':'VerifiedStrongPassword!2026'}),
        content_type='application/json')
    response=c.get(f'/api/v1/cases/{case.pk}/companion/guidance')
    assert response.status_code==200,response.content
    assert response.json()['mode']=='DETERMINISTIC_ONLY'
    assert TaskCompletion.objects.count()==before
