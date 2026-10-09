"""Live M4 synthetic module grading, immutable attempt history and role scope."""
import json
import time
import uuid
import pytest
from django.db import DatabaseError,transaction
from django.test import Client
from backend.onboarding.tests.test_m2_workflow import world,create
from backend.templates.services import create_template,publish_template
from backend.training.definitions import default_spec,public_spec
from backend.training.commands import attempt
from backend.training.models import TrainingAttempt
from backend.onboarding.commands import activate_case
from backend.onboarding.models import OnboardingCase,Task,TaskCompletion
from backend.onboarding.services import CommandFailure
from backend.audit.models import CommandReceipt,AuditEvent

@pytest.mark.django_db(transaction=True)
def test_synthetic_training_fails_then_passes_without_premature_completion(world):
    org,people=world
    spec=default_spec('security_training')
    draft=create_template(actor=people['HR'][0],key='training_demo',
       name='Synthetic grading',tasks=[dict(key='training_exam',kind='TRAINING',
       title='Training exam',required=True,owner_role='EMPLOYEE',
       available_offset_days=-30,due_offset_days=1,evidence_spec=spec)],edges=[])
    published=publish_template(actor=people['HR'][0],template_id=uuid.UUID(draft['id']),revision=1)
    made,_=create(world,uuid.UUID(published['version_id']))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='training_exam')
    assert task.execution_state=='READY'
    assert all('answer' not in q for q in public_spec(spec)['questions'])
    base=dict(actor=people['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
       module_version=spec['module_version'],content_sha256=spec['content_sha256'],
       expected_version=2)
    with pytest.raises(CommandFailure) as unauthorized:
        attempt(**{**base,'actor':people['MANAGER'][0]},
              answers={'q1':'A','q2':'B'},key=uuid.uuid4())
    assert unauthorized.value.code=='NOT_FOUND'
    with pytest.raises(CommandFailure) as forged:
        attempt(**{**base,'content_sha256':'f'*64},
              answers={'q1':'A','q2':'B'},key=uuid.uuid4())
    assert forged.value.code=='STALE_TRAINING_MODULE'
    with pytest.raises(CommandFailure) as impossible:
        attempt(**base,answers={'q1':'Z','q2':'B'},key=uuid.uuid4())
    assert impossible.value.code=='INVALID_TRAINING_ANSWERS'
    failed,status=attempt(**base,answers={'q1':'B','q2':'B'},key=uuid.uuid4())
    assert status==200 and failed['result']['passed'] is False
    assert failed['result']['score']==1
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    assert TaskCompletion.objects.count()==0
    key=uuid.uuid4()
    success,status=attempt(**{**base,'expected_version':3},
         answers={'q1':'A','q2':'B'},key=key)
    assert status==200 and success['result']['passed'] is True
    assert success['result']['task_completion']=='COMPLETED'
    assert attempt(**{**base,'expected_version':3},
         answers={'q1':'A','q2':'B'},key=key)[0]==success
    assert success['result']['progress']['mandatory_completed']==1
    assert Task.objects.get(pk=task.pk).completion.evidence_type=='TRAINING'
    assert TrainingAttempt.objects.filter(task=task).count()==2
    assert OnboardingCase.objects.get(pk=case.pk).version==4
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            TrainingAttempt.objects.filter(task=task,attempt_number=2).update(passed=False)
    assert CommandReceipt.objects.filter(route='m4-training-attempt').count()==2
    assert AuditEvent.objects.filter(event_type='TRAINING_ATTEMPT_GRADED').count()==2

@pytest.mark.django_db(transaction=True)
def test_training_http_hides_answer_key_and_uses_actual_session_authority(world):
    org,people=world
    spec=default_spec('workplace_training')
    draft=create_template(actor=people['HR'][0],key='workplace_exam',
       name='Synthetic workplace',tasks=[dict(key='workplace_exam',kind='TRAINING',
       title='Workplace exam',required=True,owner_role='EMPLOYEE',
       available_offset_days=-30,due_offset_days=1,evidence_spec=spec)],edges=[])
    published=publish_template(actor=people['HR'][0],template_id=uuid.UUID(draft['id']),revision=1)
    made,_=create(world,uuid.UUID(published['version_id']))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='workplace_exam')
    base=f'/api/v1/cases/{case.pk}/tasks/{task.pk}'
    def client(role):
        c=Client()
        c.force_login(people[role][0])
        session=c.session
        session['m1_session_started']=time.time()
        session.save()
        return c
    emp=client('EMPLOYEE')
    hr=client('HR')
    it=client('IT')
    module=emp.get(base+'/training-module')
    assert module.status_code==200,module.content
    assert 'answer' not in module.content.decode().lower()
    assert hr.get(base+'/training-module').status_code==200
    assert it.get(base+'/training-module').status_code==404
    wrong=emp.post(base+'/training-attempts',
        data=json.dumps({'module_version':spec['module_version'],
               'content_sha256':'0'*64,'answers':{'q1':'A','q2':'A'}}),
        content_type='application/json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v2"')
    assert wrong.status_code==409
    res=emp.post(base+'/training-attempts',
        data=json.dumps({'module_version':spec['module_version'],
               'content_sha256':spec['content_sha256'],'answers':{'q1':'A','q2':'A'}}),
        content_type='application/json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v2"')
    assert res.status_code==200,res.content
    assert res.json()['result']['passed'] is True
    assert emp.get(base+'/training-module').json()['task_state']=='COMPLETED'
    assert TaskCompletion.objects.get(task=task).evidence_type=='TRAINING'
