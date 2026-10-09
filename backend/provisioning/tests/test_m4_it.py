"""Live PostgreSQL qualification for isolated synthetic IT operation lifecycle."""
import uuid
import pytest
from django.db import DatabaseError,transaction
from backend.onboarding.tests.test_m2_workflow import world,create
from backend.templates.services import create_template,publish_template
from backend.onboarding.models import OnboardingCase,Task
from backend.onboarding.commands import activate_case
from backend.provisioning.commands import request_it,simulate_fulfillment
from backend.provisioning.models import ITOperation
from backend.onboarding.services import CommandFailure
from backend.audit.models import CommandReceipt,AuditEvent

@pytest.mark.django_db(transaction=True)
def test_simulated_it_persistence_idempotency_and_no_false_completion(world):
    org,p=world
    draft=create_template(actor=p['HR'][0],key='it_only',name='Synthetic IT only',
      tasks=[dict(key='independent_access',kind='ACCESS',owner_role='IT',
          title='Synthetic access',required=True,available_offset_days=-30,due_offset_days=0,
          evidence_spec={'type':'ACCESS'})],edges=[])
    version=publish_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),revision=1)
    made,_=create(world,uuid.UUID(version['version_id']))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='independent_access')
    assert task.execution_state=='READY'
    with pytest.raises(CommandFailure):
        request_it(actor=p['HR'][0],case_id=case.pk,task_id=task.pk,key=uuid.uuid4(),expected_version=2)
    assert ITOperation.objects.count()==0
    reqkey=uuid.uuid4()
    first,status=request_it(actor=p['IT'][0],case_id=case.pk,task_id=task.pk,key=reqkey,expected_version=2)
    assert status==201 and first['result']['provider']=='SYNTHETIC_ONLY'
    assert request_it(actor=p['IT'][0],case_id=case.pk,task_id=task.pk,key=reqkey,expected_version=2)[0]==first
    assert OnboardingCase.objects.get(pk=case.pk).version==3
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    with pytest.raises(CommandFailure) as exc:
        simulate_fulfillment(actor=p['MANAGER'][0],case_id=case.pk,task_id=task.pk,note='bad',
                         key=uuid.uuid4(),expected_version=3)
    assert exc.value.code=='NOT_FOUND'
    done,status=simulate_fulfillment(actor=p['IT'][0],case_id=case.pk,task_id=task.pk,
                         note='synthetic adapter only',key=uuid.uuid4(),expected_version=3)
    assert status==200 and done['result']['state']=='SIMULATED_FULFILLED'
    op=ITOperation.objects.get(task=task)
    assert len(op.simulation_digest)==64
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    assert OnboardingCase.objects.get(pk=case.pk).version==4
    assert not hasattr(Task.objects.get(pk=task.pk),'completion')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ITOperation.objects.filter(pk=op.pk).update(status='REQUESTED')
    assert AuditEvent.objects.filter(event_type='IT_SIMULATED').count()==1
    assert CommandReceipt.objects.filter(route='m4-it-simulate').count()==1
