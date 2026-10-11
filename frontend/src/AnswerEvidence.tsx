/** Presentation-only labels for server-validated source identifiers.

These labels never claim that arbitrary generated prose has been semantically
verified. Backend authorization, source admission and command guards remain
authoritative; source text is never echoed here.
*/
export type ModelAnswer = {
  answer_type:string;answer:string;case_version:number;
  citations:string[];recommended_actions:string[];
  blockers:string[];limitations:string[];
};
export type EvidenceTask = {id:string;title:string;kind:string;owner_role:string};

export function evidenceLabel(source:string,tasks:EvidenceTask[]):string{
  if(source.startsWith('TASK:')){
    const task=tasks.find(t=>source==='TASK:'+t.id);
    return task?'Task: '+task.title+' ('+task.owner_role+')':'Task reference (not in current view)';
  }
  if(source.startsWith('POLICY:')){
    const task=tasks.find(t=>source.startsWith('POLICY:'+t.id+':')&&t.kind==='POLICY_ACK');
    return task?'Assigned policy: '+task.title:'Assigned policy reference';
  }
  if(source.startsWith('EXCEPTION:'))return 'Case exception episode reference';
  return 'Case source reference';
}

export default function AnswerEvidence({answer,model,tasks,currentVersion,origin='MODEL'}:{
  answer:ModelAnswer;model:string;tasks:EvidenceTask[];currentVersion:number;
  origin?:'MODEL'|'DETERMINISTIC';
}){
  if(answer.case_version!==currentVersion){
    return <div className="subpanel" role="alert" aria-label="Outdated companion answer">
      This model answer references an older case version and is hidden.
      Ask again after refreshing the case.
    </div>;
  }
  const verbatimPolicy=answer.answer_type==='PARTIAL'&&
    answer.answer.startsWith('Verbatim assigned policy edition ')&&
    answer.citations.length===1&&answer.citations[0].startsWith('POLICY:');
  return <section className="subpanel" aria-label="Companion answer with citations">
    <strong>{origin==='DETERMINISTIC'?
      'Verified assigned policy text (no model inference)':
      verbatimPolicy?'Verbatim case-assigned policy text (model-selected; relevance unverified)':
      `Model-generated answer (${answer.answer_type})`}</strong>
    <p style={{whiteSpace:'pre-wrap'}}>{answer.answer}</p>
    <p className="meta">{origin==='DETERMINISTIC'?'Source: ':'Model: '}{model} · Evaluated case v{answer.case_version}.
      {origin==='DETERMINISTIC'?
        ' The entire assigned edition was reproduced verbatim from the authorized case. This is not an AI interpretation or legal/employment advice.':
        verbatimPolicy?
        ' The entire displayed policy body was checked against the authorized snapshot. This does not verify the model selected a relevant policy or interpret its meaning.':
        " Source identifiers are checked for authorization and task linkage; the model's prose has not been independently fact-checked."}</p>
    <h5>Cited case evidence</h5>
    {answer.citations.length?
      <ul>{answer.citations.map(source=><li key={source}>
        {evidenceLabel(source,tasks)} — <code>{source}</code>
      </li>)}</ul>:<p>No cited case sources.</p>}
    {!!answer.recommended_actions.length&&<>
      <h5>Candidate actions (human authorization required)</h5>
      <ul>{answer.recommended_actions.map(x=><li key={x}><code>{x}</code></li>)}</ul>
    </>}
    {!!answer.blockers.length&&<>
      <h5>Cited blocker IDs</h5>
      <ul>{answer.blockers.map(x=><li key={x}><code>{x}</code></li>)}</ul>
    </>}
    {answer.limitations.map((x,i)=><p className="meta" key={i}>{x}</p>)}
  </section>;
}
