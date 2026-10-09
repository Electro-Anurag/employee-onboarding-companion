"""Live database and HTTP contract for exact frozen synthetic policy editions."""
import json
import time
import uuid
import pytest
from django.db import DatabaseError,transaction
from django.test import Client
from backend.onboarding.tests.test_m2_workflow import world,create,published
from backend.onboarding.models import OnboardingCase,Task,TaskCompletion
from backend.onboarding.commands import activate_case
from backend.onboarding.services import CommandFailure
from backend.policies.models import PolicyAcknowledgement
from backend.policies.commands import acknowledge,validated_policy
from backend.audit.models import AuditEvent,CommandReceipt

@pytest.mark.django_db(transaction=True)
def test_policy_ack_is_exact_version_bound_idempotent_and_immutable(world):
    org,actors=world
    case_resp,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=case_resp['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='conduct_ack')
    assert task.execution_state=='READY'
    policy=validated_policy(task)
    assert policy['version']=='synthetic-conduct-v1'
    assert len(policy['content_sha256'])==64 and 'Synthetic' in policy['text']
    base=dict(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
              policy_version=policy['version'],content_sha256=policy['content_sha256'],
              accepted=True,expected_version=2)
    with pytest.raises(CommandFailure) as forbidden:
        acknowledge(**{**base,'actor':actors['HR'][0]},key=uuid.uuid4())
    assert forbidden.value.code=='NOT_FOUND'
    with pytest.raises(CommandFailure) as rejected:
        acknowledge(**{**base,'content_sha256':'0'*64},key=uuid.uuid4())
    assert rejected.value.code=='STALE_POLICY_EDITION'
    with pytest.raises(CommandFailure) as absent_acceptance:
        acknowledge(**{**base,'accepted':False},key=uuid.uuid4())
    assert absent_acceptance.value.code=='EXPLICIT_POLICY_ACCEPTANCE_REQUIRED'
    assert PolicyAcknowledgement.objects.count()==0 and TaskCompletion.objects.count()==0
    key=uuid.uuid4()
    response,code=acknowledge(**base,key=key)
    assert code==200 and response['result']['state']=='COMPLETED'
    assert response['result']['progress']['mandatory_completed']==1
    assert acknowledge(**base,key=key)[0]==response
    current=Task.objects.get(pk=task.pk)
    proof=current.completion
    assert proof.evidence_type=='POLICY_ACK'
    assert proof.policy_ack_id==uuid.UUID(response['result']['acknowledgement_id'])
    assert OnboardingCase.objects.get(pk=case.pk).version==3
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            PolicyAcknowledgement.objects.filter(pk=proof.policy_ack_id).update(content_sha256='0'*64)
    assert PolicyAcknowledgement.objects.get(pk=proof.policy_ack_id).content_sha256==policy['content_sha256']
    assert CommandReceipt.objects.filter(route='m3-policy-ack').count()==1
    assert AuditEvent.objects.filter(event_type='TASK_COMPLETED',entity_id=task.pk).count()==1

@pytest.mark.django_db(transaction=True)
def test_policy_browser_api_never_exposes_version_to_it_or_wrong_case(world):
    org,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='privacy_ack')
    url=f'/api/v1/cases/{case.pk}/tasks/{task.pk}/assigned-policy'
    def client_for(role):
        c=Client()
        c.force_login(actors[role][0])
        session=c.session
        session['m1_session_started']=time.time()
        session.save()
        return c
    employee=client_for('EMPLOYEE')
    policy_response=employee.get(url)
    assert policy_response.status_code==200,policy_response.content
    content=policy_response.json()['policy']
    assert content['version']=='synthetic-privacy-v1'
    assert client_for('HR').get(url).status_code==200
    assert client_for('IT').get(url).status_code==404
    assert client_for('MANAGER').get(url).status_code==404
    path=f'/api/v1/cases/{case.pk}/tasks/{task.pk}/policy-acknowledge'
    post=employee.post(path,content_type='application/json',
        data=json.dumps({'policy_version':content['version'],
            'content_sha256':content['content_sha256'],'accepted':True}),
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH=f'"case:{case.pk}:v2"')
    assert post.status_code==200,post.content
    assert employee.get(url).json()['acknowledged'] is True
    assert Task.objects.get(pk=task.pk).completion.evidence_type=='POLICY_ACK'
