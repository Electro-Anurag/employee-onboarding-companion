"""Governed, immutable published template graph; no arbitrary workflow code."""
import hashlib
import json
import re
import uuid
from django.db import transaction,connection
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from backend.accounts.models import Membership
from backend.accounts.security import actor_context
from backend.audit.models import CommandReceipt
from backend.audit.services import append_event
from backend.templates.models import (OnboardingTemplate,TemplateVersion,TemplateTask,
    TemplateDependency,KINDS,OWNER_ROLES)
from backend.templates.defaults import first_month_template

class TemplateFailure(Exception):
    def __init__(self,code,status=422):
        self.code,self.status=code,status

KIND_ROLE={
    'DOCUMENT':{'EMPLOYEE'},'FORM':{'EMPLOYEE'},'POLICY_ACK':{'EMPLOYEE'},
    'EQUIPMENT':{'IT'},'ACCESS':{'IT'},'EQUIPMENT_RECEIPT':{'EMPLOYEE'},
    'TRAINING':{'EMPLOYEE'},'ACTIVITY':{'HR','MANAGER'},
    'INTRODUCTION':{'MANAGER'},'CHECK_IN':{'MANAGER'},'MANAGER_PREPARATION':{'MANAGER'},
}
KEY=re.compile(r'^[a-z][a-z0-9_]{1,79}$')
def _validate_graph(tasks,edges):
    if not isinstance(tasks,list) or not 1<=len(tasks)<=60 or not isinstance(edges,list) or len(edges)>300:
        raise TemplateFailure('INVALID_TEMPLATE_SIZE')
    keys={}
    for i,item in enumerate(tasks):
        if not isinstance(item,dict) or set(item)-set(('key','kind','title','description','owner_role','required','available_offset_days','due_offset_days','evidence_spec','position')):
            raise TemplateFailure('INVALID_TEMPLATE_TASK')
        key=item.get('key')
        if not isinstance(key,str) or not KEY.fullmatch(key) or key in keys:
            raise TemplateFailure('INVALID_OR_DUPLICATE_TASK_KEY')
        kind=item.get('kind')
        role=item.get('owner_role')
        title=item.get('title')
        evidence=item.get('evidence_spec')
        available=item.get('available_offset_days')
        due=item.get('due_offset_days')
        if (not isinstance(kind,str) or not isinstance(role,str)
                or kind not in KINDS or role not in KIND_ROLE.get(kind,set())
                or not isinstance(title,str) or not 1<=len(title)<=160
                or type(item.get('required')) is not bool
                or type(available) is not int or type(due) is not int
                or not (-90<=available<=due<=365)
                or not isinstance(evidence,dict) or evidence.get('type')!=kind
                or len(json.dumps(evidence))>1000
                or not isinstance(item.get('description',''),str)
                or len(item.get('description',''))>2000):
            raise TemplateFailure('INCOMPATIBLE_TASK_OR_EVIDENCE')
        keys[key]=item
    parents={k:set() for k in keys}
    pair_set=set()
    for edge in edges:
        if not isinstance(edge,dict) or set(edge)!=set(('predecessor','successor')):
            raise TemplateFailure('INVALID_DEPENDENCY')
        pred,succ=edge['predecessor'],edge['successor']
        if not isinstance(pred,str) or not isinstance(succ,str) or pred not in keys or succ not in keys or pred==succ or (pred,succ) in pair_set:
            raise TemplateFailure('INVALID_DEPENDENCY')
        if keys[succ]['required'] and not keys[pred]['required']:
            raise TemplateFailure('MANDATORY_DEPENDS_ON_OPTIONAL')
        pair_set.add((pred,succ))
        parents[succ].add(pred)
    ordered=[]
    eligible=sorted(k for k in keys if not parents[k])
    while eligible:
        k=eligible.pop(0)
        ordered.append(k)
        for succ in sorted(parents):
            if k in parents[succ]:
                parents[succ].remove(k)
                if not parents[succ] and succ not in ordered and succ not in eligible:
                    eligible.append(succ)
                    eligible.sort()
    if len(ordered)!=len(keys):
        raise TemplateFailure('DEPENDENCY_CYCLE')
    return ordered

def _editor(actor,organization_id=None):
    member=actor_context(actor,locked=True)
    if member.role!=Membership.HR or not member.can_manage_templates:
        raise PermissionDenied()
    if organization_id is not None and member.organization_id!=organization_id:
        raise PermissionDenied()
    return member

def _replace_draft(version,tasks,edges):
    ordered=_validate_graph(tasks,edges)
    if version.state!=TemplateVersion.DRAFT:
        raise TemplateFailure('PUBLISHED_TEMPLATE_IMMUTABLE',409)
    TemplateDependency.objects.filter(version=version).delete()
    TemplateTask.objects.filter(version=version).delete()
    rows={}
    for n,item in enumerate(tasks):
        rows[item['key']]=TemplateTask.objects.create(
            version=version,key=item['key'],kind=item['kind'],title=item['title'],
            description=item.get('description',''),owner_role=item['owner_role'],
            required=item['required'],position=n,available_offset_days=item['available_offset_days'],
            due_offset_days=item['due_offset_days'],evidence_spec=item['evidence_spec'])
    for edge in edges:
        TemplateDependency.objects.create(version=version,
            predecessor=rows[edge['predecessor']],successor=rows[edge['successor']])
    return ordered

def _snapshot(version):
    rows=list(version.tasks.order_by('position','key').values('key','kind','title','description',
        'owner_role','required','position','available_offset_days','due_offset_days','evidence_spec'))
    edges=list(version.edges.select_related('predecessor','successor').all())
    pairs=sorted([{'predecessor':e.predecessor.key,'successor':e.successor.key} for e in edges],
                 key=lambda x:(x['predecessor'],x['successor']))
    return rows,pairs

def summary(version,include_tasks=False):
    result={'id':str(version.template_id),'version_id':str(version.pk),
            'name':version.template.name,'key':version.template.key,
            'version':version.version_number,'revision':version.revision,
            'state':version.state,'content_hash':version.content_hash}
    if include_tasks:
        ts,edges=_snapshot(version)
        result.update(tasks=ts,dependencies=edges)
    return result

def create_template(*,actor,key,name,tasks,edges):
    if not isinstance(key,str) or not KEY.fullmatch(key) or not isinstance(name,str) or not 1<=len(name)<=160:
        raise TemplateFailure('INVALID_TEMPLATE')
    _validate_graph(tasks,edges)
    with transaction.atomic():
        member=_editor(actor)
        template=OnboardingTemplate.objects.create(organization=member.organization,
                        key=key,name=name,created_by=actor)
        version=TemplateVersion.objects.create(template=template)
        _replace_draft(version,tasks,edges)
        append_event(stream_key=f'org:{member.organization_id}',actor=actor,
            event_type='TEMPLATE_CREATED',entity_id=version.pk,changes={'template_id':str(template.pk),'key':key})
        return summary(version,True)

def read_template(*,actor,template_id):
    member=actor_context(actor)
    if member.role!=Membership.HR:
        raise PermissionDenied()
    t=OnboardingTemplate.objects.filter(pk=template_id,organization_id=member.organization_id).first()
    if t is None: raise TemplateFailure('NOT_FOUND',404)
    version=t.versions.order_by('-version_number').first()
    return summary(version,True)

def list_templates(actor):
    member=actor_context(actor)
    if member.role!=Membership.HR: raise PermissionDenied()
    ts=TemplateVersion.objects.select_related('template').filter(
        template__organization_id=member.organization_id).order_by('template__key','-version_number')[:100]
    return [summary(v) for v in ts]

def edit_template(*,actor,template_id,revision,tasks,edges):
    with transaction.atomic():
        _editor(actor)
        template=OnboardingTemplate.objects.select_for_update().filter(pk=template_id).first()
        if template is None: raise TemplateFailure('NOT_FOUND',404)
        _editor(actor,template.organization_id)
        version=TemplateVersion.objects.select_for_update().filter(template=template).order_by('-version_number').first()
        if version.state!=TemplateVersion.DRAFT: raise TemplateFailure('DRAFT_REQUIRED',409)
        if version.revision!=revision: raise TemplateFailure('STALE_VERSION',409)
        _replace_draft(version,tasks,edges)
        version.revision+=1
        version.save(update_fields=['revision'])
        append_event(stream_key=f'org:{template.organization_id}',actor=actor,
            event_type='TEMPLATE_DRAFT_UPDATED',entity_id=version.pk,
            changes={'version':version.version_number,'revision':version.revision})
        return summary(version,True)

def publish_template(*,actor,template_id,revision):
    with transaction.atomic():
        member=_editor(actor)
        t=OnboardingTemplate.objects.select_for_update().filter(pk=template_id,organization=member.organization).first()
        if t is None: raise TemplateFailure('NOT_FOUND',404)
        v=TemplateVersion.objects.select_for_update().filter(template=t).order_by('-version_number').first()
        if v.state!=TemplateVersion.DRAFT: raise TemplateFailure('DRAFT_REQUIRED',409)
        if v.revision!=revision: raise TemplateFailure('STALE_VERSION',409)
        tasks,edges=_snapshot(v)
        ordered=_validate_graph(tasks,edges)
        h=hashlib.sha256(json.dumps({'tasks':tasks,'dependencies':edges},
                  sort_keys=True,separators=(',',':')).encode()).hexdigest()
        v.content_hash=h
        v.state=TemplateVersion.PUBLISHED
        v.published_at=timezone.now()
        v.save(update_fields=['content_hash','state','published_at'])
        append_event(stream_key=f'org:{t.organization_id}',actor=actor,
            event_type='TEMPLATE_PUBLISHED',entity_id=v.pk,
            changes={'template_id':str(t.pk),'version':v.version_number,'hash':h,'task_count':len(ordered)})
        return summary(v,True)

def next_draft(*,actor,template_id):
    with transaction.atomic():
        member=_editor(actor)
        t=OnboardingTemplate.objects.select_for_update().filter(pk=template_id,organization=member.organization).first()
        if t is None: raise TemplateFailure('NOT_FOUND',404)
        last=TemplateVersion.objects.filter(template=t).order_by('-version_number').first()
        if last.state!=TemplateVersion.PUBLISHED: raise TemplateFailure('DRAFT_ALREADY_EXISTS',409)
        tasks,edges=_snapshot(last)
        version=TemplateVersion.objects.create(template=t,version_number=last.version_number+1)
        _replace_draft(version,tasks,edges)
        append_event(stream_key=f'org:{member.organization_id}',actor=actor,
            event_type='TEMPLATE_DRAFT_CLONED',entity_id=version.pk,
            changes={'from_version_id':str(last.pk),'version':version.version_number})
        return summary(version,True)

def create_default(*,actor):
    tasks,edges=first_month_template()
    return create_template(actor=actor,key='employee_first_month',
        name='Employee First Month (Synthetic)',tasks=tasks,edges=edges)
