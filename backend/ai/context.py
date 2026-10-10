"""Owner-scoped, bounded immutable snapshot for later real AI provider admission.

Do not include identity documents, uploads, employee emails, secrets,
personal forms, quiz answers, or unapproved policies. This data stays local
until provider use is explicitly approved.
"""
import hashlib
import json
from backend.onboarding.models import Task,TaskDependency,CaseException
from backend.onboarding.services import get_authorized_case
from backend.onboarding.state_machine import summary_task
from backend.accounts.models import Membership
from backend.onboarding.services import CommandFailure
from backend.policies.commands import validated_policy


def authorized_context(actor,case_id):
    member,case=get_authorized_case(actor,case_id)
    if case.status not in ('PRE_JOINING','ACTIVE'):
        return {'case_id':str(case.pk),'case_version':case.version,
            'status':case.status,'tasks':[],'blockers':[],'open_exceptions':[],'eligible_actions':[],
            'sources':[],'policies':[],'context_digest':''}
    tasks=list(Task.objects.filter(case=case).order_by('key')[:61])
    if len(tasks)>60:
        raise ValueError('CASE_TASK_LIMIT_EXCEEDED')
    visible=[summary_task(t,member,case) for t in tasks]
    by_id={str(t.id):t for t in tasks}
    deps=list(TaskDependency.objects.filter(case=case).values_list(
        'predecessor_id','successor_id'))
    parent_of={}
    for parent,child in deps:
        parent_of.setdefault(str(child),[]).append(str(parent))
    item_rows=[]
    source_ids=[]
    blockers=[]
    actions=[]
    for task in visible:
        item={'id':task['id'],'key':task['key'],'title':task['title'],
              'kind':task['kind'],'owner_role':task['owner_role'],
              'state':task['state'],'due_at':task['due_at'],
              'blocked_reason_codes':task['blocked_reason_codes']}
        item_rows.append(item)
        source_ids.append('TASK:'+task['id'])
        if task['state']=='BLOCKED':
            parents=[by_id[pid] for pid in parent_of.get(task['id'],[]) if pid in by_id]
            pending=[str(p.pk) for p in parents if p.execution_state!='COMPLETED']
            blockers.append({'id':'BLOCKER:'+task['id'],
                'task_id':task['id'],'reason_codes':task['blocked_reason_codes'],
                'unmet_prerequisite_ids':pending})
        for action in task['allowed_actions']:
            actions.append({'id':'ACTION:'+task['id']+':'+action,
                'task_id':task['id'],'type':action})
    episodes=[]
    for ex in CaseException.objects.filter(case=case,status__in=['OPEN','ASSIGNED','RESOLVED']).order_by('opened_at','id')[:61]:
        # Exception notes are user-origin text and may contain personal data.
        # Send only current structured, explicitly authorized provenance.
        episodes.append({'id':'EXCEPTION:'+str(ex.pk),
            'task_id':str(ex.task_id),'cause':ex.cause,
            'status':ex.status,'episode':ex.episode,
            'assignee_role':ex.assignee.role if ex.assignee_id else None})
        source_ids.append('EXCEPTION:'+str(ex.pk))
    if len(episodes)>60:
        raise ValueError('CASE_EXCEPTION_LIMIT_EXCEEDED')
    # A model may cite *only* exact case-assigned, hash-verified synthetic
    # policy text. Never include an upload, private employee form or reviewer note.
    # IT/Manager are not authorized to read employee policy contents.
    policies=[]
    if member.role in (Membership.HR, Membership.EMPLOYEE):
        for task in tasks:
            if task.kind!='POLICY_ACK':
                continue
            try:
                policy=validated_policy(task)
            except CommandFailure:
                continue
            source='POLICY:'+str(task.pk)+':'+policy['content_sha256'][:12]
            policies.append({'source_id':source,'version':policy['version'],
                             'text':policy['text']})
            source_ids.append(source)
    ctx={'case_id':str(case.pk),'case_version':case.version,
         'status':case.status,'tasks':item_rows,'blockers':blockers[:60],
         'open_exceptions':episodes,
         'eligible_actions':actions,'sources':source_ids,
         'policies':policies}
    canonical=json.dumps(ctx,sort_keys=True,separators=(',',':'))
    ctx['context_digest']=hashlib.sha256(canonical.encode()).hexdigest()
    return ctx
