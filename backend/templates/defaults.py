"""Synthetic Aster Vale Labs onboarding template, not a real employer policy."""
from backend.policies.definitions import policy_evidence
from backend.training.definitions import default_spec
SPEC=[
('identity_document','DOCUMENT','EMPLOYEE',-30,-5,()),
('employment_document','DOCUMENT','EMPLOYEE',-30,-5,()),
('personal_details','FORM','EMPLOYEE',-30,-5,()),
('conduct_ack','POLICY_ACK','EMPLOYEE',-30,0,()),
('privacy_ack','POLICY_ACK','EMPLOYEE',-30,0,()),
('manager_preparation','MANAGER_PREPARATION','MANAGER',-30,-1,()),
('equipment_setup','EQUIPMENT','IT',-30,-1,('identity_document','personal_details')),
('workspace_access','ACCESS','IT',-30,0,('identity_document','conduct_ack')),
('equipment_receipt','EQUIPMENT_RECEIPT','EMPLOYEE',0,1,('equipment_setup',)),
('day1_induction','ACTIVITY','HR',0,0,()),
('team_introduction','INTRODUCTION','MANAGER',0,2,('manager_preparation',)),
('security_training','TRAINING','EMPLOYEE',0,5,('workspace_access','privacy_ack')),
('benefits_ack','POLICY_ACK','EMPLOYEE',0,5,()),
('week1_checkin','CHECK_IN','MANAGER',3,7,('team_introduction',)),
('workplace_training','TRAINING','EMPLOYEE',0,10,('conduct_ack',)),
('week3_checkin','CHECK_IN','MANAGER',14,21,('week1_checkin',)),
('month1_checkin','CHECK_IN','MANAGER',21,30,('week3_checkin','security_training','workplace_training')),
]
def first_month_template():
    tasks=[]
    edges=[]
    for position,(key,kind,owner,available,due,prereqs) in enumerate(SPEC):
        title=' '.join(part.capitalize() if part!='day1' else 'Day 1' for part in key.split('_'))
        tasks.append(dict(key=key,kind=kind,title=title,description='Synthetic onboarding work',
            owner_role=owner,required=True,available_offset_days=available,
            due_offset_days=due,position=position,evidence_spec=({'type':'FORM','fields':['preferred_name','contact_email']}
                if kind=='FORM' and key=='personal_details' else
                policy_evidence(key) if kind=='POLICY_ACK' else
                default_spec(key) if kind=='TRAINING' else {'type':kind})))
        for before in prereqs:
            edges.append({'predecessor':before,'successor':key})
    return tasks,edges
