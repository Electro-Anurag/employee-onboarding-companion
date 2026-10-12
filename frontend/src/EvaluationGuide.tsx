import type {ReactNode} from 'react';

/** A truthful, role-specific orientation for the senior's synthetic evaluation.
 * Navigation only: the guide never calls commands or fabricates task outcomes.
 */
export type EvaluationRole = 'HR'|'EMPLOYEE'|'IT'|'MANAGER';
export type EvaluationSection = 'cases'|'work'|'inbox'|'portfolio'|'templates';
export type EvaluationStep = {
  title:string;
  detail:string;
  section:EvaluationSection;
  buttonLabel:string;
};

export const evaluationSteps:Record<EvaluationRole,readonly EvaluationStep[]>={
  HR:[
    {title:'1. Set up a versioned template',detail:'Publish the fictional 17-step first-month template. Publishing locks that version.',section:'templates',buttonLabel:'Open templates'},
    {title:'2. Create and activate a case',detail:'Choose the synthetic employee, IT owner and manager; inspect prerequisites after activation.',section:'cases',buttonLabel:'Open cases'},
    {title:'3. Review evidence and ownership',detail:'Open assigned cases to review forms, document revisions, exceptions and completion readiness.',section:'portfolio',buttonLabel:'Open HR portfolio'},
    {title:'4. Check handoffs',detail:'Inspect current in-app reminders; the public free demo may not run a continuous background worker.',section:'inbox',buttonLabel:'Open inbox'},
  ],
  EMPLOYEE:[
    {title:'1. Find your onboarding case',detail:'Open the assigned fictional case; pending steps are determined by the server.',section:'cases',buttonLabel:'Open cases'},
    {title:'2. Submit required evidence',detail:'Use current work to open permitted forms and policy acknowledgements. Do not upload real identity documents.',section:'work',buttonLabel:'Open my work'},
    {title:'3. Follow review results',detail:'Return to your case to view review decisions and the next eligible task.',section:'cases',buttonLabel:'View my case'},
  ],
  IT:[
    {title:'1. Locate IT-owned work',detail:'Use assigned tasks to find the fictional workspace-access and equipment steps.',section:'work',buttonLabel:'Open my work'},
    {title:'2. Record simulated fulfillment',detail:'The IT operation is a simulated external system; confirmation is still a real audited application command.',section:'cases',buttonLabel:'Open cases'},
    {title:'3. Review handoffs',detail:'Review your in-app inbox and the next server-authorized tasks.',section:'inbox',buttonLabel:'Open inbox'},
  ],
  MANAGER:[
    {title:'1. Review manager obligations',detail:'Find your assigned case and first-week preparation work.',section:'work',buttonLabel:'Open my work'},
    {title:'2. Record actual evidence',detail:'Submit preparation, meeting attendance and training evidence through permitted controls, not this guide.',section:'cases',buttonLabel:'Open cases'},
    {title:'3. Check next steps',detail:'Inspect dependency status and messages after an authorized action.',section:'inbox',buttonLabel:'Open inbox'},
  ]
};

type Props={
  role:EvaluationRole;
  onNavigate:(section:EvaluationSection)=>void;
  enabled?:boolean;
  children?:ReactNode;
};

export default function EvaluationGuide({role,onNavigate,enabled=true}:Props){
  return <details className="evaluation-guide" aria-label="Evaluation guide">
    <summary>Evaluation walkthrough</summary>
    <p>Fictional organization and identities. Follow these steps using real app controls; this guide never changes a case.</p>
    <ol>{evaluationSteps[role].map(step=>
      <li key={step.title}>
        <strong>{step.title}</strong>
        <p>{step.detail}</p>
        <button type="button" className="quiet" disabled={!enabled}
          onClick={()=>onNavigate(step.section)}>{step.buttonLabel}</button>
      </li>
    )}</ol>
    <p className="evaluation-limits"><strong>Evidence boundaries:</strong> Forms, authorizations, dependencies and audit changes are backed by Django/PostgreSQL. External HR/IT fulfillment is simulated. Model inference, secure scanner storage and periodic workers may be unavailable on free hosting; deterministic guidance is not model AI.</p>
    <p className="evaluation-limits">For the full engineering test matrix and demonstrated scenarios, use the submission documentation. Never use real employee information.</p>
  </details>;
}
