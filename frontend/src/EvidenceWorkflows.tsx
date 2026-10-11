import {useState,type FormEvent} from 'react';

type Role='HR'|'IT'|'MANAGER'|'EMPLOYEE';
type FormEntry={id:string;revision:number;answers:Record<string,string>;
  review:null|{decision:'ACCEPTED'|'CHANGES_REQUESTED';note:string}};
type FormList={results:FormEntry[]};
type DocumentRow={id:string;revision:number;filename:string;scan_status:string;
  scan_profile:string;malware_scanned:boolean;
  review:null|{decision:'ACCEPTED'|'REJECTED'|'NEEDS_CLARIFICATION';note:string}};
type DocumentList={results:DocumentRow[];synthetic_only:boolean;malware_scanned:boolean};
type SecureDoc={id:string;revision:number;filename:string;size:number;sha256:string;
  state:string;quarantine_stored:boolean;clean_version_verified:boolean;
  download_available:boolean;scan_attempts:{number:number;outcome:string}[];
  review:null|{decision:'ACCEPTED'|'REJECTED'|'NEEDS_CLARIFICATION';note:string}};
type SecureHistory={enabled:boolean;results:SecureDoc[];task_state:string};
type ActivityOccurrence={id:string;revision:number;start:string;end:string;
  medium:'VIDEO'|'IN_PERSON';meeting_reference:string;reason:string;
  cancellation:null|{id:string;reason:string;cancelled_at:string};
  attendance:null|{id:string;outcome:'ATTENDED'|'MISSED';note:string}};
type ActivityHistory={results:ActivityOccurrence[];current_revision:number|null;task_state:string};
type TrainingModule={module:{module_version:string;content_sha256:string;passing_score:number;
  questions:{key:string;prompt:string;options:{value:string;label:string}[]}[]};
  task_state:string;attempts:{number:number;score:number;passed:boolean}[]};
type ITOperation={state:'REQUESTED'|'SIMULATED_FULFILLED';provider:string;simulation_digest:string|null;
  confirmation_id:string|null;task_completion:string;
  retry_explicitly_available:boolean;
  failures:{id:string;sequence:number;cause:string;note:string}[]};
type ReceiptSource={provider:string;candidates:{task_id:string;confirmation_id:string;title:string}[]};
type PolicyEdition={task_id:string;policy:{version:string;content_sha256:string;text:string;policy_key:string};
  acknowledged:boolean};
type Task={id:string;key:string;kind:string;state:string;owner_role:string};

// Answers are already returned only by the case- and role-scoped form endpoint.
// Never fetch them through an unscoped route, or render raw HTML.
export function FormRevisionEntry({entry,role}:{entry:FormEntry;role:Role}){
  const state=entry.review?entry.review.decision+
    (entry.review.note?' — '+entry.review.note:''):'Pending HR review';
  return <div className="form-revision">
    <p className="meta">Revision {entry.revision}: {state}</p>
    {role==='HR'&&<div className="subpanel"
      aria-label={'Employee-submitted values for revision '+entry.revision}>
      <strong>Submitted fields — revision {entry.revision} (read-only)</strong>
      <dl className="form-evidence-values">
        {Object.entries(entry.answers).map(([key,value])=><div key={key}>
          <dt>{key.replace(/_/g,' ').replace(/^./,letter=>letter.toUpperCase())}</dt>
          <dd>{value}</dd>
        </div>)}
      </dl>
      <p className="meta">Compare this exact submitted revision before your HR decision.</p>
    </div>}
  </div>;
}

export default function EvidenceWorkflows({task,caseId,role,prefillName,prefillEmail,read,mutate,refreshCase,uploadDocument,uploadSecureDocument}:{
  task:Task;caseId:string;role:Role;prefillName:string;prefillEmail:string;
  read:(path:string)=>Promise<unknown>;
  mutate:(path:string,body:unknown)=>Promise<void>;
  refreshCase:()=>Promise<void>;
  uploadDocument:(path:string,file:File)=>Promise<void>;
  uploadSecureDocument:(base:string,file:File)=>Promise<void>;
}){
  const [history,setHistory]=useState<FormEntry[]|null>(null);
  const [operation,setOperation]=useState<ITOperation|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [preferredName,setPreferredName]=useState(role==='EMPLOYEE'?prefillName:'');
  const [contactEmail,setContactEmail]=useState(role==='EMPLOYEE'?prefillEmail:'');
  const [reviewNote,setReviewNote]=useState('');
  const [simulationNote,setSimulationNote]=useState('');
  const [simulationFailureCause,setSimulationFailureCause]=useState<
    'PROVIDER_UNAVAILABLE'|'SIMULATED_TIMEOUT'|'SIMULATED_REJECTION'>('SIMULATED_TIMEOUT');
  const [simulationFailureNote,setSimulationFailureNote]=useState('');
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
  const [secureDocuments,setSecureDocuments]=useState<SecureHistory|null>(null);
  const [secureFile,setSecureFile]=useState<File|null>(null);
  const [secureNote,setSecureNote]=useState('');
  const [secureDecision,setSecureDecision]=useState<'ACCEPTED'|'REJECTED'|'NEEDS_CLARIFICATION'>('ACCEPTED');
  const [training,setTraining]=useState<TrainingModule|null>(null);
  const [trainingAnswers,setTrainingAnswers]=useState<Record<string,string>>({});
  const [trainingResult,setTrainingResult]=useState('');
  const [activities,setActivities]=useState<ActivityOccurrence[]|null>(null);
  const [activityStart,setActivityStart]=useState('');
  const [activityEnd,setActivityEnd]=useState('');
  const [activityMedium,setActivityMedium]=useState<'VIDEO'|'IN_PERSON'>('VIDEO');
  const [activityReference,setActivityReference]=useState('');
  const [activityReason,setActivityReason]=useState('');
  const [attendanceOutcome,setAttendanceOutcome]=useState<'ATTENDED'|'MISSED'>('ATTENDED');
  const [attendanceNote,setAttendanceNote]=useState('');
  const [cancellationReason,setCancellationReason]=useState('');
  const base='/api/v1/cases/'+caseId+'/tasks/'+task.id;
  async function safeRun(fn:()=>Promise<void>){
    setBusy(true);setError('');
    try{await fn();}catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  async function loadForms(){
    const r=await read(base+'/form-submissions') as FormList;
    setHistory(r.results);
    if(role==='EMPLOYEE'){
      const latest=r.results.at(-1);
      if(latest?.review?.decision==='CHANGES_REQUESTED'){
        setPreferredName(latest.answers.preferred_name||prefillName);
        setContactEmail(latest.answers.contact_email||prefillEmail);
      }
    }
    // Loading history must also refresh the case version used by a subsequent
    // HR review; employee submissions can change it in another session.
    await refreshCase();
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
  async function loadActivities(){
    const response=await read(base+'/activity-occurrences') as ActivityHistory;
    setActivities(response.results);
  }
  async function loadTraining(){
    const result=await read(base+'/training-module') as TrainingModule;
    setTraining(result);
    setTrainingResult('');
  }
  async function loadSecureHistory(){
    const history=await read(base+'/secure-documents') as SecureHistory;
    setSecureDocuments(history);
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
  if(['ACTIVITY','INTRODUCTION','CHECK_IN'].includes(task.kind)&&role!=='IT'){
    const latest=activities?.at(-1);
    const organizer=role===task.owner_role&&(role==='HR'||role==='MANAGER');
    const canSchedule=organizer&&(task.state==='READY'||task.state==='IN_PROGRESS')&&
      (!latest||latest.attendance?.outcome!=='ATTENDED');
    const canCancel=(organizer||role==='HR')&&task.state==='IN_PROGRESS'&&
      latest&&!latest.cancellation&&!latest.attendance&&Date.parse(latest.end)>Date.now();
    const slotValid=activityStart&&activityEnd&&
      Number.isFinite(Date.parse(activityStart))&&Number.isFinite(Date.parse(activityEnd))&&
      Date.parse(activityEnd)>Date.parse(activityStart);
    const canRecord=organizer&&task.state==='IN_PROGRESS'&&latest&&!latest.attendance&&!latest.cancellation&&
      Date.parse(latest.end)<=Date.now();
    return <section className="subpanel" aria-label="Activity occurrence and attendance">
      <h5>Versioned meeting and attendance</h5>
      <p className="meta">Meeting scheduling is recorded locally; no calendar invitation or video link is sent externally.</p>
      <button className="quiet" disabled={busy} onClick={()=>void safeRun(loadActivities)}>
        Load activity schedule
      </button>
      {activities&&activities.length===0&&<p className="meta">No meeting scheduled.</p>}
      {activities&&activities.map(occ=><p className="meta" key={occ.id}>
        Revision {occ.revision}: {new Date(occ.start).toLocaleString()} — {new Date(occ.end).toLocaleString()},
        {' '}{occ.medium}: {occ.meeting_reference}.
        {occ.cancellation?' Cancelled: '+occ.cancellation.reason:
          occ.attendance?' Attendance '+occ.attendance.outcome:' Attendance pending'}
      </p>)}
      {canSchedule&&<div className="form">
        <label>Meeting start (local)
          <input type="datetime-local" value={activityStart}
            onChange={e=>setActivityStart(e.target.value)}/>
        </label>
        <label>Meeting end (local)
          <input type="datetime-local" value={activityEnd}
            onChange={e=>setActivityEnd(e.target.value)}/>
        </label>
        <label>Meeting medium
          <select value={activityMedium} onChange={e=>
            setActivityMedium(e.target.value as 'VIDEO'|'IN_PERSON')}>
            <option value="VIDEO">Video (local record only)</option>
            <option value="IN_PERSON">In-person</option>
          </select>
        </label>
        <label>Room or approved meeting reference
          <input required maxLength={160} value={activityReference}
            onChange={e=>setActivityReference(e.target.value)}/>
        </label>
        <label>Scheduling/rescheduling reason
          <input required minLength={8} maxLength={300} value={activityReason}
            onChange={e=>setActivityReason(e.target.value)}/>
        </label>
        <button disabled={busy||!slotValid||activityReference.trim().length<4||
          activityReason.trim().length<8} onClick={()=>void safeRun(async()=>{
          await mutate(base+'/activity-occurrences/schedule',{
            start:new Date(activityStart).toISOString(),
            end:new Date(activityEnd).toISOString(),
            medium:activityMedium,meeting_reference:activityReference,
            reason:activityReason});
          await loadActivities();
          setActivityReason('');
        })}>{latest?'Record reschedule':'Schedule meeting occurrence'}</button>
      </div>}
      {canCancel&&latest&&<div className="form">
        <label>Cancellation reason
          <textarea required minLength={8} maxLength={300}
            value={cancellationReason}
            onChange={e=>setCancellationReason(e.target.value)}/>
        </label>
        <button disabled={busy||cancellationReason.trim().length<8}
          onClick={()=>void safeRun(async()=>{
            await mutate(base+'/activity-occurrences/'+latest.id+'/cancel',
              {reason:cancellationReason});
            await loadActivities();
            setCancellationReason('');
          })}>Cancel current occurrence (task remains incomplete)</button>
      </div>}
      {canRecord&&latest&&<div className="form">
        <label>Actual attendance outcome
          <select value={attendanceOutcome} onChange={e=>
            setAttendanceOutcome(e.target.value as 'ATTENDED'|'MISSED')}>
            <option value="ATTENDED">Attended</option>
            <option value="MISSED">Missed — task remains incomplete</option>
          </select>
        </label>
        <label>Organizer attendance evidence
          <textarea required maxLength={500} value={attendanceNote}
            onChange={e=>setAttendanceNote(e.target.value)}/>
        </label>
        <button disabled={busy||attendanceNote.trim().length<8}
          onClick={()=>void safeRun(async()=>{
            await mutate(base+'/activity-occurrences/'+latest.id+'/attendance',{
              outcome:attendanceOutcome,note:attendanceNote});
            await loadActivities();setAttendanceNote('');
          })}>Record organizer attendance</button>
      </div>}
      {error&&<p role="alert" className="block">Activity operation failed: {error}</p>}
    </section>;
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
    const latestSecure=secureDocuments?.results.at(-1);
    const secureUploadReady=role==='EMPLOYEE'&&secureDocuments?.enabled&&
      (task.state==='READY'||task.state==='IN_PROGRESS')&&
      (!latestSecure||['AWAITING_CONTENT','REJECTED','NEEDS_CLARIFICATION',
        'REJECTED_SECURITY','SCAN_EXHAUSTED'].includes(latestSecure.state));
    const secureReviewReady=role==='HR'&&secureDocuments?.enabled&&
      task.state==='IN_PROGRESS'&&latestSecure?.state==='AWAITING_HR_REVIEW';
    return <section className="subpanel" aria-label="Synthetic document workflow">
      <h5>Versioned S3 document security workflow</h5>
      <p className="meta">For generated or anonymized test PDFs only. A real ClamAV scan is required before HR can review an exact clean object. The demo is not authorized for real identity data.</p>
      <button className="quiet" disabled={busy} onClick={()=>void safeRun(loadSecureHistory)}>
        Load S3 document processing history
      </button>
      {latestSecure?.state==='AWAITING_CONTENT'&&role==='EMPLOYEE'&&
        <p className="meta">Select the original exact PDF to resume the pending upload,
          or select a corrected PDF to create an audited replacement intent.</p>}
      {secureDocuments&&!secureDocuments.enabled&&
        <p className="meta">Real S3 document processing is disabled on this deployment.</p>}
      {secureDocuments?.results.map(x=><p className="meta" key={x.id}>
        S3 revision {x.revision} ({x.filename}): {x.state}.
        {x.scan_attempts.map(a=>' Scan '+a.number+' '+a.outcome).join(';')}
        {x.review?' HR '+x.review.decision+' — '+x.review.note:''}
        {x.download_available&&<a href={base+'/secure-documents/'+x.id+'/download'}>
          Download verified clean version</a>}
      </p>)}
      {secureUploadReady&&<form className="form" onSubmit={ev=>{
        ev.preventDefault();
        if(!secureFile)return;
        void safeRun(async()=>{await uploadSecureDocument(base,secureFile);
          await loadSecureHistory();setSecureFile(null);});
      }}>
        <label>Generated/anonymized PDF (up to 10 MiB)
          <input required type="file" accept=".pdf,application/pdf"
            onChange={ev=>setSecureFile(ev.target.files?.[0]||null)}/>
        </label>
        <button disabled={busy||!secureFile} type="submit">Upload to private S3 quarantine</button>
      </form>}
      {secureReviewReady&&latestSecure&&<div className="form">
        <label>Clean-object HR decision
          <select value={secureDecision} onChange={ev=>setSecureDecision(
            ev.target.value as 'ACCEPTED'|'REJECTED'|'NEEDS_CLARIFICATION')}>
            <option value="ACCEPTED">Accept verified clean PDF</option>
            <option value="REJECTED">Reject — request replacement</option>
            <option value="NEEDS_CLARIFICATION">Request clarification</option>
          </select>
        </label>
        <label>HR review evidence
          <textarea maxLength={500} value={secureNote}
            onChange={ev=>setSecureNote(ev.target.value)}/>
        </label>
        <button disabled={busy||!secureNote.trim()}
          onClick={()=>void safeRun(async()=>{
            await mutate(base+'/secure-documents/'+latestSecure.id+'/review',{
              decision:secureDecision,note:secureNote});
            await loadSecureHistory();setSecureNote('');
          })}>Record HR decision for exact clean version</button>
      </div>}

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
      <h5>Assigned policy</h5>
      <button className="quiet" disabled={busy} onClick={()=>void safeRun(loadPolicy)}>
        View assigned policy
      </button>
      {policy&&<div>
        <p className="meta">Assigned edition: {policy.policy.version}</p>
        <details className="meta"><summary>Version proof</summary>
          <p>SHA-256: <code>{policy.policy.content_sha256}</code></p></details>
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
          history.map(x=><FormRevisionEntry key={x.id} entry={x} role={role}/>)}
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
      {operation?.failures?.map(f=><p className="meta" key={f.id}>
        Failure {f.sequence}: {f.cause} — {f.note} (synthetic, task incomplete)
      </p>)}
      {role==='IT'&&(task.state==='READY'||task.state==='IN_PROGRESS')&&!operation&&
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
          })}>{operation.failures.length?'Retry with simulated fulfillment':'Record simulated fulfillment'}</button>
          {operation.failures.length<5&&<div className="form">
            <label>Simulated failure cause
              <select value={simulationFailureCause}
                onChange={e=>setSimulationFailureCause(e.target.value as
                  'PROVIDER_UNAVAILABLE'|'SIMULATED_TIMEOUT'|'SIMULATED_REJECTION')}>
                <option value="PROVIDER_UNAVAILABLE">Simulated provider unavailable</option>
                <option value="SIMULATED_TIMEOUT">Simulated timeout</option>
                <option value="SIMULATED_REJECTION">Simulated rejection</option>
              </select>
            </label>
            <label>Simulated failure note
              <input minLength={8} maxLength={300} value={simulationFailureNote}
                onChange={e=>setSimulationFailureNote(e.target.value)}/>
            </label>
            <button disabled={busy||simulationFailureNote.trim().length<8}
              onClick={()=>void safeRun(async()=>{
                await mutate(base+'/it-operation/simulated-failure',{
                  cause:simulationFailureCause,note:simulationFailureNote});
                await loadIT();setSimulationFailureNote('');
              })}>Record synthetic failure (task remains pending)</button>
          </div>}
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
      {receiptSource&&receiptSource.candidates.length>0&&
        (task.state==='READY'||task.state==='IN_PROGRESS')&&
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
