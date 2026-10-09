import { useEffect, useRef, useState } from 'react';
import './App.css';
import EvidenceWorkflows from './EvidenceWorkflows';

type Me = { display_name:string;role:'HR'|'IT'|'MANAGER'|'EMPLOYEE';user_id:string;capabilities?:{manage_templates:boolean;coordinate_ownership:boolean} };
type Progress = { mandatory_total:number;mandatory_completed:number;mandatory_remaining:number;percent:number };
type Case = {id:string; status:string;joining_date:string;employee_name:string;version:number;progress?:Progress};
type Task = {id:string;key:string;kind:string;title:string;state:string;owner_role:string;
  due_at:string;available_at:string;blocked_reason_codes:string[];allowed_actions:string[];required:boolean};
type Template = {id:string;version_id:string;name:string;key:string;version:number;revision:number;
  state:'DRAFT'|'PUBLISHED';tasks?:unknown[];dependencies?:unknown[];content_hash:string};
type Owner = {id:string;name:string};
type TaskPayload = {case_id:string;case_version:number;case_status:string;progress:Progress;tasks:Task[]};
type WorkspaceTask = Task & {case_id:string;employee_name:string};
type ApiError = {error?:{code?:string;message?:string}};

export default function App(){
  const [me,setMe]=useState<Me|null>(null);
  const [csrf,setCsrf]=useState('');
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [cases,setCases]=useState<Case[]>([]);
  const [work,setWork]=useState<WorkspaceTask[]>([]);
  const [templates,setTemplates]=useState<Template[]>([]);
  const [owners,setOwners]=useState<Record<string,Owner[]>>({});
  const [template,setTemplate]=useState<Template|null>(null);
  const [editor,setEditor]=useState('');
  const [selected,setSelected]=useState<Case|null>(null);
  const [detail,setDetail]=useState<TaskPayload|null>(null);
  const [employeeId,setEmployeeId]=useState('');
  const [itId,setItId]=useState('');
  const [managerId,setManagerId]=useState('');
  const [templateId,setTemplateId]=useState('');
  const [joiningDate,setJoiningDate]=useState('');
  const [attestTask,setAttestTask]=useState<string|null>(null);
  const [plan,setPlan]=useState('');
  const [buddy,setBuddy]=useState('');
  const [station,setStation]=useState(false);
  const [note,setNote]=useState('');
  const [message,setMessage]=useState('Sign in to access assigned onboarding work.');
  const [busy,setBusy]=useState(false);
  const [tab,setTab]=useState<'cases'|'work'|'templates'>('cases');
  // Every identity transition invalidates all in-flight identity-bound reads.
  // The generation is checked immediately before committing any fetched data.
  const identityEpoch=useRef(0);
  function forgetProtectedIdentity(){
    identityEpoch.current+=1;
    setCases([]);setWork([]);setTemplates([]);setOwners({});
    setTemplate(null);setEditor('');setSelected(null);setDetail(null);
    setEmployeeId('');setItId('');setManagerId('');setTemplateId('');setJoiningDate('');
    setAttestTask(null);setPlan('');setBuddy('');setStation(false);setNote('');
    setTab('cases');
  }
  function replaceIdentity(next:Me|null){
    forgetProtectedIdentity();
    setMe(next);
  }

  async function request<T>(path:string,method='GET',body?:unknown,extra:Record<string,string>={}):Promise<T>{
    const headers:Record<string,string>={...extra};
    if(method!=='GET'){
      headers['Content-Type']='application/json';
      headers['X-CSRFToken']=csrf;
      headers['Idempotency-Key']=extra['Idempotency-Key']||crypto.randomUUID();
    }
    const response=await fetch(path,{method,credentials:'same-origin',headers,
      body:method==='GET'?undefined:JSON.stringify(body||{})});
    let result:unknown;
    try{result=await response.json();}catch{result={};}
    if(!response.ok){
      const data=result as ApiError;
      throw new Error((data.error?.code||data.error?.message||'HTTP '+response.status));
    }
    return result as T;
  }

  useEffect(()=>{
    // Startup is an identity-bearing read. Do not let a delayed old /auth/me
    // response replace a newer session established through sign-in/logout.
    const generation=identityEpoch.current;
    void (async()=>{
      try{
        const r=await fetch('/api/v1/auth/csrf',{credentials:'same-origin'});
        if(!r.ok)throw new Error('CSRF endpoint unavailable');
        const initialCsrf=(await r.json()).csrf_token;
        if(identityEpoch.current!==generation)return;
        setCsrf(initialCsrf);
        const identity=await fetch('/api/v1/auth/me',{credentials:'same-origin'});
        if(!identity.ok)return;
        const initialIdentity=await identity.json();
        if(identityEpoch.current!==generation)return;
        replaceIdentity(initialIdentity);
      }catch{
        if(identityEpoch.current===generation)
          setMessage('Authentication endpoint unavailable. Retry later.');
      }
    })();
  },[]);

  async function refresh(identity:Me){
    const generation=identityEpoch.current;
    const nextCases=await request<{results:Case[]}>('/api/v1/cases');
    const nextWork=await request<{results:WorkspaceTask[]}>('/api/v1/workspaces/me');
    let nextTemplates:Template[]=[];
    let nextOwners:Record<string,Owner[]>={};
    if(identity.role==='HR'){
      const t=await request<{results:Template[]}>('/api/v1/templates');
      nextTemplates=t.results;
      const entries=await Promise.all(['EMPLOYEE','IT','MANAGER'].map(async(role)=>{
        const v=await request<{results:Owner[]}>('/api/v1/owners?role='+role);
        return [role,v.results] as const;
      }));
      nextOwners=Object.fromEntries(entries);
    }
    if(identityEpoch.current!==generation)return;
    setCases(nextCases.results);setWork(nextWork.results);
    setTemplates(nextTemplates);setOwners(nextOwners);
  }
  useEffect(()=>{
    if(!me)return;
    const generation=identityEpoch.current;
    void refresh(me).catch(e=>{
      if(identityEpoch.current===generation)
        setMessage('Unable to read workspace: '+String(e));
    });
  },[me]);

  async function perform(workflow:()=>Promise<void>){
    const generation=identityEpoch.current;
    setBusy(true);
    try{
      await workflow();
      if(identityEpoch.current===generation)
        setMessage('Saved successfully. All status updates come from the server.');
    }catch(e){
      if(identityEpoch.current===generation)
        setMessage('Operation not completed: '+(e instanceof Error?e.message:String(e)));
    }finally{setBusy(false);}
  }

  async function signIn(event:React.FormEvent){
    event.preventDefault();
    // Invalidate any startup identity response BEFORE the login round-trip.
    const transition=++identityEpoch.current;
    await perform(async()=>{
      await request('/api/v1/auth/login','POST',{email,password});
      const m=await request<Me>('/api/v1/auth/me');
      const token=await fetch('/api/v1/auth/csrf',{credentials:'same-origin'});
      if(!token.ok)throw new Error('Could not refresh CSRF');
      const newCsrf=(await token.json()).csrf_token;
      if(identityEpoch.current!==transition)return;
      setCsrf(newCsrf);
      replaceIdentity(m);setPassword('');
    });
  }
  async function signOut(){
    // Prevent responses from the previous authenticated identity from
    // committing data while logout is in progress.
    const transition=++identityEpoch.current;
    await perform(async()=>{
      await request('/api/v1/auth/logout','POST',{});
      if(identityEpoch.current!==transition)return;
      replaceIdentity(null);
      const token=await fetch('/api/v1/auth/csrf',{credentials:'same-origin'});
      if(token.ok)setCsrf((await token.json()).csrf_token);
    });
  }
  async function selectCase(c:Case){
    const generation=identityEpoch.current;
    await perform(async()=>{
      const result=await request<TaskPayload>('/api/v1/cases/'+c.id+'/tasks');
      if(identityEpoch.current!==generation)return;
      setSelected(c);setDetail(result);setTab('cases');setAttestTask(null);
    });
  }
  async function reloadCase(caseId:string,identity:Me){
    const generation=identityEpoch.current;
    await refresh(identity);
    if(identityEpoch.current!==generation)return;
    const result=await request<TaskPayload>('/api/v1/cases/'+caseId+'/tasks');
    if(identityEpoch.current!==generation)return;
    setDetail(result);
    setSelected(old=>old&&old.id===caseId?{...old,version:result.case_version,status:result.case_status}:old);
  }
  async function activate(){
    if(!selected||!detail||!me)return;
    await perform(async()=>{
      await request('/api/v1/cases/'+selected.id+'/activate','POST',{},
        {'If-Match':'"case:'+selected.id+':v'+detail.case_version+'"'});
      await reloadCase(selected.id,me);
    });
  }
  async function beginDayOne(){
    if(!selected||!detail||!me)return;
    await perform(async()=>{
      await request('/api/v1/cases/'+selected.id+'/day-one','POST',{},
        {'If-Match':'"case:'+selected.id+':v'+detail.case_version+'"'});
      await reloadCase(selected.id,me);
    });
  }
  async function start(task:Task){
    if(!detail||!me)return;
    await perform(async()=>{
      await request('/api/v1/cases/'+detail.case_id+'/tasks/'+task.id+'/start','POST',{},
        {'If-Match':'"case:'+detail.case_id+':v'+detail.case_version+'"'});
      await reloadCase(detail.case_id,me);
    });
  }
  async function uploadDocument(path:string,file:File){
    if(!detail||!me)throw new Error('No authenticated case selected');
    const generation=identityEpoch.current;
    const caseId=detail.case_id;
    const body=new FormData();
    body.set('file',file);
    const response=await fetch(path,{method:'POST',credentials:'same-origin',
      headers:{'X-CSRFToken':csrf,'Idempotency-Key':crypto.randomUUID(),
        'If-Match':'"case:'+caseId+':v'+detail.case_version+'"'},body});
    const result=await response.json() as ApiError;
    if(!response.ok)throw new Error(result.error?.code||'HTTP '+response.status);
    if(identityEpoch.current!==generation)return;
    await reloadCase(caseId,me);
  }
  async function uploadSecureDocument(base:string,file:File){
    if(!detail||!me)throw new Error('No authenticated case selected');
    if(file.type!=='application/pdf'||file.size<40||file.size>10*1024*1024)
      throw new Error('Select a generated/anonymized PDF under 10 MiB.');
    const epoch=identityEpoch.current,caseId=detail.case_id;
    const bytes=await file.arrayBuffer();
    const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)))
      .map(x=>x.toString(16).padStart(2,'0')).join('');
    if(identityEpoch.current!==epoch)return;
    // Resume the exact pending intent across reloads rather than creating
    // a second immutable intent. A different PDF gets audited supersession.
    const history=await request<{results:{id:string;sha256:string;size:number;state:string}[]}>(
      base+'/secure-documents');
    if(identityEpoch.current!==epoch)return;
    const latest=history.results.at(-1);
    const resume=latest?.state==='AWAITING_CONTENT'&&
      latest.sha256===sha&&latest.size===file.size;
    let uploadId:string;
    let version=detail.case_version;
    if(resume){
      uploadId=latest.id;
    }else{
      const ready=await request<{case_version:number;result:{upload_id:string}}>(
        base+'/secure-documents/prepare','POST',
        {sha256:sha,size:file.size,filename:file.name},
        {'If-Match':'"case:'+caseId+':v'+detail.case_version+'"'});
      if(identityEpoch.current!==epoch)return;
      uploadId=ready.result.upload_id;
      version=ready.case_version;
    }
    const multipart=new FormData();
    multipart.set('file',file);
    try{
      const response=await fetch(base+'/secure-documents/'+uploadId+'/content',{
        method:'POST',credentials:'same-origin',
        headers:{'X-CSRFToken':csrf,'Idempotency-Key':uploadId,
          'If-Match':'"case:'+caseId+':v'+version+'"'},
        body:multipart});
      const data=await response.json() as ApiError;
      if(!response.ok)throw new Error(data.error?.code||'HTTP '+response.status);
    }catch(e){
      if(identityEpoch.current===epoch)await reloadCase(caseId,me);
      throw e;
    }
    if(identityEpoch.current!==epoch)return;
    await reloadCase(caseId,me);
  }
  async function mutateEvidence(path:string,body:unknown){
    if(!detail||!me)throw new Error('No authenticated case selected');
    const generation=identityEpoch.current;
    const caseId=detail.case_id;
    await request(path,'POST',body,{'If-Match':'"case:'+caseId+':v'+detail.case_version+'"'});
    if(identityEpoch.current!==generation)return;
    await reloadCase(caseId,me);
  }
  async function attest(event:React.FormEvent){
    event.preventDefault();
    if(!detail||!attestTask||!me)return;
    await perform(async()=>{
      await request('/api/v1/cases/'+detail.case_id+'/tasks/'+attestTask+'/attest-manager','POST',
        {prepared_fields:{first_week_plan:plan,buddy_name:buddy,workstation_ready:station},note},
        {'If-Match':'"case:'+detail.case_id+':v'+detail.case_version+'"'});
      setAttestTask(null);setPlan('');setBuddy('');setNote('');setStation(false);
      await reloadCase(detail.case_id,me);
    });
  }
  async function createDefault(){
    if(!me)return;
    const generation=identityEpoch.current;
    await perform(async()=>{
      const result=await request<Template>('/api/v1/templates','POST',{use_default:true});
      if(identityEpoch.current!==generation)return;
      setTemplate(result);
      await refresh(me);
      if(identityEpoch.current===generation)setTab('templates');
    });
  }
  async function showTemplate(item:Template){
    const generation=identityEpoch.current;
    await perform(async()=>{
      const result=await request<Template>('/api/v1/templates/'+item.id);
      if(identityEpoch.current!==generation)return;
      setTemplate(result);
      setEditor(JSON.stringify({tasks:result.tasks,dependencies:result.dependencies},null,2));
    });
  }
  async function publish(){
    if(!me||!template)return;
    await perform(async()=>{
      const result=await request<Template>('/api/v1/templates/'+template.id+'/publish','POST',{},
        {'If-Match':'"template:'+template.id+':version:'+template.version_id+':r'+template.revision+'"'});
      setTemplate(result);await refresh(me);
    });
  }
  async function clone(){
    if(!me||!template)return;
    await perform(async()=>{
      const result=await request<Template>('/api/v1/templates/'+template.id+'/next-draft','POST',{});
      setTemplate(result);
      setEditor(JSON.stringify({tasks:result.tasks,dependencies:result.dependencies},null,2));
      await refresh(me);
    });
  }
  async function saveDraft(){
    if(!me||!template)return;
    await perform(async()=>{
      const draft=JSON.parse(editor) as {tasks:unknown[];dependencies:unknown[]};
      if(!Array.isArray(draft.tasks)||!Array.isArray(draft.dependencies))throw Error('Expected arrays for tasks and dependencies');
      const result=await request<Template>('/api/v1/templates/'+template.id+'/draft','PATCH',draft,
        {'If-Match':'"template:'+template.id+':version:'+template.version_id+':r'+template.revision+'"'});
      setTemplate(result);await refresh(me);
    });
  }
  async function createCase(event:React.FormEvent){
    event.preventDefault();
    if(!me)return;
    await perform(async()=>{
      await request('/api/v1/cases','POST',{employee_id:employeeId,
        template_version_id:templateId,joining_date:joiningDate,
        owners:{IT:itId,MANAGER:managerId}});
      await refresh(me);
      setMessage('Case persisted in CREATED. Select it to activate when ready.');
    });
  }
  return <main className="shell">
    <header className="topbar"><div><span className="eyebrow">Aster Vale Labs — synthetic demo</span><h1>Onboarding Companion</h1>
      <p>M2 case engine with M3 versioned form review and M4 synthetic IT operations. Remaining milestone workflows are still under development.</p></div>
      {me&&<button className="quiet" disabled={busy} onClick={()=>void signOut()}>Sign out</button>}
    </header>
    {!me?<section className="panel login"><h2>Sign in</h2>
      <form onSubmit={e=>void signIn(e)} className="form">
        <label>Email<input type="email" required autoComplete="username" value={email} onChange={e=>setEmail(e.target.value)}/></label>
        <label>Password<input type="password" required autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label>
        <button type="submit" disabled={busy||!csrf}>Sign in</button>
      </form></section>:
    <div className="layout">
      <aside className="sidebar panel"><strong>{me.display_name}</strong><p>Role: {me.role}</p>
        <nav aria-label="Workspace">
          <button className={tab==='cases'?'selected':'quiet'} onClick={()=>setTab('cases')}>Cases ({cases.length})</button>
          <button className={tab==='work'?'selected':'quiet'} onClick={()=>setTab('work')}>My work ({work.length})</button>
          {me.role==='HR'&&<button className={tab==='templates'?'selected':'quiet'} onClick={()=>setTab('templates')}>Templates ({templates.length})</button>}
        </nav>
        <button className="quiet" disabled={busy} onClick={()=>void perform(async()=>{await refresh(me);if(selected)await reloadCase(selected.id,me);})}>Refresh</button>
      </aside>
      <div className="content">
        {tab==='cases'&&<section className="panel"><h2>Authorized cases</h2>
          {!cases.length&&<p>No cases assigned yet.</p>}
          <div className="case-list">{cases.map(c=><button key={c.id} disabled={busy}
              className={selected?.id===c.id?'selected':'quiet'} onClick={()=>void selectCase(c)}>
              <span><strong>{c.employee_name}</strong> <small>{c.status}</small></span>
              <span>Joining {c.joining_date} · v{c.version}</span>
              {c.progress&&<span>{c.progress.mandatory_completed}/{c.progress.mandatory_total} required complete</span>}
            </button>)}</div>
          {selected&&detail&&<section aria-label="Case tasks" className="subpanel">
            <div className="heading"><h3>{selected.employee_name} — {detail.case_status}</h3>
              <p>{detail.progress.mandatory_completed}/{detail.progress.mandatory_total} mandatory tasks completed ({detail.progress.percent}%)</p></div>
            {detail.case_status==='CREATED'&&me.role==='HR'&&<button disabled={busy} onClick={()=>void activate()}>Activate case</button>}
            {detail.case_status==='PRE_JOINING'&&me.role==='HR'&&<button disabled={busy} onClick={()=>void beginDayOne()}>Begin Day 1 (joining date required)</button>}
            {detail.tasks.length===0&&<p>Tasks will be instantiated only after successful activation.</p>}
            <div className="task-list">{detail.tasks.map(t=><article key={t.id} className="task">
              <div><h4>{t.title}</h4><span className="meta">{t.kind} · {t.owner_role} · {t.state}</span>
                <p className="meta">Due: {new Date(t.due_at).toLocaleString()} {t.required?'· Required':'· Optional'}</p>
                {!!t.blocked_reason_codes.length&&<p className="block">Blocked: {t.blocked_reason_codes.join(', ')}</p>}
              </div>
              <div className="task-actions">
                {t.allowed_actions.includes('START')&&<button disabled={busy} onClick={()=>void start(t)}>Start</button>}
                {t.allowed_actions.includes('ATTEST_MANAGER_PREPARATION')&&
                  <button disabled={busy} onClick={()=>setAttestTask(old=>old===t.id?null:t.id)}>Complete preparation</button>}
              </div>
              {(t.kind==='FORM'||t.kind==='DOCUMENT'||t.kind==='TRAINING'||t.kind==='POLICY_ACK'||t.kind==='ACTIVITY'||t.kind==='INTRODUCTION'||t.kind==='CHECK_IN'||t.kind==='ACCESS'||t.kind==='EQUIPMENT'||t.kind==='EQUIPMENT_RECEIPT')&&
                <EvidenceWorkflows key={me.user_id+':'+t.id} task={t} caseId={detail.case_id}
                  role={me.role} read={path=>request(path)} mutate={mutateEvidence} uploadDocument={uploadDocument} uploadSecureDocument={uploadSecureDocument}/>}
              {attestTask===t.id&&<form className="form attest" onSubmit={e=>void attest(e)}>
                <label>First-week plan<input required minLength={8} maxLength={300} value={plan} onChange={e=>setPlan(e.target.value)}/></label>
                <label>Buddy's name<input required minLength={2} maxLength={100} value={buddy} onChange={e=>setBuddy(e.target.value)}/></label>
                <label className="check"><input type="checkbox" checked={station} onChange={e=>setStation(e.target.checked)}/> Workstation is ready</label>
                <label>Attestation note<textarea required maxLength={500} value={note} onChange={e=>setNote(e.target.value)}/></label>
                <button disabled={busy||!station} type="submit">Submit recorded evidence</button>
              </form>}
            </article>)}</div>
            <p className="meta">Separate real S3 processing requires explicitly configured private buckets and a scanner; do not upload genuine employee data to the demo. Training completion requires server grading; meetings use versioned scheduling and organizer-recorded attendance. External calendar notifications remain unimplemented.</p>
          </section>}
        </section>}
        {tab==='work'&&<section className="panel"><h2>My assigned tasks</h2>
          {!work.length?<p>No currently assigned tasks.</p>:<div className="task-list">{work.map(t=><article className="task" key={t.id}>
            <div><strong>{t.employee_name} — {t.title}</strong><p className="meta">{t.state} · {t.owner_role} · {t.kind}</p>
              {!!t.blocked_reason_codes.length&&<p className="block">{t.blocked_reason_codes.join(', ')}</p>}</div>
            <button disabled={busy} onClick={()=>{const c=cases.find(x=>x.id===t.case_id);if(c)void selectCase(c);}}>Open case</button>
          </article>)}</div>}
        </section>}
        {tab==='templates'&&me.role==='HR'&&<section className="panel"><h2>Versioned templates</h2>
          {me.capabilities?.manage_templates&&<button disabled={busy} onClick={()=>void createDefault()}>Create default synthetic 17-task template</button>}
          {!templates.length&&<p>No templates published or drafted yet.</p>}
          <div className="case-list">{templates.map(t=><button key={t.version_id} className="quiet" disabled={busy} onClick={()=>void showTemplate(t)}>
            {t.name} — v{t.version} {t.state} (revision {t.revision})
          </button>)}</div>
          {template&&<section className="subpanel"><h3>{template.name} v{template.version} — {template.state}</h3>
            <p>Content SHA-256: <code>{template.content_hash||'Not published'}</code></p>
            {template.state==='DRAFT'&&me.capabilities?.manage_templates?<><label>Draft tasks and dependency JSON
              <textarea className="json-editor" value={editor} onChange={e=>setEditor(e.target.value)}/>
            </label><div className="actions"><button disabled={busy} onClick={()=>void saveDraft()}>Save draft</button>
              <button disabled={busy} onClick={()=>void publish()}>Validate and publish</button></div></>
             :<><p>{template.state==='PUBLISHED'?'Published versions are immutable. Active cases retain their original snapshot.':'This draft is read-only for your current role capability.'}</p>
               {template.state==='PUBLISHED'&&me.capabilities?.manage_templates&&<button disabled={busy} onClick={()=>void clone()}>Create next version draft</button>}</>}
          </section>}
        </section>}
        {me.role==='HR'&&tab==='cases'&&<section className="panel"><h2>Create an onboarding case</h2>
          <p className="meta">Choose a published version, synthetic employee, IT and manager. HR ownership is assigned to your current account.</p>
          <form className="form" onSubmit={e=>void createCase(e)}>
            <label>Published template<select required value={templateId} onChange={e=>setTemplateId(e.target.value)}><option value="">Select template</option>
              {templates.filter(t=>t.state==='PUBLISHED').map(t=><option value={t.version_id} key={t.version_id}>{t.name} v{t.version}</option>)}</select></label>
            <label>Employee<select required value={employeeId} onChange={e=>setEmployeeId(e.target.value)}><option value="">Select employee</option>
              {(owners.EMPLOYEE||[]).map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
            <label>IT owner<select required value={itId} onChange={e=>setItId(e.target.value)}><option value="">Select IT owner</option>
              {(owners.IT||[]).map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
            <label>Manager<select required value={managerId} onChange={e=>setManagerId(e.target.value)}><option value="">Select manager</option>
              {(owners.MANAGER||[]).map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
            <label>Joining date<input type="date" required value={joiningDate} onChange={e=>setJoiningDate(e.target.value)}/></label>
            <button type="submit" disabled={busy||!templateId||!employeeId||!itId||!managerId||!joiningDate}>Create case</button>
          </form>
        </section>}
      </div>
    </div>}
    <p aria-live="polite" role="status" className="status">{message}</p>
    <footer><small>Local/CI synthetic demonstration. This is not a hosted production system and does not process real employee data.</small></footer>
  </main>;
}
