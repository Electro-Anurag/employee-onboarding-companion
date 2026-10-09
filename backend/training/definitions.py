"""Immutable published synthetic training pack and strict quiz validation."""
import hashlib
import json
from backend.onboarding.services import CommandFailure

TRAINING_QUESTIONS={
  'security_training':[
    {'key':'q1','prompt':'How should a synthetic security concern be handled?',
     'options':[{'value':'A','label':'Report to the assigned owner'},
                {'value':'B','label':'Share a credential'}],'answer':'A'},
    {'key':'q2','prompt':'Should the demonstration accept real employee secrets?',
     'options':[{'value':'A','label':'Yes'},{'value':'B','label':'No'}],'answer':'B'}],
  'workplace_training':[
    {'key':'q1','prompt':'How should a team member be treated?',
     'options':[{'value':'A','label':'Respectfully'},{'value':'B','label':'Disrespectfully'}],'answer':'A'},
    {'key':'q2','prompt':'Which system should be used for a synthetic task?',
     'options':[{'value':'A','label':'Approved test workspace'},
                {'value':'B','label':'Unapproved shared account'}],'answer':'A'}],
}
def hash_core(core):
    return hashlib.sha256(json.dumps(core,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def default_spec(key):
    core={'type':'TRAINING','module_version':'synthetic-'+key+'-v1',
          'questions':TRAINING_QUESTIONS[key],'passing_score':2}
    return {**core,'content_sha256':hash_core(core)}

def validate_spec(spec):
    if not isinstance(spec,dict) or set(spec)!=set(
        ('type','module_version','questions','passing_score','content_sha256')):
        raise CommandFailure('TRAINING_MODULE_NOT_CONFIGURED',422)
    core={k:v for k,v in spec.items() if k!='content_sha256'}
    version=spec['module_version']
    questions=spec['questions']
    if (spec['type']!='TRAINING' or not isinstance(version,str) or not 1<=len(version)<=80
         or not isinstance(questions,list) or not 1<=len(questions)<=5
         or type(spec['passing_score']) is not int
         or not 1<=spec['passing_score']<=len(questions)
         or not isinstance(spec['content_sha256'],str)
         or hash_core(core)!=spec['content_sha256']):
        raise CommandFailure('INVALID_TRAINING_MODULE',422)
    seen=set()
    for q in questions:
        if (not isinstance(q,dict) or set(q)!=set(('key','prompt','options','answer'))
          or not isinstance(q['key'],str) or not 1<=len(q['key'])<=64
          or q['key'] in seen or not isinstance(q['prompt'],str)
          or not 1<=len(q['prompt'])<=200
          or not isinstance(q['options'],list) or not 2<=len(q['options'])<=5
          or not all(isinstance(opt,dict) and set(opt)=={'value','label'}
              and isinstance(opt['value'],str) and 1<=len(opt['value'])<=20
              and isinstance(opt['label'],str) and 1<=len(opt['label'])<=150
              for opt in q['options'])
          or len({opt['value'] for opt in q['options']})!=len(q['options'])
          or q['answer'] not in {opt['value'] for opt in q['options']}):
            raise CommandFailure('INVALID_TRAINING_QUESTION',422)
        seen.add(q['key'])
    return spec

def public_spec(spec):
    valid=validate_spec(spec)
    return {'module_version':valid['module_version'],'content_sha256':valid['content_sha256'],
        'passing_score':valid['passing_score'],
        'questions':[{'key':q['key'],'prompt':q['prompt'],'options':q['options']}
                     for q in valid['questions']]}
