"""Live S3-versioning and actual clamd qualification (never runs without services).

This uses generated PDFs and the standard EICAR anti-malware test signature,
not real employee data. A healthy actual ClamAV daemon is REQUIRED.
"""
import hashlib
import os
import uuid
import pytest
from django.conf import settings
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.onboarding.commands import activate_case
from backend.onboarding.models import Task,OnboardingCase,TaskCompletion
from backend.documents.tests.test_secure_s3_journey import generated_pdf
from backend.documents.real_commands import prepare,receive,scan_one,review
from backend.documents.real_models import SecureCleanObject,SecureScanAttempt
from backend.documents import storage
from backend.documents.scanner import clamav_signature_provenance

pytestmark=pytest.mark.skipif(os.getenv('M3_LIVE_S3_CLAMAV')!='1',
    reason='Requires live versioned MinIO/S3 and ClamAV daemon')

EICAR=(b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$'
       b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')

@pytest.mark.django_db(transaction=True)
def test_live_s3_exact_versions_and_actual_antivirus_rejection_then_hr_approval(world):
    org,actors=world
    assert settings.M3_REAL_DOCUMENT_ENABLED
    assert clamav_signature_provenance().startswith('ClamAV ')
    s3=storage.client()
    q,clean=storage.buckets(s3)
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    equipment=Task.objects.get(case=case,key='equipment_setup')
    assert equipment.execution_state=='BLOCKED'
    raw=generated_pdf()
    attack=raw.replace(b'%%EOF',b'%'+EICAR+b'\\n%%EOF')
    attack=attack.replace(b'\\n%%EOF',b'\n%%EOF')
    # Must still be a well-formed PDF for the scanner security gate.
    from backend.documents.pdf_validation import validate_pdf
    validate_pdf(attack)
    v1,_=prepare(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        sha256=hashlib.sha256(attack).hexdigest(),size=len(attack),
        filename='eicar_generated.pdf',key=uuid.uuid4(),expected_version=2)
    id1=uuid.UUID(v1['result']['upload_id'])
    received,_=receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        upload_id=id1,raw=attack,key=uuid.uuid4(),expected_version=3)
    assert received['result']['state']=='QUARANTINED'
    assert not SecureCleanObject.objects.filter(upload_id=id1).exists()
    malicious=scan_one(id1)
    assert malicious['state']=='REJECTED_SECURITY',malicious
    assert SecureScanAttempt.objects.get(upload_id=id1).outcome=='MALWARE'
    assert TaskCompletion.objects.count()==0
    normal,_=prepare(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
        filename='generated_replacement.pdf',key=uuid.uuid4(),expected_version=4)
    id2=uuid.UUID(normal['result']['upload_id'])
    received,_=receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        upload_id=id2,raw=raw,key=uuid.uuid4(),expected_version=5)
    assert received['result']['state']=='QUARANTINED'
    clean_result=scan_one(id2)
    assert clean_result['state']=='AWAITING_HR_REVIEW',clean_result
    obj=SecureCleanObject.objects.get(upload_id=id2)
    assert obj.version_id and obj.version_id!='null'
    assert storage.download(obj)==raw
    assert s3.head_object(Bucket=clean,Key=obj.object_key,VersionId=obj.version_id)['ContentLength']==len(raw)
    accepted,_=review(actor=actors['HR'][0],case_id=case.pk,task_id=task.pk,
        upload_id=id2,decision='ACCEPTED',note='Real scanner and exact S3 version qualified',
        key=uuid.uuid4(),expected_version=6)
    assert accepted['result']['task_completion']=='COMPLETED'
    assert TaskCompletion.objects.get(task=task).evidence_type=='SECURE_DOCUMENT'
    assert Task.objects.get(pk=equipment.pk).execution_state=='BLOCKED'
    assert not SecureCleanObject.objects.filter(upload_id=id1).exists()
