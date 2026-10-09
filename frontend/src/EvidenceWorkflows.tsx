import {useState,type FormEvent} from 'react';

type Role='HR'|'IT'|'MANAGER'|'EMPLOYEE';
type FormEntry={id:string;revision:number;answers:Record<string,string>;
  review:null|{decision:'ACCEPTED'|'CHANGES_REQUESTED';note:string}};
type FormList={results:FormEntry[]};
type DocumentRow={id:string;revision:number;filename:string;scan_status:string;
  scan_profile:string;malware_scanned:boolean;
  review:null|{decision:'ACCEPTED'|'REJECTED'|'NEEDS_CLARIFICATION';note:string}};
type DocumentList={results:DocumentRow[];synthetic_only:boolean;malware_scanned:boolean};
type TrainingModule={module:{module_version:string;content_sha256:string;passing_score:number;
  questions:{key:string;prompt:string;options:{value:string;label:string}[]}[]};
  task_state:string;attempts:{number:number;score:number;passed:boolean}[]};
type ITOperation={state:'REQUESTED'|'SIMULATED_FULFILLED';provider:string;simulation_digest:string|null;
  confirmation_id:string|null;task_completion:string};
type ReceiptSource={provider:string;candidates:{task_id:string;confirmation_id:string;title:string}[]};
type PolicyEdition={task_id:string;policy:{version:string;content_sha256:string;text:string;policy_key:string};
  acknowledged:boolean};
type Task={id:string;key:string;kind:string;state:string;owner_role:string};

export default function EvidenceWorkflows({task,caseId,role,read,mutate,uploadDocument}:{
  task:Task;caseId:string;role:Role;
  read:(path:string)=>Promise<unknown>;
  mutate:(path:string,body:unknown)=>Promise<void>;
  uploadDocument:(path:string,file:File)=>Promise<void>;
}){
  const [history,setHistory]=useState<FormEntry[]|null>(null);
  const [operation,setOperation]=useState<ITOperation|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [preferredName,setPreferredName]=useState('');
  const [contactEmail,setContactEmail]=useState('');
  const [reviewNote,setReviewNote]=useState('');
  const [simulationNote,setSimulationNote]=useState('');
  const [confirmationNote,setConfirmationNote]=useState('');
  const [receiptNote,setReceiptNote]=useState('');
  const [receiptSource,setReceiptSource]=useState<ReceiptSource|null>(null);
  const [receiptConfirmation,setReceiptConfirmation]=useState('');
  const [policy,setPolicy]=useState<PolicyEdition|null>(null);
  const [policyConsent,setPolicyConsent]=useState(false);
  const [documentRows,setDocumentRows]=useState<DocumentRow[]|null>(null);
  const [documentFile,setDocumentFile]=useState<File|null>(null);
  const [documentDecision,setDocumentDecision]=useState<'ACCEPTED'|'REJECTED'|'NEEDS_CLARIFICATION'>('ACCEPTED');
  const [documentNote,setDocumentNote]=useState('');
  const [training,setTraining]=useState<TrainingModule|null>(null);
  const [trainingAnswers,setTrainingAnswers]=useState<Record<string,string>>({});
  const [trainingResult,setTrainingResult]=useState('');
  const base='/api/v1/cases/'+caseId+'/tasks/'+task.id;
  async function safeRun(fn:()=>Promise<void>){
    setBusy(true);setError('');
    try{await fn();}catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  async function loadForms(){
    const r=await read(base+'/form-submissions') as FormList;
    setHistory(r.results);
  }
  async function loadIT(){
    const r=await read(base+'/it-operation') as ITOperation;
    setOperation(r);
  }
  async function loadReceiptSource(){
    const result=await read(base+'/equipment-receipt/source') as ReceiptSource;
    setReceiptSource(result);
    setReceiptConfirmation(current=>current||result.candidates[0]?.confirmation_id||'');
  }
  async function loadTraining(){
    const result=await read(base+'/training-module') as TrainingModule;
    setTraining(result);
    setTrainingResult('');
  }
  async function loadDocumentHistory(){
    const result=await read(base+'/document-revisions') as DocumentList;
    setDocumentRows(result.results);
  }
  async function loadPolicy(){
    const result=await read(base+'/assigned-policy') as PolicyEdition;
    setPolicy(result);
    setPolicyConsent(false);
  }
  if(task.kind==='TRAINING'&&(role==='EMPLOYEE'||role==='HR')){
    return <section className="subpanel" aria-label="Versioned training quiz">
      <h5>Versioned, server-graded synthetic training</h5>
      <button className="quiet" disabled={busy} onClick={()=>void safeRun(loadTraining)}>
        View assigned training
      </button>
      {training&&<div className="form">
        <p className="meta">Module: {training.module.module_version}; passing score:
          {training.module.passing_score}/{training.module.questions.length}</p>
        {training.module.questions.map(q=><label key={q.key}>{q.prompt}
          <select disabled={busy||role!=='EMPLOYEE'||task.state==='COMPLETED'}
            value={trainingAnswers[q.key]||''}
            onChange={e=>setTrainingAnswers(prev=>({...prev,[q.key]:e.target.value}))}>
            <option value="">Choose answer</option>
            {q.options.map(o=><option value={o.value} key={o.value}>{o.label}</option>)}
          </select>
        </label>)}
        {training.attempts.map(a=><p className="meta" key={a.number}>
          Attempt {a.number}: {a.score} points — {a.passed?'PASSED':'NOT PASSED'}</p>)}
        {role==='EMPLOYEE'&&task.state!=='COMPLETED'&&
          (task.state==='READY'||task.state==='IN_PROGRESS')&&
          <button disabled={busy||training.module.questions.some(q=>!trainingAnswers[q.key])}
            onClick={()=>void safeRun(async()=>{
              await mutate(base+'/training-attempts',{
                module_version:training.module.module_version,
                content_sha256:training.module.content_sha256,answers:trainingAnswers});
              await loadTraining();
            })}>Submit answers for server grading</button>}
      </div>}
      {trainingResult&&<p className="meta">{trainingResult}</p>}
      {error&&<p role="alert" className="block">Training operation failed: {error}</p>}
    </section>;
  }
  if(task.kind==='DOCUMENT'&&(role==='EMPLOYEE'||role==='HR')){
    const current=documentRows?.at(-1);
    const mayUpload=role==='EMPLOYEE'&&(task.state==='READY'||task.state==='IN_PROGRESS')&&
      (!current||current.review?.decision==='REJECTED'||current.review?.decision==='NEEDS_CLARIFICATION');
    const mayReview=role==='HR'&&task.state==='IN_PROGRESS'&&current&&!current.review;
    return <section className="subpanel" aria-label="Synthetic document workflow">
      <h5>Synthetic document submission and HR verification</h5>
      <p className="meta">Only exact demonstration text files are accepted. These files are NOT antivirus scanned. Do not upload real employee documents.</p>
      <a href={base+'/document-sample'}>Download allowed synthetic text sample</a>
      <button className="quiet" disabled={busy}
        onClick={()=>void safeRun(loadDocumentHistory)}>Load document history</button>
      {documentRows&&documentRows.map(entry=><p className="meta" key={entry.id}>
        Revision {entry.revision}: {entry.scan_status} (not antivirus scanned) ·
        {entry.review?entry.review.decision+(entry.review.note?' — '+entry.review.note:''):' Pending HR review'}
        <a href={base+'/document-revisions/'+entry.id+'/download'}> Download revision</a>
      </p>)}
      {mayUpload&&<form className="form" onSubmit={e=>{e.preventDefault();
        if(!documentFile)return;
        void safeRun(async()=>{await uploadDocument(base+'/document-revisions',documentFile);
          await loadDocumentHistory();setDocumentFile(null);});}}>
        <label>Select the downloaded synthetic .txt fixture
          <input type="file" accept=".txt,text/plain" required
            onChange={e=>setDocumentFile(e.target.files?.[0]||null)}/>
        </label>
        <button type="submit" disabled={busy||!documentFile}>Upload synthetic document</button>
      </form>}
      {mayReview&&current&&<div className="form">
        <label>HR decision
          <select value={documentDecision} onChange={e=>setDocumentDecision(
            e.target.value as 'ACCEPTED'|'REJECTED'|'NEEDS_CLARIFICATION')}>
            <option value="ACCEPTED">Accept synthetic revision</option>
            <option value="REJECTED">Reject and request replacement</option>
            <option value="NEEDS_CLARIFICATION">Request clarification</option>
          </select>
        </label>
        <label>Reason / review evidence
          <textarea required maxLength={500} value={documentNote}
            onChange={e=>setDocumentNote(e.target.value)}/>
        </label>
        <button disabled={busy||!documentNote.trim()} onClick={()=>void safeRun(async()=>{
          await mutate(base+'/document-revisions/'+current.id+'/review',{
            decision:documentDecision,note:documentNote});
          await loadDocumentHistory();setDocumentNote('');
        })}>Record independent HR document decision</button>
      </div>}
      {error&&<p role="alert" className="block">Document operation failed: {error}</p>}
    </section>;
  }
  if(task.kind==='POLICY_ACK'&&(role==='EMPLOYEE'||role==='HR')){
    return <section className="subpanel" aria-label="Assigned policy acknowledgement">
      <h5>Case-assigned policy edition — synthetic text</h5>
      <button className="quiet" disabled={busy} onClick={()=>void safeRun(loadPolicy)}>
        View assigned policy
      </button>
      {policy&&<div>
        <p className="meta">Assigned edition: {policy.policy.version}</p>
        <p className="meta">SHA-256: <code>{policy.policy.content_sha256}</code></p>
        <p>{policy.policy.text}</p>
        {policy.acknowledged&&<p className="meta">Acknowledged and stored as immutable evidence.</p>}
      </div>}
      {role==='EMPLOYEE'&&policy&&!policy.acknowledged&&task.state==='READY'&&
        <div className="form">
          <label className="check"><input type="checkbox" checked={policyConsent}
            onChange={e=>setPolicyConsent(e.target.checked)}/>
            I have read and explicitly acknowledge this assigned synthetic edition.
          </label>
          <button disabled={busy||!policyConsent} onClick={()=>void safeRun(async()=>{
            await mutate(base+'/policy-acknowledge',{
              policy_version:policy.policy.version,
              content_sha256:policy.policy.content_sha256,accepted:true});
            await loadPolicy();
          })}>Record version-specific acknowledgement</button>
        </div>}
      {error&&<p role="alert" className="block">Policy operation failed: {error}</p>}
    </section>;
  }
  if(task.kind==='FORM'&&(role==='EMPLOYEE'||role==='HR')){
    const last=history?.at(-1);
    const canSubmit=role==='EMPLOYEE'&&task.key==='personal_details'&&
      (task.state==='READY'||task.state==='IN_PROGRESS')&&
      (!last||last.review?.decision==='CHANGES_REQUESTED');
    const pending=role==='HR'&&last&&!last.review;
    return <section className="subpanel" aria-label="Form evidence workflow">
      <h5>Form submission and review</h5>
      <button className="quiet" disabled={busy} onClick={()=>void safeRun(loadForms)}>Load form history</button>
      {history&&<div>
        {history.length===0?<p>No submitted form revisions.</p>:
          history.map(x=><p className="meta" key={x.id}>Revision {x.revision}: {x.review?
            x.review.decision+(x.review.note?' — '+x.review.note:''):'Pending HR review'}</p>)}
      </div>}
      {canSubmit&&<form className="form" onSubmit={(e:FormEvent)=>{e.preventDefault();
        void safeRun(async()=>{await mutate(base+'/form-submissions',{answers:{
          preferred_name:preferredName,contact_email:contactEmail}});
          await loadForms();setPreferredName('');setContactEmail('');});}}>
        <label>Preferred name<input required maxLength={200} value={preferredName}
          onChange={e=>setPreferredName(e.target.value)}/></label>
        <label>Contact email<input required type="email" maxLength={200} value={contactEmail}
          onChange={e=>setContactEmail(e.target.value)}/></label>
        <button disabled={busy} type="submit">Submit immutable form revision</button>
      </form>}
      {pending&&last&&<div className="form">
        <label>HR review note<textarea maxLength={500} value={reviewNote}
          onChange={e=>setReviewNote(e.target.value)}/></label>
        <div className="actions">
          <button disabled={busy} onClick={()=>void safeRun(async()=>{
            await mutate(base+'/form-submissions/'+last.id+'/review',
              {decision:'ACCEPTED',note:reviewNote});
            await loadForms();setReviewNote('');
          })}>Accept revision and complete task</button>
          <button disabled={busy||!reviewNote.trim()} onClick={()=>void safeRun(async()=>{
            await mutate(base+'/form-submissions/'+last.id+'/review',
              {decision:'CHANGES_REQUESTED',note:reviewNote});
            await loadForms();setReviewNote('');
          })}>Request correction</button>
        </div>
      </div>}
      {task.key!=='personal_details'&&role==='EMPLOYEE'&&
        <p className="meta">This form's custom field editor is not yet supported. No submission control is enabled.</p>}
      {error&&<p role="alert" className="block">Form operation failed: {error}</p>}
    </section>;
  }
  if(['ACCESS','EQUIPMENT'].includes(task.kind)&&(role==='IT'||role==='HR')){
    return <section className="subpanel" aria-label="Synthetic IT workflow">
      <h5>IT provisioning — synthetic simulation only</h5>
      <p className="meta">No external IT system is connected. Only a separate human IT confirmation can mark this synthetic task complete.</p>
      <button className="quiet" disabled={busy} onClick={()=>void safeRun(loadIT)}>Inspect IT operation</button>
      {operation&&<p className="meta">Provider {operation.provider}: {operation.state}
        {operation.simulation_digest?' · receipt '+operation.simulation_digest.slice(0,12):''}</p>}
      {role==='IT'&&task.state==='READY'&&
        <button disabled={busy} onClick={()=>void safeRun(async()=>{
          await mutate(base+'/it-operation/request',{});await loadIT();
        })}>Create synthetic IT request</button>}
      {role==='IT'&&task.state==='IN_PROGRESS'&&operation?.state==='REQUESTED'&&
        <div className="form">
          <label>Simulation note<input maxLength={300} value={simulationNote}
            onChange={e=>setSimulationNote(e.target.value)}/></label>
          <button disabled={busy} onClick={()=>void safeRun(async()=>{
            await mutate(base+'/it-operation/simulate',{note:simulationNote});
            await loadIT();setSimulationNote('');
          })}>Record simulated fulfillment</button>
        </div>}
      {role==='IT'&&task.state==='IN_PROGRESS'&&operation?.state==='SIMULATED_FULFILLED'&&!operation.confirmation_id&&
        <div className="form">
          <label>IT confirmation note<input required minLength={8} maxLength={300}
            value={confirmationNote} onChange={e=>setConfirmationNote(e.target.value)}/></label>
          <button disabled={busy||confirmationNote.trim().length<8}
            onClick={()=>void safeRun(async()=>{
              await mutate(base+'/it-operation/confirm',{note:confirmationNote});
              await loadIT();setConfirmationNote('');
            })}>Confirm simulated IT outcome and complete task</button>
        </div>}
      {operation?.confirmation_id&&<p className="meta">Explicit IT confirmation recorded. This does not verify external provisioning.</p>}
      {error&&<p role="alert" className="block">IT operation failed: {error}</p>}
    </section>;
  }
  if(task.kind==='EQUIPMENT_RECEIPT'&&role==='EMPLOYEE'){
    return <section className="subpanel" aria-label="Equipment receipt workflow">
      <h5>Equipment acknowledgement — synthetic case</h5>
      <p className="meta">Only acknowledge a specifically confirmed upstream equipment request.</p>
      <button className="quiet" disabled={busy} onClick={()=>void safeRun(loadReceiptSource)}>
        Load confirmed equipment evidence
      </button>
      {receiptSource&&<p className="meta">{receiptSource.candidates.length} confirmed equipment record(s)</p>}
      {receiptSource&&receiptSource.candidates.length>0&&task.state==='READY'&&
        <div className="form">
          <label>Confirmed equipment
            <select value={receiptConfirmation} onChange={e=>setReceiptConfirmation(e.target.value)}>
              {receiptSource.candidates.map(c=><option key={c.confirmation_id}
                value={c.confirmation_id}>{c.title}</option>)}
            </select>
          </label>
          <label>Receipt note<input required minLength={8} maxLength={300}
            value={receiptNote} onChange={e=>setReceiptNote(e.target.value)}/></label>
          <button disabled={busy||receiptNote.trim().length<8||!receiptConfirmation}
            onClick={()=>void safeRun(async()=>{
              await mutate(base+'/equipment-receipt',
                {it_confirmation_id:receiptConfirmation,note:receiptNote});
              setReceiptNote('');await loadReceiptSource();
            })}>Acknowledge confirmed synthetic equipment</button>
        </div>}
      {error&&<p role="alert" className="block">Equipment receipt failed: {error}</p>}
    </section>;
  }
  return null;
}
