"""M6 deterministic offline companion baseline: current facts, not generated AI."""
from backend.ai.context import authorized_context


def current_guidance(actor,case_id):
    ctx=authorized_context(actor,case_id)
    indexed={t['id']:t for t in ctx['tasks']}
    actions=[]
    for action in ctx['eligible_actions']:
        t=indexed.get(action['task_id'])
        if t is None:continue
        actions.append({'action_id':action['id'],'task_id':t['id'],
            'source_id':'TASK:'+t['id'],'task_title':t['title'],
            'action':action['type'],'due_at':t['due_at'],
            'owner_role':t['owner_role']})
    actions.sort(key=lambda a:(a['due_at'],a['task_title'],a['action']))
    blockers=[]
    for entry in ctx['blockers']:
        t=indexed.get(entry['task_id'])
        if t is None:continue
        prerequisites=[{
            'task_id':pid,'source_id':'TASK:'+pid,
            'task_title':indexed[pid]['title'],
            'state':indexed[pid]['state'],
            'owner_role':indexed[pid]['owner_role']}
            for pid in entry['unmet_prerequisite_ids'] if pid in indexed]
        blockers.append({'blocker_id':entry['id'],
            'task_id':t['id'],'source_id':'TASK:'+t['id'],
            'task_title':t['title'],'reason_codes':entry['reason_codes'],
            'unmet_prerequisites':prerequisites})
    return {'mode':'DETERMINISTIC_ONLY','ai_model_used':False,
        'case_id':ctx['case_id'],'case_version':ctx['case_version'],
        'context_digest':ctx['context_digest'],
        'actionable':actions[:3],'total_eligible_actions':len(actions),
        'blockers':blockers[:15],
        'limitations':['No AI model has generated or verified this guidance.',
            'Task actions still require their normal authorized human commands.']}
