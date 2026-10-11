import {describe,it,expect} from 'vitest';
import {orderedWorkflowTasks,workflowPresentation,type DisplayTask} from './workflowPresentation';
const task=(id:string,state:string,position:number,prerequisite_task_ids:string[]=[]):DisplayTask=>
  ({id,key:id,state,position,prerequisite_task_ids,due_at:'2026-10-19T17:00:00Z'});

describe('governed focused workflow',()=>{
  it('hides future dependent tasks until server authorizes them; preserves completed evidence',()=>{
    const first=[task('details','IN_PROGRESS',0),
      task('equipment','BLOCKED',1,['details']),
      task('access','NOT_STARTED',2,['equipment']),
      task('privacy','READY',3)];
    const page=workflowPresentation(first);
    expect(page.current.map(t=>t.id)).toEqual(['details','privacy']);
    expect(page.completed).toEqual([]);
    expect(page.futureCount).toBe(2);
    expect([...page.current,...page.completed].map(t=>t.id)).not.toContain('equipment');
    const after=[task('details','COMPLETED',0),task('equipment','READY',1,['details']),
      task('access','BLOCKED',2,['equipment']),task('privacy','READY',3)];
    const approved=workflowPresentation(after);
    expect(approved.current.map(t=>t.id)).toEqual(['equipment','privacy']);
    expect(approved.completed.map(t=>t.id)).toEqual(['details']);
    expect(approved.futureCount).toBe(1);
  });
  it('orders predecessors before descendants even when authored positions are reversed',()=>{
    const p=orderedWorkflowTasks([task('descendant','READY',0,['parent']),
      task('parallel','READY',1),task('parent','COMPLETED',9)]);
    expect(p.map(t=>t.id).indexOf('parent')).toBeLessThan(p.map(t=>t.id).indexOf('descendant'));
  });
  it('does not serialize independent ready tasks or expose cancelled/future cards',()=>{
    const page=workflowPresentation([task('first','READY',0),task('second','READY',1),
      task('cancelled','CANCELLED',2),task('later','NOT_STARTED',3)]);
    expect(page.current.map(t=>t.id)).toEqual(['first','second']);
    expect(page.otherCount).toBe(1);
    expect(page.futureCount).toBe(1);
  });
  it('rejects a corrupt dependency cycle instead of creating an artificial flow',()=>{
    expect(()=>workflowPresentation([task('a','READY',0,['b']),task('b','READY',1,['a'])])).toThrow('Invalid workflow dependency graph');
  });
});
