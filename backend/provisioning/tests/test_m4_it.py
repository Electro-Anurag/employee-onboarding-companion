"""Live PostgreSQL qualification for isolated synthetic IT operation lifecycle."""
import uuid
import pytest
from django.db import DatabaseError,transaction
from backend.onboarding.tests.test_m2_workflow import world,create
from backend.templates.services import create_template,publish_template
from backend.onboarding.models import OnboardingCase,Task
from backend.onboarding.commands import activate_case
from backend.provisioning.commands import request_it,simulate_fulfillment,confirm_it,receive_equipment
from backend.provisioning.models import ITOperation,ITConfirmation,EquipmentReceipt
from backend.onboarding.models import TaskCompletion
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

@pytest.mark.django_db(transaction=True)
def test_human_it_confirmation_is_distinct_from_simulation_and_idempotent(world):
    org,p=world
    draft=create_template(actor=p['HR'][0],key='it_confirmation',name='Synthetic IT confirmation',
      tasks=[dict(key='access',kind='ACCESS',owner_role='IT',title='Account access',required=True,
       available_offset_days=-30,due_offset_days=0,evidence_spec={'type':'ACCESS'})],edges=[])
    version=publish_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),revision=1)
    made,_=create(world,uuid.UUID(version['version_id']))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='access')
    request_it(actor=p['IT'][0],case_id=case.pk,task_id=task.pk,key=uuid.uuid4(),expected_version=2)
    with pytest.raises(CommandFailure) as not_yet:
        confirm_it(actor=p['IT'][0],case_id=case.pk,task_id=task.pk,note='I confirm this task',
                   key=uuid.uuid4(),expected_version=3)
    assert not_yet.value.code=='SIMULATED_RESULT_REQUIRED'
    assert ITConfirmation.objects.count()==0 and TaskCompletion.objects.count()==0
    simulate_fulfillment(actor=p['IT'][0],case_id=case.pk,task_id=task.pk,
        note='Only a synthetic provider',key=uuid.uuid4(),expected_version=3)
    with pytest.raises(CommandFailure):
        confirm_it(actor=p['HR'][0],case_id=case.pk,task_id=task.pk,
                   note='Unauthorized confirmation',key=uuid.uuid4(),expected_version=4)
    key=uuid.uuid4()
    response,status=confirm_it(actor=p['IT'][0],case_id=case.pk,task_id=task.pk,
        note='Personally verify the simulated outcome',key=key,expected_version=4)
    assert status==200 and response['result']['state']=='COMPLETED'
    assert response['result']['external_fulfillment_verified'] is False
    assert confirm_it(actor=p['IT'][0],case_id=case.pk,task_id=task.pk,
        note='Personally verify the simulated outcome',key=key,expected_version=4)[0]==response
    assert OnboardingCase.objects.get(pk=case.pk).version==5
    assert Task.objects.get(pk=task.pk).completion.it_confirmation_id==uuid.UUID(response['result']['confirmation_id'])
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ITConfirmation.objects.filter(pk=response['result']['confirmation_id']).update(note='tampering')
    assert TaskCompletion.objects.count()==1

@pytest.mark.django_db(transaction=True)
def test_employee_equipment_receipt_requires_confirmed_same_case_evidence(world):
    org,p=world
    draft=create_template(actor=p['HR'][0],key='equipment_handover',name='Synthetic equipment',
      tasks=[
        dict(key='device',kind='EQUIPMENT',owner_role='IT',title='Synthetic device',
             required=True,available_offset_days=-30,due_offset_days=1,evidence_spec={'type':'EQUIPMENT'}),
        dict(key='device_receipt',kind='EQUIPMENT_RECEIPT',owner_role='EMPLOYEE',
             title='Synthetic equipment receipt',required=True,available_offset_days=-30,
             due_offset_days=1,evidence_spec={'type':'EQUIPMENT_RECEIPT'})],
      edges=[{'predecessor':'device','successor':'device_receipt'}])
    version=publish_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),revision=1)
    made,_=create(world,uuid.UUID(version['version_id']))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    equipment=Task.objects.get(case=case,key='device')
    receipt_task=Task.objects.get(case=case,key='device_receipt')
    assert receipt_task.execution_state=='BLOCKED'
    request_it(actor=p['IT'][0],case_id=case.pk,task_id=equipment.pk,key=uuid.uuid4(),expected_version=2)
    simulate_fulfillment(actor=p['IT'][0],case_id=case.pk,task_id=equipment.pk,
        note='synthetic',key=uuid.uuid4(),expected_version=3)
    with pytest.raises(CommandFailure) as blocked:
        receive_equipment(actor=p['EMPLOYEE'][0],case_id=case.pk,task_id=receipt_task.pk,
            it_confirmation_id=uuid.uuid4(),note='Received a synthetic device',
            key=uuid.uuid4(),expected_version=4)
    assert blocked.value.code=='TASK_NOT_READY'
    done,_=confirm_it(actor=p['IT'][0],case_id=case.pk,task_id=equipment.pk,
        note='Human IT confirmation recorded',key=uuid.uuid4(),expected_version=4)
    receipt_task.refresh_from_db()
    assert receipt_task.execution_state=='READY'
    confirmation=uuid.UUID(done['result']['confirmation_id'])
    with pytest.raises(CommandFailure) as wrong_role:
        receive_equipment(actor=p['IT'][0],case_id=case.pk,task_id=receipt_task.pk,
            it_confirmation_id=confirmation,note='Received a synthetic device',
            key=uuid.uuid4(),expected_version=5)
    assert wrong_role.value.code=='NOT_FOUND'
    confirmed,code=receive_equipment(actor=p['EMPLOYEE'][0],case_id=case.pk,task_id=receipt_task.pk,
        it_confirmation_id=confirmation,note='Received a synthetic device',
        key=uuid.uuid4(),expected_version=5)
    assert code==200 and confirmed['result']['state']=='COMPLETED'
    assert confirmed['result']['progress']['mandatory_completed']==2
    assert EquipmentReceipt.objects.count()==1 and TaskCompletion.objects.count()==2
    assert Task.objects.get(pk=receipt_task.pk).completion.equipment_receipt_id==uuid.UUID(confirmed['result']['receipt_id'])
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            EquipmentReceipt.objects.filter(pk=confirmed['result']['receipt_id']).update(note='tampered')
    assert OnboardingCase.objects.get(pk=case.pk).version==6
