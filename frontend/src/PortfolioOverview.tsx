import React from 'react';

export type PortfolioCase = {
  case_id:string;employee_name:string;joining_date:string;
  status:string;case_version:number;
  progress:{mandatory_total:number;mandatory_completed:number;mandatory_remaining:number;percent:number};
  overdue_mandatory:number;unclosed_exceptions:number;
};
export type PortfolioPage = {
  as_of:string;scope:'CURRENT_HR_ASSIGNMENTS_PAGE';page_count:number;
  has_more:boolean;next_cursor:string|null;results:PortfolioCase[];
};

export default function PortfolioOverview({snapshot,busy,onRefresh,onMore,onOpen}:{
  snapshot:PortfolioPage;busy:boolean;onRefresh:()=>void;onMore:()=>void;
  onOpen:(item:PortfolioCase)=>void;
}){
  const loaded=snapshot.results;
  return <section className="panel" aria-label="HR onboarding portfolio">
    <h2>My assigned onboarding cases</h2>
    <p>{loaded.length} case(s) loaded from current HR assignments.
      {' '}Counts are for loaded cases only, not the organization.</p>
    <p className="meta">Read-only as of {new Date(snapshot.as_of).toLocaleString()}.
      Changes to assignments or task evidence require refresh.</p>
    <button disabled={busy} onClick={onRefresh}>Refresh portfolio</button>
    {!loaded.length&&<p>No onboarding cases currently assigned.</p>}
    <div className="case-list">{loaded.map(item=><button key={item.case_id}
      disabled={busy} onClick={()=>onOpen(item)}>
      <span><strong>{item.employee_name}</strong> <small>{item.status}</small></span>
      <span>Joining {item.joining_date} · v{item.case_version}</span>
      <span>{item.progress.mandatory_completed}/{item.progress.mandatory_total}
        {' '}mandatory complete · {item.overdue_mandatory} overdue · {
          item.unclosed_exceptions} unclosed exceptions</span>
    </button>)}</div>
    {snapshot.has_more&&<button disabled={busy||!snapshot.next_cursor}
      onClick={onMore}>Load more authorized cases</button>}
  </section>;
}
