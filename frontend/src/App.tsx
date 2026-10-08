import { useEffect, useState } from 'react';
type Me = { display_name:string;role:string; user_id:string };
type Case = {id:string; status:string; joining_date:string; employee_name:string; version:number};
export default function App(){
  const [me,setMe] = useState<Me|null>(null);
  const [csrf,setCsrf] = useState('');
  const [email,setEmail] = useState('');
  const [password,setPassword] = useState('');
  const [cases,setCases] = useState<Case[]>([]);
  const [message,setMessage] = useState('Session not established.');
  useEffect(()=>{ void (async()=>{
    try {
      const r=await fetch('/api/v1/auth/csrf',{credentials:'same-origin'});
      if (!r.ok) throw new Error('CSRF initialization unavailable');
      setCsrf((await r.json()).csrf_token);
      const m=await fetch('/api/v1/auth/me',{credentials:'same-origin'});
      if(m.ok) setMe(await m.json());
    } catch{setMessage('Authentication service unavailable.');}
  })();},[]);
  useEffect(()=>{if(!me)return; void (async()=>{
    const r=await fetch('/api/v1/cases',{credentials:'same-origin'});
    if(r.ok)setCases((await r.json()).results);
    else setMessage('Case list unavailable or access denied.');
  })();},[me]);
  async function signIn(e:React.FormEvent){
    e.preventDefault();setMessage('Signing in...');
    try {const r=await fetch('/api/v1/auth/login',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({email,password})});
    if(!r.ok){setMessage('Sign in failed. Please verify the account and password.');return;}
    const identity=await fetch('/api/v1/auth/me',{credentials:'same-origin'});
    if(!identity.ok) throw new Error('Session unavailable');
    const newCsrf=await fetch('/api/v1/auth/csrf',{credentials:'same-origin'});
    if(!newCsrf.ok) throw new Error('CSRF refresh unavailable');
    setCsrf((await newCsrf.json()).csrf_token);
    setPassword('');setMe(await identity.json());setMessage('Signed in.');
    }catch{setMessage('Authentication service unavailable.');}
  }
  async function signOut(){
    try {
      const r=await fetch('/api/v1/auth/logout',{method:'POST',credentials:'same-origin',headers:{'X-CSRFToken':csrf}});
      if(!r.ok) throw new Error('Server refused logout');
      setMe(null);setCases([]);setMessage('Signed out.');
      const token=await fetch('/api/v1/auth/csrf',{credentials:'same-origin'});
      if(token.ok)setCsrf((await token.json()).csrf_token);
    } catch {setMessage('Sign out could not be confirmed. Please retry.');}
  }
  return <main style={{fontFamily:'system-ui',maxWidth:800,margin:'4rem auto',padding:'1.5rem',lineHeight:1.6}}>
    <h1>Employee Onboarding Companion</h1>
    <p><strong>M1 — Identity and security foundation.</strong> Onboarding task workflows are not available yet.</p>
    {me? <section aria-label="Current session"><h2>Signed in as {me.display_name}</h2><p>Role: {me.role}</p>
    <button onClick={()=>void signOut()}>Sign out</button><h3>Authorized case previews</h3>
    {cases.length?<ul>{cases.map(c=><li key={c.id}>{c.employee_name} — {c.status} — joining {c.joining_date}</li>)}</ul>:<p>No cases assigned yet.</p>}</section>
    :<form onSubmit={e=>void signIn(e)}><h2>Sign in</h2>
    <label>Email <input type="email" required autoComplete="username" value={email} onChange={e=>setEmail(e.target.value)}/></label>
    <label style={{display:'block'}}>Password <input type="password" required autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label>
    <button type="submit" disabled={!csrf}>Sign in</button></form>}
    <p aria-live="polite" role="status">{message}</p>
  </main>;
}
