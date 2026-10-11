import { useEffect, useRef, useState } from 'react';
import './App.css';
import EvidenceWorkflows from './EvidenceWorkflows';
import {workflowPresentation} from './workflowPresentation';

type Me = { display_name:string;email:string;role:'HR'|'IT'|'MANAGER'|'EMPLOYEE';user_id:string;capabilities?:{manage_templates:boolean;coordinate_ownership:boolean} };
type Progress = { mandatory_total:number;mandatory_completed:number;mandatory_remaining:number;percent:number };
type Case = {id:string; status:string;joining_date:string;employee_name:string;version:number;progress?:Progress};
type Task = {id:string;key:string;kind:string;title:string;state:string;owner_role:string;
  due_at:string;available_at:string;position:number;prerequisite_task_ids:string[];
  blocked_reason_codes:string[];allowed_actions:string[];required:boolean};
type Template = {id:string;version_id:string;name:string;key:string;version:number;revision:number;
  state:'DRAFT'|'PUBLISHED';tasks?:unknown[];dependencies?:unknown[];content_hash:string};
type Owner = {id:string;name:string};
type TaskPayload = {case_id:string;case_version:number;case_status:string;progress:Progress;tasks:Task[]};
type WorkspaceTask = Task & {case_id:string;employee_name:string};
type ApiError = {error?:{code?:string;message?:string}};
type DatePreview = {case_id:string;case_version:number;schedule_revision:number;
  old_joining_date:string;new_joining_date:string;preview_digest:string;
  change_count:number;preserved_count:number;preserved_task_ids:string[];
  warnings:string[];changes:{task_id:string;title:string;old_available_at:string;
    old_due_at:string;new_available_at:string;new_due_at:string}[]};
type Guidance = {mode:'DETERMINISTIC_ONLY';ai_model_used:false;
  case_version:number;actionable:{task_id:string;task_title:string;action:string;due_at:string;owner_role:string}[];
  blockers:{task_title:string;reason_codes:string[];
    unmet_prerequisites:{task_title:string;state:string;owner_role:string}[]}[];
  open_exceptions:{id:string;task_title:string;cause:string;episode:number;
    status:string;assignee_role:string|null}[];limitations:string[]};
type CompanionAnswer = {mode:string;ai_model_used:boolean;error_code?:string;model?:string;
  guidance?:Guidance;answer?:{answer_type:string;answer:string;citations:string[];
    recommended_actions:string[];blockers:string[];limitations:string[]}};
type ExceptionRecord = {id:string;task_id:string;task_title:string;task_owner_role:string;
  cause:string;episode:number;
  status:'OPEN'|'ASSIGNED'|'RESOLVED'|'CLOSED'|'SUPERSEDED';assignee_role:string|null;
  reason:string;blocking_now:boolean;events:{action:string;status:string;note:string;created_at:string}[]};
type InboxRow = {id:string;case_id:string;task_id:string;summary:string;
  rule_code:string;created_at:string;read_at:string|null;status:string};

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
  const [focusedTaskId,setFocusedTaskId]=useState<string|null>(null);
  const [showFullPlan,setShowFullPlan]=useState(false);
  const [employeeId,setEmployeeId]=useState('');
  const [itId,setItId]=useState('');
  const [managerId,setManagerId]=useState('');
  const [templateId,setTemplateId]=useState('');
  const [joiningDate,setJoiningDate]=useState('');
  const [newJoiningDate,setNewJoiningDate]=useState('');
  const [dateChangeReason,setDateChangeReason]=useState('');
  const [datePreview,setDatePreview]=useState<DatePreview|null>(null);
  const [attestTask,setAttestTask]=useState<string|null>(null);
  const [plan,setPlan]=useState('');
  const [buddy,setBuddy]=useState('');
  const [station,setStation]=useState(false);
  const [note,setNote]=useState('');
  const [message,setMessage]=useState('Sign in to access assigned onboarding work.');
  const [busy,setBusy]=useState(false);
  const [tab,setTab]=useState<'cases'|'work'|'templates'|'inbox'>('cases');
  const [inbox,setInbox]=useState<InboxRow[]>([]);
  const [inboxLoaded,setInboxLoaded]=useState(false);
  const [exceptions,setExceptions]=useState<ExceptionRecord[]>([]);
  const [exceptionsLoaded,setExceptionsLoaded]=useState(false);
  const [guidance,setGuidance]=useState<Guidance|null>(null);
  const [aiQuestion,setAiQuestion]=useState('');
  const [aiAnswer,setAiAnswer]=useState<CompanionAnswer|null>(null);
  const [exceptionTask,setExceptionTask]=useState('');
  const [exceptionCause,setExceptionCause]=useState('PREREQUISITE_BLOCKED');
  const [exceptionNote,setExceptionNote]=useState('');
  const [exceptionAssignees,setExceptionAssignees]=useState<Record<string,string>>({});
  const [recoveryOwner,setRecoveryOwner]=useState<Record<string,string>>({});
  const [recoveryReason,setRecoveryReason]=useState('');
  // Every identity transition invalidates all in-flight identity-bound reads.
  // The generation is checked immediately before committing any fetched data.
  const identityEpoch=useRef(0);
  const aiRequestEpoch=useRef(0);
  const datePreviewGeneration=useRef(0);
  function forgetProtectedIdentity(){
    identityEpoch.current+=1;
    aiRequestEpoch.current+=1;
    datePreviewGeneration.current+=1;
    setCases([]);setWork([]);setTemplates([]);setOwners({});
    setInbox([]);setInboxLoaded(false);
    setExceptions([]);setExceptionsLoaded(false);setExceptionTask('');
    setGuidance(null);setAiAnswer(null);setAiQuestion('');setExceptionNote('');setExceptionAssignees({});
    setRecoveryOwner({});setRecoveryReason('');
    setTemplate(null);setEditor('');setSelected(null);setDetail(null);setFocusedTaskId(null);setShowFullPlan(false);
    setEmployeeId('');setItId('');setManagerId('');setTemplateId('');setJoiningDate('');
    setNewJoiningDate('');setDateChangeReason('');setDatePreview(null);
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

  async function loadInbox(){
    const generation=identityEpoch.current;
    const result=await request<{results:InboxRow[];delivery:string}>('/api/v1/notifications');
    if(identityEpoch.current!==generation)return;
    setInbox(result.results);setInboxLoaded(true);
  }
  useEffect(()=>{
    if(tab!=='inbox'||!me)return;
    const generation=identityEpoch.current;
    void loadInbox().catch(e=>{
      if(identityEpoch.current===generation)
        setMessage('Inbox unavailable: '+(e instanceof Error?e.message:String(e)));
    });
  },[tab,me]);
  async function markInboxRead(id:string){
    await perform(async()=>{
      await request('/api/v1/notifications/'+id+'/read','POST',{});
      await loadInbox();
    });
  }

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
    const aiSwitch=++aiRequestEpoch.current;
    await perform(async()=>{
      const result=await request<TaskPayload>('/api/v1/cases/'+c.id+'/tasks');
      if(identityEpoch.current!==generation||aiRequestEpoch.current!==aiSwitch)return;
      setSelected(c);setDetail(result);setTab('cases');setAttestTask(null);
      setFocusedTaskId(null);setShowFullPlan(false);
      setExceptions([]);setExceptionsLoaded(false);setExceptionTask('');
      setGuidance(null);setAiAnswer(null);setAiQuestion('');setDatePreview(null);
      datePreviewGeneration.current+=1;
      setNewJoiningDate('');setDateChangeReason('');
      setRecoveryOwner({});setRecoveryReason('');
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
  async function previewJoiningDate(){
    if(!selected||!detail||!newJoiningDate)return;
    const generation=++datePreviewGeneration.current;
    const identity=identityEpoch.current;
    await perform(async()=>{
      const target=newJoiningDate;
      setDatePreview(null);
      const response=await request<DatePreview>(
        '/api/v1/cases/'+detail.case_id+'/joining-date/preview?joining_date='+
          encodeURIComponent(target),'GET',undefined,
        {'If-Match':'"case:'+detail.case_id+':v'+detail.case_version+'"'});
      if(datePreviewGeneration.current===generation&&identityEpoch.current===identity)
        setDatePreview(response);
    });
  }
  async function commitJoiningDate(){
    if(!selected||!detail||!datePreview||!me)return;
    if(datePreview.new_joining_date!==newJoiningDate||
      datePreview.case_version!==detail.case_version)return;
    const caseId=detail.case_id;
    await perform(async()=>{
      await request('/api/v1/cases/'+caseId+'/joining-date/commit','POST',{
        joining_date:datePreview.new_joining_date,
        preview_digest:datePreview.preview_digest,
        reason:dateChangeReason},{
          'If-Match':'"case:'+caseId+':v'+datePreview.case_version+'"'
        });
      setDatePreview(null);setDateChangeReason('');
      setGuidance(null);setAiAnswer(null);setExceptionsLoaded(false);setExceptions([]);
      datePreviewGeneration.current+=1;
      await reloadCase(caseId,me);
      setSelected(old=>old&&old.id===caseId?
        {...old,joining_date:datePreview.new_joining_date}:old);
    });
  }
  async function loadGuidance(caseId:string){
    const generation=identityEpoch.current;
    const result=await request<Guidance>('/api/v1/cases/'+caseId+'/companion/guidance');
    if(identityEpoch.current!==generation)return;
    setGuidance(result);
  }
  async function askCompanion(caseId:string){
    const generation=identityEpoch.current;
    const aiGeneration=aiRequestEpoch.current;
    const question=aiQuestion.trim();
    if(!question||question.length>400)return;
    setBusy(true);
    try{
      const result=await request<CompanionAnswer>(
        '/api/v1/cases/'+caseId+'/companion/answer','POST',{question});
      if(identityEpoch.current!==generation||aiRequestEpoch.current!==aiGeneration)return;
      setAiAnswer(result);
      if(!result.ai_model_used&&result.guidance){setGuidance(result.guidance);}
      setMessage(result.ai_model_used?'Validated model response received. No workflow changes made.':
        'Real AI unavailable: '+(result.error_code||'UNKNOWN')+'. Deterministic guidance shown.');
    }catch(e){
      if(identityEpoch.current===generation&&aiRequestEpoch.current===aiGeneration)
        setMessage('Question failed: '+
        (e instanceof Error?e.message:String(e)));
    }finally{setBusy(false);}
  }
  async function loadExceptions(caseId:string){
    const generation=identityEpoch.current;
    const result=await request<{results:ExceptionRecord[]}>(
      '/api/v1/cases/'+caseId+'/exceptions');
    if(identityEpoch.current!==generation)return;
    setExceptions(result.results);setExceptionsLoaded(true);
  }
  async function exceptionCommand(caseId:string,route:string,body:unknown){
    if(!detail||!me)return;
    await perform(async()=>{
      await request('/api/v1/cases/'+caseId+'/exceptions'+route,'POST',body,
        {'If-Match':'"case:'+caseId+':v'+detail.case_version+'"'});
      await reloadCase(caseId,me);
      setGuidance(null);setAiAnswer(null);
      await loadExceptions(caseId);
      setExceptionNote('');
    });
  }
  async function recoverUnavailableOwner(episode:ExceptionRecord){
    if(!me||!detail||me.role!=='HR'||episode.cause!=='OWNER_UNAVAILABLE')return;
    if(episode.task_owner_role!=='IT'&&episode.task_owner_role!=='MANAGER')return;
    const target=recoveryOwner[episode.id];
    if(!target||recoveryReason.trim().length<8)return;
    const caseId=detail.case_id;
    await perform(async()=>{
      await request('/api/v1/cases/'+caseId+'/assignments','POST',{
        role:episode.task_owner_role,new_member_id:target,reason:recoveryReason.trim()
      },{'If-Match':'"case:'+caseId+':v'+detail.case_version+'"'});
      await reloadCase(caseId,me);
      setGuidance(null);setAiAnswer(null);setRecoveryReason('');setRecoveryOwner({});
      await loadExceptions(caseId);
      setMessage('Recovery owner reassigned; resolve exception only after confirming underlying blocker cleared.');
    });
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
  async function closeout(){
    if(!selected||!detail||!me||me.role!=='HR'||
       detail.case_status!=='ACTIVE'||detail.progress.mandatory_remaining!==0)return;
    await perform(async()=>{
      await request('/api/v1/cases/'+selected.id+'/closeout','POST',{},
        {'If-Match':'"case:'+selected.id+':v'+detail.case_version+'"'});
      setGuidance(null);setAiAnswer(null);
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
    const selection=aiRequestEpoch.current;
    const caseId=detail.case_id;
    // A different role can submit while this case is open. Re-read the
    // authoritative version before the command; keep If-Match fail-closed.
    try{
      const current=await request<TaskPayload>('/api/v1/cases/'+caseId+'/tasks');
      if(identityEpoch.current!==generation||aiRequestEpoch.current!==selection)
        throw new Error('Selected case changed. Review the latest case before retrying.');
      await request(path,'POST',body,{'If-Match':'"case:'+caseId+':v'+current.case_version+'"'});
    }catch(e){
      if(identityEpoch.current===generation&&aiRequestEpoch.current===selection){
        try{await reloadCase(caseId,me);}catch{/* Preserve the original error. */}
      }
      if(e instanceof Error&&e.message==='STALE_VERSION')
        throw new Error('Case changed during your action. No approval was recorded. Reload form history and review the latest revision.');
      throw e;
    }
    if(identityEpoch.current!==generation||aiRequestEpoch.current!==selection)return;
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
      await request('/api/v1/cases','POST',{employee_id:employeeChoice,
        template_version_id:templateChoice,joining_date:joiningDate,
        owners:{IT:itChoice,MANAGER:managerChoice}});
      await refresh(me);
      setMessage('Case persisted in CREATED. Select it to activate when ready.');
    });
  }
  const publishedTemplates=templates.filter(t=>t.state==='PUBLISHED');
  const templateChoice=templateId||(publishedTemplates.length===1?publishedTemplates[0].version_id:'');
  const employeeChoice=employeeId||((owners.EMPLOYEE||[]).length===1?owners.EMPLOYEE[0].id:'');
  const itChoice=itId||((owners.IT||[]).length===1?owners.IT[0].id:'');
  const managerChoice=managerId||((owners.MANAGER||[]).length===1?owners.MANAGER[0].id:'');
  const currentWork=work.filter(t=>t.state==='READY'||t.state==='IN_PROGRESS')
    .sort((a,b)=>a.due_at.localeCompare(b.due_at)||a.title.localeCompare(b.title));
  const workflow=detail?workflowPresentation(detail.tasks):null;
  const activeTaskIndex=workflow?
    Math.max(0,workflow.current.findIndex(task=>task.id===focusedTaskId)):0;
  const activeTask=workflow?.current[activeTaskIndex]||null;
  return <main className="shell">
    <header className="topbar"><div><span className="eyebrow">Aster Vale Labs — synthetic demo</span><h1>Onboarding Companion</h1>
      <p>Know what needs doing, by whom, and what comes next.</p></div>
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
          <button className={tab==='work'?'selected':'quiet'} onClick={()=>setTab('work')}>My work ({currentWork.length})</button>
          <button className={tab==='inbox'?'selected':'quiet'} onClick={()=>setTab('inbox')}>In-app inbox</button>
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
            {detail.case_status==='ACTIVE'&&me.role==='HR'&&
              <div className="subpanel">
                <p className="meta">HR closeout checks typed evidence for every applicable mandatory
                  task and refuses any unclosed exception. No automatic waiver is available.</p>
                <button disabled={busy||detail.progress.mandatory_remaining!==0}
                  onClick={()=>void closeout()}>Confirm final onboarding closeout</button>
              </div>}
            {detail.case_status==='PRE_JOINING'&&me.role==='HR'&&
              <section className="subpanel" aria-label="Joining date reschedule">
                <h4>Change joining date — preview before approval</h4>
                <p className="meta">Current joining date: {selected.joining_date}. Untouched tasks are
                  rescheduled from the published template; started and completed evidence stays historical.</p>
                <label>Proposed joining date
                  <input aria-label="Proposed joining date" type="date"
                    value={newJoiningDate} onChange={e=>{
                      datePreviewGeneration.current+=1;
                      setNewJoiningDate(e.target.value);setDatePreview(null);}}/>
                </label>
                <button disabled={busy||!newJoiningDate||newJoiningDate===selected.joining_date}
                  onClick={()=>void previewJoiningDate()}>Preview date change impact</button>
                {datePreview&&<>
                  <h5>Review actual schedule changes</h5>
                  <p>{datePreview.change_count} untouched task(s) move;
                    {datePreview.preserved_count} started/completed task(s) stay unchanged.</p>
                  {datePreview.changes.map(x=><p key={x.task_id} className="meta">
                    {x.title}: due {new Date(x.old_due_at).toLocaleString()}
                    {' → '}{new Date(x.new_due_at).toLocaleString()}
                  </p>)}
                  {datePreview.warnings.map((x,i)=><p className="meta" key={i}>{x}</p>)}
                  <label>HR confirmation reason (8–240 characters)
                    <textarea aria-label="Joining date change reason" minLength={8} maxLength={240}
                      required value={dateChangeReason}
                      onChange={e=>setDateChangeReason(e.target.value)}/>
                  </label>
                  <button disabled={busy||dateChangeReason.trim().length<8||
                    datePreview.case_version!==detail.case_version}
                    onClick={()=>void commitJoiningDate()}>Approve and commit previewed date change</button>
                </>}
              </section>}
            {detail.tasks.length===0&&<p>Tasks will be instantiated only after successful activation.</p>}
            {workflow&&detail.tasks.length>0&&<section className="subpanel" aria-label="Focused current work">
              <div className="heading">
                <div>
                  <h4>{showFullPlan?'All workflow steps':'Next steps'}</h4>
                  <p className="meta">{workflow.current.length} available · {workflow.completed.length} done · {workflow.futureCount} upcoming</p>
                </div>
                {!showFullPlan&&workflow.current.length>1&&<div className="task-actions" role="group" aria-label="Choose current step">
                  <button className="quiet" disabled={busy||activeTaskIndex===0}
                    onClick={()=>setFocusedTaskId(workflow.current[activeTaskIndex-1].id)}>
                    Previous step</button>
                  <span className="meta">Step {activeTaskIndex+1} of {workflow.current.length}</span>
                  <button className="quiet" disabled={busy||activeTaskIndex===workflow.current.length-1}
                    onClick={()=>setFocusedTaskId(workflow.current[activeTaskIndex+1].id)}>
                    Next step</button>
                </div>}
              </div>
              <button className="quiet" disabled={busy}
                onClick={()=>{setShowFullPlan(v=>!v);setAttestTask(null);}}>
                {showFullPlan?'Return to focused work':'View all steps (advanced)'}
              </button>
              {!activeTask&&!showFullPlan&&<p>No work ready yet. Upcoming work unlocks after prerequisites and dates permit.</p>}
              <div className="task-list">{(showFullPlan?detail.tasks:(activeTask?[activeTask]:[])).map(t=><article key={t.id} className="task">
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
                  role={me.role} prefillName={me.display_name} prefillEmail={me.email}
                  read={path=>request(path)} mutate={mutateEvidence}
                  refreshCase={()=>reloadCase(detail.case_id,me)}
                  uploadDocument={uploadDocument} uploadSecureDocument={uploadSecureDocument}/>}
              {attestTask===t.id&&<form className="form attest" onSubmit={e=>void attest(e)}>
                <label>First-week plan<input required minLength={8} maxLength={300} value={plan} onChange={e=>setPlan(e.target.value)}/></label>
                <label>Buddy's name<input required minLength={2} maxLength={100} value={buddy} onChange={e=>setBuddy(e.target.value)}/></label>
                <label className="check"><input type="checkbox" checked={station} onChange={e=>setStation(e.target.checked)}/> Workstation is ready</label>
                <label>Attestation note<textarea required maxLength={500} value={note} onChange={e=>setNote(e.target.value)}/></label>
                <button disabled={busy||!station} type="submit">Submit recorded evidence</button>
              </form>}
            </article>)}</div>
            </section>}
            {!showFullPlan&&workflow&&workflow.completed.length>0&&<details className="subpanel"
              aria-label="Completed onboarding steps">
              <summary>Completed steps ({workflow.completed.length})</summary>
              <div className="task-list">{workflow.completed.map(t=><article key={t.id} className="task">
                <div><strong>{t.title}</strong>
                  <p className="meta">{t.kind} · {t.owner_role} · COMPLETED</p>
                  <details><summary>Review completed evidence</summary>
                    {(t.kind==='FORM'||t.kind==='DOCUMENT'||t.kind==='TRAINING'||t.kind==='POLICY_ACK'||t.kind==='ACTIVITY'||t.kind==='INTRODUCTION'||t.kind==='CHECK_IN'||t.kind==='ACCESS'||t.kind==='EQUIPMENT'||t.kind==='EQUIPMENT_RECEIPT')&&
                      <EvidenceWorkflows key={me.user_id+':'+t.id} task={t} caseId={detail.case_id}
                        role={me.role} prefillName={me.display_name} prefillEmail={me.email}
                  read={path=>request(path)} mutate={mutateEvidence}
                        refreshCase={()=>reloadCase(detail.case_id,me)}
                        uploadDocument={uploadDocument} uploadSecureDocument={uploadSecureDocument}/>}
                  </details>
                </div>
              </article>)}</div>
            </details>}
            <details role="region" className="subpanel" aria-label="Case companion guidance">
              <summary>Guidance and policy assistant</summary>
              <div className="heading"><h4>Current blocker and next-action guidance</h4>
                <button className="quiet" disabled={busy}
                  onClick={()=>void perform(()=>loadGuidance(detail.case_id))}>
                  Analyze current case
                </button>
              </div>
              <p className="meta">Deterministic current-state guidance; no AI model call, external
                provider, autonomous approval or message sending.</p>
              <div className="form">
                 <label>Ask about a synthetic policy or next action
                   <input value={aiQuestion} maxLength={400} onChange={e=>setAiQuestion(e.target.value)}
                     placeholder="What conduct policy applies to me?"/>
                 </label>
                 <button disabled={busy||!aiQuestion.trim()}
                   onClick={()=>void askCompanion(detail.case_id)}>Ask read-only companion</button>
               </div>
               <p className="meta">External model inference is opt-in and requires an approved
                 provider/API configuration. The response cannot approve or change any task.</p>
               {aiAnswer?.ai_model_used&&aiAnswer.answer&&<div className="subpanel">
                 <strong>Model-generated, source-validated answer ({aiAnswer.answer.answer_type})</strong>
                 <p>{aiAnswer.answer.answer}</p>
                 <p className="meta">Model: {aiAnswer.model} · Source identifiers:
                   {' '}{aiAnswer.answer.citations.length?aiAnswer.answer.citations.join(', '):'None'}</p>
                 {!!aiAnswer.answer.recommended_actions.length&&<p className="meta">
                   Eligible next-action IDs: {aiAnswer.answer.recommended_actions.join(', ')}
                 </p>}
                 {aiAnswer.answer.limitations.map((x,i)=><p className="meta" key={i}>{x}</p>)}
               </div>}
               {aiAnswer&&!aiAnswer.ai_model_used&&<p className="meta">
                 No model answer was produced ({aiAnswer.error_code}).
                 Current-state deterministic guidance is displayed below.
               </p>}
               {guidance&&<>
                <p className="meta">Evaluated case v{guidance.case_version}</p>
                <h5>Your eligible next actions</h5>
                {!guidance.actionable.length&&<p>Nothing currently actionable for this role.</p>}
                {guidance.actionable.map(x=><p key={x.task_id+':'+x.action}>
                  {x.task_title} — {x.action} (due {new Date(x.due_at).toLocaleString()})
                </p>)}
                <h5>Open exception episodes</h5>
                {!guidance.open_exceptions.length&&<p>No current exception episodes.</p>}
                {guidance.open_exceptions.map(x=><p key={x.id}>
                  {x.task_title} — {x.cause}, episode {x.episode}, {x.status}
                  {x.assignee_role?' · '+x.assignee_role:''}
                </p>)}
                <h5>Evidence-based blockers</h5>
                {!guidance.blockers.length&&<p>No current dependency or unavailable-owner blockers.</p>}
                {guidance.blockers.map((x,i)=><div key={i}>
                  <strong>{x.task_title}</strong>
                  <p className="meta">{x.reason_codes.join(', ')}</p>
                  {x.unmet_prerequisites.map((p,j)=><p key={j} className="meta">
                    Waiting on {p.task_title} ({p.owner_role} · {p.state})
                  </p>)}
                </div>)}
              </>}
            </details>
            <details role="region" className="subpanel" aria-label="Case exceptions">
              <summary>Exceptions and recovery</summary>
              <div className="heading"><h4>Exception recovery</h4>
                <button className="quiet" disabled={busy}
                  onClick={()=>void perform(()=>loadExceptions(detail.case_id))}>Load current exceptions</button>
              </div>
              <p className="meta">Resolution requires a real correction to the underlying task.
                Exception status never unlocks a dependency or approves evidence.</p>
              {!exceptionsLoaded&&<p>Load exceptions to inspect current blockers and episodes.</p>}
              {exceptionsLoaded&&!exceptions.length&&<p>No exceptions recorded for this case.</p>}
              {exceptionsLoaded&&<div className="task-list">{exceptions.map(x=>
                <article key={x.id} className="task">
                  <div><strong>{x.task_title}</strong>
                    <p className="meta">{x.cause} · Episode {x.episode} · {x.status}
                      {x.assignee_role?' · '+x.assignee_role:''}</p>
                    <p>{x.reason}</p>
                    <p className="meta">{x.blocking_now?'Underlying blocker remains active':'Underlying condition cleared'}</p>
                    <details><summary>Audited exception history ({x.events.length} transitions)</summary>
                      {x.events.map((event,i)=><p key={i} className="meta">{event.action}
                        {' · '}{new Date(event.created_at).toLocaleString()}
                        {' — '}{event.note}</p>)}
                    </details>
                  </div>
                  <div className="task-actions">
                    {me.role==='HR'&&x.cause==='OWNER_UNAVAILABLE'&&x.blocking_now&&
                      (x.status==='OPEN'||x.status==='ASSIGNED')&&
                      (x.task_owner_role==='IT'||x.task_owner_role==='MANAGER')&&
                      <div className="form" role="group" aria-label={'Recover '+x.task_title+' owner'}>
                        <strong>Recover unavailable {x.task_owner_role} owner</strong>
                        <label>Available replacement
                          <select aria-label={'Replacement owner for '+x.task_title}
                            value={recoveryOwner[x.id]||''}
                            onChange={e=>setRecoveryOwner(p=>({...p,[x.id]:e.target.value}))}>
                            <option value="">Select an available case owner</option>
                            {(owners[x.task_owner_role]||[]).map(o=><option key={o.id}
                              value={o.id}>{o.name}</option>)}
                          </select>
                        </label>
                        <label>Reason for ownership recovery
                          <textarea aria-label="Owner recovery reason" minLength={8} maxLength={240}
                            value={recoveryReason} onChange={e=>setRecoveryReason(e.target.value)}/>
                        </label>
                        <button disabled={busy||!recoveryOwner[x.id]||recoveryReason.trim().length<8}
                          onClick={()=>void recoverUnavailableOwner(x)}>Reassign current task owner</button>
                      </div>}
                    {me.role==='HR'&&(x.status==='OPEN'||x.status==='ASSIGNED')&&<>
                      <label>Assign owner
                        <select value={exceptionAssignees[x.id]||'HR'}
                          onChange={e=>setExceptionAssignees(old=>({...old,[x.id]:e.target.value}))}>
                          <option value="HR">HR</option><option value="IT">IT</option>
                          <option value="MANAGER">Manager</option>
                        </select>
                      </label>
                      <button disabled={busy} onClick={()=>void exceptionCommand(
                        detail.case_id,'/'+x.id+'/assign',{assignee_role:exceptionAssignees[x.id]||'HR',
                          note:exceptionNote.trim()||'Assign exception to current role owner'})}>Assign</button>
                    </>}
                    {x.status==='ASSIGNED'&&(me.role==='HR'||me.role===x.assignee_role)&&
                      <button disabled={busy||x.blocking_now} title={x.blocking_now?'Clear actual task blocker first':''}
                        onClick={()=>void exceptionCommand(detail.case_id,'/'+x.id+'/resolve',{
                          note:exceptionNote.trim()||'Underlying task condition verified as cleared'})}>Resolve after correction</button>}
                    {x.status==='RESOLVED'&&me.role==='HR'&&
                      <button disabled={busy||x.blocking_now}
                        onClick={()=>void exceptionCommand(detail.case_id,'/'+x.id+'/close',{
                          note:exceptionNote.trim()||'HR verified current predicate and closure'})}>Close verified exception</button>}
                  </div>
                </article>)}</div>}
              <form className="form" onSubmit={e=>{
                e.preventDefault();
                void exceptionCommand(detail.case_id,'/open',{
                  task_id:exceptionTask,cause:exceptionCause,note:exceptionNote});
              }}>
                <h5>Report a real task blocker</h5>
                <label>Task
                  <select aria-label="Exception task" required value={exceptionTask} onChange={e=>setExceptionTask(e.target.value)}>
                    <option value="">Select a task</option>
                    {detail.tasks.map(t=><option key={t.id} value={t.id}>{t.title}</option>)}
                  </select>
                </label>
                <label>Blocking condition
                  <select value={exceptionCause} onChange={e=>setExceptionCause(e.target.value)}>
                    <option value="PREREQUISITE_BLOCKED">Required predecessor incomplete</option>
                    <option value="OWNER_UNAVAILABLE">Assigned owner unavailable</option>
                    <option value="TASK_OVERDUE">Task overdue</option>
                  </select>
                </label>
                <label>Reason (8–240 characters)
                  <textarea aria-label="Exception report reason" minLength={8} maxLength={240} required value={exceptionNote}
                    onChange={e=>setExceptionNote(e.target.value)}/>
                </label>
                <button type="submit" disabled={busy||!exceptionTask||exceptionNote.trim().length<8}>
                  Open exception with current-state verification
                </button>
              </form>
            </details>
            <details className="meta"><summary>Evaluation limits</summary><p>
              Synthetic only: secure PDF intake, external AI and automatic background reminders
              are disabled on this free hosting plan.</p></details>
          </section>}
        </section>}
        {tab==='work'&&<section className="panel"><h2>My assigned tasks</h2>
          {!currentWork.length?<p>No tasks currently need your action. Future steps stay in the case plan.</p>:<div className="task-list">{currentWork.map(t=><article className="task" key={t.id}>
            <div><strong>{t.employee_name} — {t.title}</strong><p className="meta">{t.state} · {t.owner_role} · {t.kind}</p>
              {!!t.blocked_reason_codes.length&&<p className="block">{t.blocked_reason_codes.join(', ')}</p>}</div>
            <button disabled={busy} onClick={()=>{const c=cases.find(x=>x.id===t.case_id);if(c)void selectCase(c);}}>Open case</button>
          </article>)}</div>}
        </section>}
        {tab==='inbox'&&<section className="panel" aria-label="In-app inbox">
          <div className="heading"><h2>Reminders and handoffs</h2>
            <button className="quiet" disabled={busy} onClick={()=>void perform(loadInbox)}>Refresh inbox</button>
          </div>
          <details className="meta"><summary>Delivery details</summary><p>In-app only; email and calendar delivery are not enabled.</p></details>
          {!inboxLoaded&&<p>Loading authorized reminders…</p>}
          {inboxLoaded&&!inbox.length&&<p>No current reminders assigned to you.</p>}
          <div className="task-list">{inbox.map(item=><article className="task" key={item.id}>
            <div><strong>{item.summary}</strong>
              <p className="meta">{item.rule_code} · {new Date(item.created_at).toLocaleString()}
                {item.read_at?' · Read':' · Unread'}</p></div>
            <div className="task-actions">
              {!item.read_at&&<button disabled={busy}
                onClick={()=>void markInboxRead(item.id)}>Mark read</button>}
              <button disabled={busy||!cases.some(c=>c.id===item.case_id)}
                onClick={()=>{const c=cases.find(c=>c.id===item.case_id);
                  if(c)void selectCase(c);}}>Open assigned case</button>
            </div>
          </article>)}</div>
        </section>}
        {tab==='templates'&&me.role==='HR'&&<section className="panel"><h2>Versioned templates</h2>
          {me.capabilities?.manage_templates&&<button disabled={busy} onClick={()=>void createDefault()}>Create default synthetic 17-task template</button>}
          {!templates.length&&<p>No templates published or drafted yet.</p>}
          <div className="case-list">{templates.map(t=><button key={t.version_id} className="quiet" disabled={busy} onClick={()=>void showTemplate(t)}>
            {t.name} — v{t.version} {t.state} (revision {t.revision})
          </button>)}</div>
          {template&&<section className="subpanel"><h3>{template.name} v{template.version} — {template.state}</h3>
            <details className="meta"><summary>Version integrity</summary><p>Content SHA-256: <code>{template.content_hash||'Not published'}</code></p></details>
            {template.state==='DRAFT'&&me.capabilities?.manage_templates?<><label>Draft tasks and dependency JSON
              <textarea className="json-editor" value={editor} onChange={e=>setEditor(e.target.value)}/>
            </label><div className="actions"><button disabled={busy} onClick={()=>void saveDraft()}>Save draft</button>
              <button disabled={busy} onClick={()=>void publish()}>Validate and publish</button></div></>
             :<><p>{template.state==='PUBLISHED'?'Published versions are immutable. Active cases retain their original snapshot.':'This draft is read-only for your current role capability.'}</p>
               {template.state==='PUBLISHED'&&me.capabilities?.manage_templates&&<button disabled={busy} onClick={()=>void clone()}>Create next version draft</button>}</>}
          </section>}
        </section>}
        {me.role==='HR'&&tab==='cases'&&<section className="panel"><h2>Create an onboarding case</h2>
          <p className="meta">Choose a joining date. Available single choices are preselected; HR owns this case.</p>
          <form className="form" onSubmit={e=>void createCase(e)}>
            <label>Published template<select required value={templateChoice} onChange={e=>setTemplateId(e.target.value)}><option value="">Select template</option>
              {publishedTemplates.map(t=><option value={t.version_id} key={t.version_id}>{t.name} v{t.version}</option>)}</select></label>
            <label>Employee<select required value={employeeChoice} onChange={e=>setEmployeeId(e.target.value)}><option value="">Select employee</option>
              {(owners.EMPLOYEE||[]).map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
            <label>IT owner<select required value={itChoice} onChange={e=>setItId(e.target.value)}><option value="">Select IT owner</option>
              {(owners.IT||[]).map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
            <label>Manager<select required value={managerChoice} onChange={e=>setManagerId(e.target.value)}><option value="">Select manager</option>
              {(owners.MANAGER||[]).map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
            <label>Joining date<input type="date" required value={joiningDate} onChange={e=>setJoiningDate(e.target.value)}/></label>
            <button type="submit" disabled={busy||!templateChoice||!employeeChoice||!itChoice||!managerChoice||!joiningDate}>Create case</button>
          </form>
        </section>}
      </div>
    </div>}
    <p aria-live="polite" role="status" className="status">{message}</p>
    <footer><small>Local/CI synthetic demonstration. This is not a hosted production system and does not process real employee data.</small></footer>
  </main>;
}
