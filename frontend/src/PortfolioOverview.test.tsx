import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import PortfolioOverview,{type PortfolioPage} from './PortfolioOverview';

const page:PortfolioPage={
  as_of:'2026-10-11T10:00:00Z',scope:'CURRENT_HR_ASSIGNMENTS_PAGE',
  page_count:1,has_more:true,next_cursor:'123e4567-e89b-12d3-a456-426614174000',
  results:[{case_id:'123e4567-e89b-12d3-a456-426614174000',
    employee_name:'Synthetic Employee',joining_date:'2026-11-01',
    status:'PRE_JOINING',case_version:4,
    progress:{mandatory_total:17,mandatory_completed:2,mandatory_remaining:15,percent:11.8},
    overdue_mandatory:1,unclosed_exceptions:2}],
};
describe('M7 current-HR portfolio',()=>{
  it('presents page-scoped truthful counts and open/next controls',()=>{
    const html=renderToStaticMarkup(<PortfolioOverview snapshot={page}
      busy={false} onOpen={()=>{}} onMore={()=>{}} onRefresh={()=>{}}/>);
    expect(html).toContain('HR onboarding portfolio');
    expect(html).toContain('Synthetic Employee');
    expect(html).toContain('2/17');
    expect(html).toContain('1 overdue');
    expect(html).toContain('2 unclosed exceptions');
    expect(html).toContain('not the organization');
    expect(html).toContain('Load more authorized cases');
    expect(html).not.toContain('Company total');
  });
  it('does not show pagination for a complete empty result',()=>{
    const html=renderToStaticMarkup(<PortfolioOverview snapshot={{
      ...page,results:[],page_count:0,has_more:false,next_cursor:null}}
      busy={false} onOpen={()=>{}} onMore={()=>{}} onRefresh={()=>{}}/>);
    expect(html).toContain('No onboarding cases currently assigned');
    expect(html).not.toContain('Load more authorized cases');
  });
});
