import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import App from './App';
import {FormRevisionEntry} from './EvidenceWorkflows';

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
  it('labels the UI as a synthetic local/CI demonstration', () => {
    const output=renderToStaticMarkup(<App />);
    expect(output).toContain('synthetic demo');
    expect(output).toContain('not a hosted production system');
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
