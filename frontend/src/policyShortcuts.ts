/** Accessible, role-bound suggestions; server authorization is still required. */
export type PolicyShortcutTask={key:string;kind:string};
export type PolicyShortcut={key:string;label:string;question:string};
const SUPPORTED_POLICIES:readonly PolicyShortcut[]=[
  {key:'conduct_ack',label:'Read conduct policy',question:'Show the assigned conduct policy'},
  {key:'privacy_ack',label:'Read privacy policy',question:'Show the assigned privacy policy'},
  {key:'benefits_ack',label:'Read benefits policy',question:'Show the assigned benefits policy'},
];
export function assignedPolicyShortcuts(
  role:string|undefined,tasks:readonly PolicyShortcutTask[],
):PolicyShortcut[]{
  // This controls presentation only; the server re-authorizes and verifies
  // the current case and edition for every companion query.
  if(role!=='EMPLOYEE'&&role!=='HR')return [];
  return SUPPORTED_POLICIES.filter(p=>tasks.some(t=>
    t.kind==='POLICY_ACK'&&t.key===p.key));
}
