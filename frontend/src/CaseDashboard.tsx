import React from 'react';

export type RoleDashboardCounts = {
  mandatory_total:number;mandatory_completed:number;
  actionable:number;blocked:number;overdue:number;
};
export type CaseDashboardData = {
  case_id:string;case_version:number;case_status:string;as_of:string;
  progress:{mandatory_total:number;mandatory_completed:number;mandatory_remaining:number;percent:number};
  by_role:Record<'EMPLOYEE'|'HR'|'IT'|'MANAGER',RoleDashboardCounts>;
  states:Record<string,number>;
  unclosed_exceptions:number;open_exceptions:number;resolved_pending_hr_close:number;
  scope:'REQUIRED_APPLICABLE_TASKS_ONLY';
};
const ROLES=['EMPLOYEE','HR','IT','MANAGER'] as const;

export default function CaseDashboard({snapshot}:{snapshot:CaseDashboardData}){
  const overdue=ROLES.reduce((total,role)=>total+snapshot.by_role[role].overdue,0);
  const blocked=ROLES.reduce((total,role)=>total+snapshot.by_role[role].blocked,0);
  return <section className="subpanel" aria-label="Onboarding case dashboard">
    <h4>Mandatory onboarding overview</h4>
    <p>{snapshot.progress.mandatory_completed} of {snapshot.progress.mandatory_total} verified complete;
      {' '}{snapshot.progress.mandatory_remaining} remaining ({snapshot.progress.percent}%).</p>
    <p>{overdue} overdue mandatory task(s), {blocked} blocked mandatory task(s),
      {' '}{snapshot.unclosed_exceptions} exception(s) awaiting closure.</p>
    <table>
      <caption>Current mandatory tasks by accountable role</caption>
      <thead><tr>
        <th scope="col">Role</th><th scope="col">Complete</th>
        <th scope="col">Actionable</th><th scope="col">Blocked</th>
        <th scope="col">Overdue</th>
      </tr></thead>
      <tbody>{ROLES.map(role=><tr key={role}>
        <th scope="row">{role}</th>
        <td>{snapshot.by_role[role].mandatory_completed}/{snapshot.by_role[role].mandatory_total}</td>
        <td>{snapshot.by_role[role].actionable}</td>
        <td>{snapshot.by_role[role].blocked}</td>
        <td>{snapshot.by_role[role].overdue}</td>
      </tr>)}</tbody>
    </table>
    <p className="meta">{snapshot.open_exceptions} open/assigned exception(s);
      {' '}{snapshot.resolved_pending_hr_close} resolved and awaiting HR closure.</p>
    <p className="meta">Read-only snapshot as of {new Date(snapshot.as_of).toLocaleString()}.
      Refresh to update. Completion requires verified typed evidence;
      blocked and overdue work may overlap.</p>
  </section>;
}
