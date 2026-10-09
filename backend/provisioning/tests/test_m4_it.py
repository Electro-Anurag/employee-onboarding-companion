"""Live PostgreSQL qualification for isolated synthetic IT operation lifecycle."""
import uuid
import pytest
import json
import time
from django.test import Client
from django.db import DatabaseError,transaction
from backend.onboarding.tests.test_m2_workflow import world,create
from backend.templates.services import create_template,publish_template
from backend.onboarding.models import OnboardingCase,Task
from backend.onboarding.commands import activate_case
from backend.provisioning.commands import request_it,simulate_fulfillment,confirm_it,receive_equipment,record_simulated_failure
from backend.provisioning.models import ITOperation,ITConfirmation,EquipmentReceipt,ITSimulationFailure
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

@pytest.mark.django_db(transaction=True)
def test_simulated_failures_preserve_pending_task_then_success_requires_human_it_confirmation(world):
    org,people=world
    draft=create_template(actor=people['HR'][0],key='it_retry',name='Synthetic retryable IT',
      tasks=[dict(key='independent_access',kind='ACCESS',owner_role='IT',
        title='Synthetic IT access',required=True,available_offset_days=-30,due_offset_days=0,
        evidence_spec={'type':'ACCESS'})],edges=[])
    version=publish_template(actor=people['HR'][0],
        template_id=uuid.UUID(draft['id']),revision=1)
    made,_=create(world,uuid.UUID(version['version_id']))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,
        key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='independent_access')
    request_it(actor=people['IT'][0],case_id=case.pk,task_id=task.pk,
        key=uuid.uuid4(),expected_version=2)
    first_args=dict(actor=people['IT'][0],case_id=case.pk,task_id=task.pk,
        cause='SIMULATED_TIMEOUT',note='Synthetic provider did not respond',
        expected_version=3)
    with pytest.raises(CommandFailure) as invalid:
        record_simulated_failure(**{**first_args,'actor':people['HR'][0]},
            key=uuid.uuid4())
    assert invalid.value.code=='NOT_FOUND'
    op=ITOperation.objects.get(task=task)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ITSimulationFailure.objects.create(operation=op,sequence=1,
                reported_by=people['HR'][0],cause='SIMULATED_TIMEOUT',
                note='Forged cross-role failure record')
    key=uuid.uuid4()
    first,status=record_simulated_failure(**first_args,key=key)
    assert status==201 and first['result']['failure_sequence']==1
    assert record_simulated_failure(**first_args,key=key)[0]==first
    assert first['result']['retry_explicitly_available'] is True
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    assert TaskCompletion.objects.count()==0
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ITSimulationFailure.objects.filter(pk=first['result']['failure_id']).update(
                note='forged correction')
    second,status=record_simulated_failure(actor=people['IT'][0],
        case_id=case.pk,task_id=task.pk,cause='PROVIDER_UNAVAILABLE',
        note='Synthetic provider is still unavailable',
        key=uuid.uuid4(),expected_version=4)
    assert status==201 and second['result']['failure_sequence']==2
    assert TaskCompletion.objects.count()==0
    result,status=simulate_fulfillment(actor=people['IT'][0],case_id=case.pk,
        task_id=task.pk,note='Synthetic provider retry succeeded',
        key=uuid.uuid4(),expected_version=5)
    assert status==200 and result['result']['state']=='SIMULATED_FULFILLED'
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    assert TaskCompletion.objects.count()==0
    with pytest.raises(CommandFailure) as late:
        record_simulated_failure(actor=people['IT'][0],case_id=case.pk,
            task_id=task.pk,cause='SIMULATED_REJECTION',
            note='Should not fail a successful operation',
            key=uuid.uuid4(),expected_version=6)
    assert late.value.code=='IT_PENDING_REQUEST_REQUIRED'
    done,status=confirm_it(actor=people['IT'][0],case_id=case.pk,task_id=task.pk,
        note='Human IT signoff on synthetic retry success',
        key=uuid.uuid4(),expected_version=6)
    assert status==200 and done['result']['state']=='COMPLETED'
    assert Task.objects.get(pk=task.pk).completion.evidence_type=='IT_CONFIRMATION'
    assert ITSimulationFailure.objects.filter(operation=op).count()==2
    assert AuditEvent.objects.filter(event_type='IT_SIMULATION_FAILED').count()==2
    assert CommandReceipt.objects.filter(route='m4-it-failure').count()==2
    assert OnboardingCase.objects.get(pk=case.pk).version==7

@pytest.mark.django_db(transaction=True)
def test_failed_it_attempt_api_is_role_scoped_and_replayable(world):
    org,people=world
    draft=create_template(actor=people['HR'][0],key='it_fail_http',name='Synthetic failure',
        tasks=[dict(key='device',kind='EQUIPMENT',owner_role='IT',
            title='Synthetic test equipment',required=True,
            available_offset_days=-30,due_offset_days=0,
            evidence_spec={'type':'EQUIPMENT'})],edges=[])
    version=publish_template(actor=people['HR'][0],
        template_id=uuid.UUID(draft['id']),revision=1)
    made,_=create(world,uuid.UUID(version['version_id']))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,
        key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='device')
    request_it(actor=people['IT'][0],case_id=case.pk,task_id=task.pk,
        key=uuid.uuid4(),expected_version=2)
    base=f'/api/v1/cases/{case.pk}/tasks/{task.pk}/it-operation'
    def client(role):
        c=Client()
        c.force_login(people[role][0])
        session=c.session
        session['m1_session_started']=time.time()
        session.save()
        return c
    it=client('IT')
    employee=client('EMPLOYEE')
    assert employee.get(base).status_code==404
    result=it.post(base+'/simulated-failure',
        data=json.dumps({'cause':'SIMULATED_REJECTION',
                        'note':'Simulated provider rejected the synthetic device'}),
        content_type='application/json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v3"')
    assert result.status_code==201,result.content
    assert result.json()['result']['task_completion']=='IN_PROGRESS'
    info=it.get(base)
    assert info.status_code==200
    assert info.json()['state']=='REQUESTED'
    assert len(info.json()['failures'])==1
    assert info.json()['failures'][0]['cause']=='SIMULATED_REJECTION'
    assert info.json()['retry_explicitly_available'] is True
    assert employee.get(base).status_code==404
    assert TaskCompletion.objects.count()==0

@pytest.mark.django_db(transaction=True)
def test_generic_start_keeps_typed_it_and_equipment_receipt_reachable(world):
    from backend.onboarding.commands import start_task
    org,people=world
    draft=create_template(actor=people['HR'][0],key='started_equipment',
        name='Generic Start followed by typed workflow',tasks=[
        dict(key='device',kind='EQUIPMENT',owner_role='IT',
            title='Synthetic equipment',required=True,available_offset_days=-30,
            due_offset_days=1,evidence_spec={'type':'EQUIPMENT'}),
        dict(key='receipt',kind='EQUIPMENT_RECEIPT',owner_role='EMPLOYEE',
            title='Acknowledge synthetic equipment',required=True,
            available_offset_days=-30,due_offset_days=1,
            evidence_spec={'type':'EQUIPMENT_RECEIPT'})],
        edges=[{'predecessor':'device','successor':'receipt'}])
    version=publish_template(actor=people['HR'][0],template_id=uuid.UUID(draft['id']),revision=1)
    made,_=create(world,uuid.UUID(version['version_id']))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    device=Task.objects.get(case=case,key='device')
    receipt=Task.objects.get(case=case,key='receipt')
    start_task(actor=people['IT'][0],case_id=case.pk,task_id=device.pk,
        key=uuid.uuid4(),expected_version=2)
    initial,_=request_it(actor=people['IT'][0],case_id=case.pk,task_id=device.pk,
        key=uuid.uuid4(),expected_version=3)
    assert initial['result']['provider']=='SYNTHETIC_ONLY'
    simulate_fulfillment(actor=people['IT'][0],case_id=case.pk,task_id=device.pk,
        note='Test adapter only',key=uuid.uuid4(),expected_version=4)
    signed,_=confirm_it(actor=people['IT'][0],case_id=case.pk,task_id=device.pk,
        note='Human test confirmation',key=uuid.uuid4(),expected_version=5)
    receipt.refresh_from_db()
    assert receipt.execution_state=='READY'
    start_task(actor=people['EMPLOYEE'][0],case_id=case.pk,task_id=receipt.pk,
        key=uuid.uuid4(),expected_version=6)
    final,_=receive_equipment(actor=people['EMPLOYEE'][0],case_id=case.pk,
        task_id=receipt.pk,it_confirmation_id=uuid.UUID(signed['result']['confirmation_id']),
        note='Synthetic device received by employee',key=uuid.uuid4(),expected_version=7)
    assert final['result']['state']=='COMPLETED'
    assert TaskCompletion.objects.filter(task__in=[device,receipt]).count()==2
