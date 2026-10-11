import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import CaseDashboard,{type CaseDashboardData} from './CaseDashboard';

const snapshot:CaseDashboardData={
  case_id:'synthetic-case',case_version:3,case_status:'ACTIVE',
  as_of:'2026-10-11T10:00:00Z',
  progress:{mandatory_total:4,mandatory_completed:1,mandatory_remaining:3,percent:25},
  by_role:{
    EMPLOYEE:{mandatory_total:1,mandatory_completed:0,actionable:1,blocked:0,overdue:0},
    HR:{mandatory_total:1,mandatory_completed:0,actionable:0,blocked:1,overdue:1},
    IT:{mandatory_total:1,mandatory_completed:0,actionable:1,blocked:0,overdue:1},
    MANAGER:{mandatory_total:1,mandatory_completed:1,actionable:0,blocked:0,overdue:0},
  },
  states:{READY:2,IN_PROGRESS:0,BLOCKED:1,NOT_STARTED:0,NEEDS_CLARIFICATION:0,
          COMPLETED:1,CANCELLED:0},
  unclosed_exceptions:2,open_exceptions:1,resolved_pending_hr_close:1,
  scope:'REQUIRED_APPLICABLE_TASKS_ONLY',
};

describe('M7 read-only case dashboard',()=>{
  it('renders evidence-based role counts and clearly labels snapshot',()=>{
    const html=renderToStaticMarkup(<CaseDashboard snapshot={snapshot}/>);
    expect(html).toContain('Onboarding case dashboard');
    expect(html).toContain('1 of 4 verified complete');
    expect(html).toContain('2 overdue mandatory task(s)');
    expect(html).toContain('1 blocked mandatory task(s)');
    expect(html).toContain('2 exception(s) awaiting closure');
    for(const role of ['EMPLOYEE','HR','IT','MANAGER'])
      expect(html).toContain('<th scope="row">'+role+'</th>');
    expect(html).toContain('Refresh to update');
    expect(html).not.toContain('Approve');
    expect(html).not.toContain('Auto-complete');
  });
});
