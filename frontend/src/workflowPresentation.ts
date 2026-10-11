/**
 * View-only workflow presentation. The server owns prerequisites, eligibility,
 * assigned roles, evidence acceptance and transitions. Never derive a task's
 * state or enable a command from a client-side position.
 */
export type DisplayTask={
  id:string;key:string;state:string;position:number;prerequisite_task_ids:string[];
  due_at:string;
};

export function orderedWorkflowTasks<T extends DisplayTask>(tasks:readonly T[]):T[]{
  const index=new Map(tasks.map(task=>[task.id,task]));
  const indegree=new Map(tasks.map(task=>[task.id,0]));
  const children=new Map(tasks.map(task=>[task.id,[] as string[]]));
  for(const task of tasks){
    for(const before of new Set(task.prerequisite_task_ids)){
      if(!index.has(before))continue;
      indegree.set(task.id,(indegree.get(task.id)||0)+1);
      children.get(before)!.push(task.id);
    }
  }
  const cmp=(a:T,b:T)=>a.position-b.position||
    a.due_at.localeCompare(b.due_at)||a.key.localeCompare(b.key)||a.id.localeCompare(b.id);
  const available=tasks.filter(t=>indegree.get(t.id)===0).sort(cmp);
  const result:T[]=[];
  while(available.length){
    const current=available.shift()!;
    result.push(current);
    for(const child of children.get(current.id)||[]){
      const remaining=(indegree.get(child)||0)-1;
      indegree.set(child,remaining);
      if(remaining===0){available.push(index.get(child)!);available.sort(cmp);}
    }
  }
  // The published server template rejects cycles; fail visibly if the
  // response is corrupted instead of presenting a fabricated sequence.
  if(result.length!==tasks.length)throw new Error('Invalid workflow dependency graph');
  return result;
}

export function workflowPresentation<T extends DisplayTask>(tasks:readonly T[]){
  const ordered=orderedWorkflowTasks(tasks);
  const current=ordered.filter(t=>t.state==='READY'||t.state==='IN_PROGRESS');
  // In-progress work is the initial focus; navigation can reach all other
  // concurrently eligible tasks without inventing new dependencies.
  current.sort((a,b)=>
    (a.state==='IN_PROGRESS'?0:1)-(b.state==='IN_PROGRESS'?0:1) ||
    a.position-b.position || a.due_at.localeCompare(b.due_at) || a.key.localeCompare(b.key));
  const completed=ordered.filter(t=>t.state==='COMPLETED');
  const future=ordered.filter(t=>t.state==='BLOCKED'||t.state==='NOT_STARTED');
  const other=ordered.filter(t=>!current.includes(t)&&!completed.includes(t)&&!future.includes(t));
  return {current,completed,futureCount:future.length,otherCount:other.length};
}
