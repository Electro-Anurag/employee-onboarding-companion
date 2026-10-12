import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import App,{preferNewerCase} from './App';
import {FormRevisionEntry} from './EvidenceWorkflows';
import EvaluationGuide,{evaluationSteps,type EvaluationRole} from './EvaluationGuide';

describe('M2 authenticated workspace UI boundaries', () => {
  it('renders truthful unauthenticated state and working sign-in form', () => {
    const output=renderToStaticMarkup(<App />);
    expect(output).toContain('Onboarding Companion');
    expect(output).toContain('Sign in');
    expect(output).toContain('type="email"');
    expect(output).toContain('type="password"');
    expect(output).not.toContain('Complete preparation');
    expect(output).not.toContain('Activate case');
    expect(output).not.toContain('All tasks completed');
  });
  it('labels the UI as synthetic evaluation only', () => {
    const output=renderToStaticMarkup(<App />);
    expect(output).toContain('synthetic demo');
    expect(output).toContain('Synthetic evaluation only');
  });
});

describe('M3 form revision review visibility and escaping',()=>{
  const entry={id:'synthetic-revision',revision:2,
    answers:{preferred_name:'Demo <Employee> Revised',contact_email:'employee@example.invalid'},
    review:null};
  it('shows exact submitted fields to the authorized HR reviewer',()=>{
    const html=renderToStaticMarkup(<FormRevisionEntry entry={entry} role="HR"/>);
    expect(html).toContain('Submitted fields — revision 2 (read-only)');
    expect(html).toContain('Preferred name');
    expect(html).toContain('Contact email');
    expect(html).toContain('Demo &lt;Employee&gt; Revised');
    expect(html).not.toContain('Demo <Employee> Revised');
    expect(html).toContain('Pending HR review');
  });
  it('does not add an HR-review values panel to other roles',()=>{
    for(const role of ['EMPLOYEE','IT','MANAGER'] as const){
      const html=renderToStaticMarkup(<FormRevisionEntry entry={entry} role={role}/>);
      expect(html).not.toContain('Demo &lt;Employee&gt; Revised');
      expect(html).not.toContain('Submitted fields — revision');
    }
  });
});

describe('simple and truthful first screen',()=>{
  it('starts without any preapproved evidence or synthetic remote claim',()=>{
    const html=renderToStaticMarkup(<App/>);
    expect(html).toContain('Know what needs doing');
    expect(html).not.toContain('Record version-specific acknowledgement');
    expect(html).not.toContain('Confirm simulated IT outcome');
  });
});

describe('case response ordering under overlapping form-review refresh',()=>{
  const old={case_id:'one',case_version:3,tasks:[{state:'IN_PROGRESS'}]};
  const accepted={case_id:'one',case_version:4,tasks:[{state:'COMPLETED'}]};
  it('cannot regress completed evidence to an earlier in-flight response',()=>{
    expect(preferNewerCase(accepted,old)).toBe(accepted);
    expect(preferNewerCase(old,accepted)).toBe(accepted);
  });
  it('allows same-version refresh and distinct selected cases',()=>{
    const same={...accepted,tasks:[{state:'COMPLETED',note:'fresh'}]};
    expect(preferNewerCase(accepted,same)).toBe(same);
    const different={case_id:'two',case_version:1,tasks:[]};
    expect(preferNewerCase(accepted,different)).toBe(different);
  });
});

describe('approved evidence remains authoritative',()=>{
  it('retains accepted task state while stale navigation returns',()=>{
    const accepted={case_id:'case',case_version:9,tasks:[{state:'COMPLETED'}]};
    const earlier={case_id:'case',case_version:8,tasks:[{state:'IN_PROGRESS'}]};
    expect(preferNewerCase(accepted,earlier).tasks[0].state).toBe('COMPLETED');
  });
});

describe('D5 semantic navigation and keyboard entry points',()=>{
  it('offers a skip link and exactly one login main landmark',()=>{
    const markup=renderToStaticMarkup(<App/>);
    expect(markup).toContain('href="#main-content"');
    expect(markup).toContain('Skip to main content');
    expect(markup).toContain('<main id="main-content"');
    expect(markup.match(/<main\b/g)).toHaveLength(1);
    expect(markup.indexOf('<header')).toBeLessThan(markup.indexOf('<main'));
    expect(markup).toContain('tabindex="-1"');
  });
});

describe('evaluation walkthrough presents truthful role-specific guidance',()=>{
  it('exposes the right steps and only allowed navigation for each role',()=>{
    const allowed:Record<EvaluationRole,string[]>={
      HR:['templates','cases','portfolio','inbox'],
      EMPLOYEE:['cases','work','cases'],
      IT:['work','cases','inbox'],
      MANAGER:['work','cases','inbox'],
    };
    for(const role of Object.keys(allowed) as EvaluationRole[]){
      expect(evaluationSteps[role].map(x=>x.section)).toEqual(allowed[role]);
      const html=renderToStaticMarkup(<EvaluationGuide role={role} onNavigate={()=>{}}/>);
      expect(html).toContain('Evaluation walkthrough');
      expect(html).toContain('Fictional organization and identities');
      expect(html).toContain('deterministic guidance is not model AI');
      expect(html).toContain('never changes a case');
      expect(html).not.toContain('Sign in');
    }
  });
  it('does not create operational buttons that bypass owner commands',()=>{
    for(const role of ['HR','IT','MANAGER','EMPLOYEE'] as const){
      const html=renderToStaticMarkup(<EvaluationGuide role={role} enabled={false} onNavigate={()=>{}}/>);
      expect(html).toContain('disabled=""');
      expect(html).not.toContain('Confirm final onboarding closeout');
      expect(html).not.toContain('Submit recorded evidence');
    }
  });
});
