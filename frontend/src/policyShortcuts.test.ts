import {describe,it,expect} from 'vitest';
import {assignedPolicyShortcuts} from './policyShortcuts';

const assigned=[
  {key:'conduct_ack',kind:'POLICY_ACK'},
  {key:'privacy_ack',kind:'POLICY_ACK'},
  {key:'benefits_ack',kind:'POLICY_ACK'},
  {key:'equipment_setup',kind:'IT'},
];

describe('readable no-model policy shortcuts (UI suggestions only)',()=>{
  it('offers only truly assigned policy keys to authorized policy readers',()=>{
    for(const role of ['HR','EMPLOYEE']){
      const options=assignedPolicyShortcuts(role,assigned);
      expect(options.map(x=>x.key)).toEqual([
        'conduct_ack','privacy_ack','benefits_ack']);
      expect(options.map(x=>x.question)).toEqual([
        'Show the assigned conduct policy',
        'Show the assigned privacy policy',
        'Show the assigned benefits policy',
      ]);
    }
  });
  it('never offers policy text selectors to IT/Manager/anonymous users',()=>{
    for(const role of ['IT','MANAGER',undefined,'UNKNOWN']){
      expect(assignedPolicyShortcuts(role,assigned)).toEqual([]);
    }
  });
  it('does not offer keys lacking a case task or a policy acknowledgement kind',()=>{
    expect(assignedPolicyShortcuts('EMPLOYEE',[
      {key:'conduct_ack',kind:'POLICY_ACK'},
      {key:'privacy_ack',kind:'DOCUMENT'},
      {key:'benefits_ack',kind:'FORM'},
    ]).map(x=>x.key)).toEqual(['conduct_ack']);
    expect(assignedPolicyShortcuts('HR',[])).toEqual([]);
  });
  it('does not invent actions or approvals in suggested questions',()=>{
    for(const opt of assignedPolicyShortcuts('EMPLOYEE',assigned)){
      expect(opt.question).toMatch(/^Show the assigned (conduct|privacy|benefits) policy$/);
      expect(opt.question).not.toMatch(/approve|waive|guarantee|complete/i);
    }
  });
});
