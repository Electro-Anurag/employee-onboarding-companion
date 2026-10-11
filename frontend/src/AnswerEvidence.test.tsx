import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import AnswerEvidence,{evidenceLabel,type ModelAnswer} from './AnswerEvidence';

const tasks=[
  {id:'t-one',title:'Assigned Conduct Policy',kind:'POLICY_ACK',owner_role:'EMPLOYEE'},
  {id:'t-two',title:'Manager Setup <script>alert(1)</script>',kind:'MANAGER_PREPARATION',
   owner_role:'MANAGER'},
];
const answer:ModelAnswer={
  answer_type:'SUPPORTED',answer:'Review the assigned synthetic policy.',
  case_version:4,citations:['POLICY:t-one:abcd1234abcd','TASK:t-two'],
  recommended_actions:['ACTION:t-two:START'],blockers:[],limitations:[],
};
describe('M6 answer provenance presentation',()=>{
  it('labels exact source IDs without revealing policy body or trusting HTML labels',()=>{
    const html=renderToStaticMarkup(<AnswerEvidence answer={answer}
      model="offline-synthetic" tasks={tasks} currentVersion={4}/>);
    expect(html).toContain('Assigned policy: Assigned Conduct Policy');
    expect(html).toContain('Manager Setup &lt;script&gt;alert(1)&lt;/script&gt;');
    expect(html).not.toContain('<script>alert(1)</script>');
    expect(html).toContain('POLICY:t-one:abcd1234abcd');
    expect(html).toContain('TASK:t-two');
    expect(html).toContain('human authorization required');
    expect(html).toContain('not been independently fact-checked');
  });
  it('suppresses every stale model claim, citation and proposed action',()=>{
    const html=renderToStaticMarkup(<AnswerEvidence answer={answer}
      model="offline-synthetic" tasks={tasks} currentVersion={5}/>);
    expect(html).toContain('Outdated companion answer');
    expect(html).not.toContain('Review the assigned synthetic policy');
    expect(html).not.toContain('ACTION:t-two:START');
    expect(html).not.toContain('POLICY:t-one:abcd1234abcd');
  });
  it('never invents a task label for an unmatched valid-looking reference',()=>{
    expect(evidenceLabel('TASK:unknown',tasks)).toContain('not in current view');
    expect(evidenceLabel('EXCEPTION:synthetic',tasks)).toContain('exception episode');
  });
});
