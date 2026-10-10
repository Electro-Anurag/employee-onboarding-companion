'use strict';
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');
const file=process.env.M3_LIVE_BROWSER_CREDENTIAL_FILE;
const valid=process.env.M3_LIVE_BROWSER_VALID_PDF;
const invalid=process.env.M3_LIVE_BROWSER_INVALID_PDF;
const crashMarker=process.env.M3_CI_CRASH_MARKER;
if(!file||!valid||!invalid||!crashMarker)throw Error('Live browser fixture, PDF or crash marker missing');
let caseId;
const users={};
for(const line of fs.readFileSync(file,'utf8').split(/\r?\n/)){
  const c=line.match(/^CASE\s+([\da-f-]{36})$/);
  const u=line.match(/^(HR|EMPLOYEE|IT|MANAGER)\s+(\S+)\s+(\S+)$/);
  if(c)caseId=c[1];
  if(u)users[u[1]]={email:u[2],password:u[3]};
}
if(!caseId||!users.HR||!users.EMPLOYEE)throw Error('Invalid live credentials');
async function login(page,role){
  await page.goto('/');
  await page.getByLabel('Email').fill(users[role].email);
  await page.getByLabel('Password').fill(users[role].password);
  await page.getByRole('button',{name:'Sign in'}).click();
  await expect(page.getByText('Role: '+role)).toBeVisible();
}
async function open(page){
  await page.getByRole('button',{name:/^Cases \(/}).click();
  await page.locator('.case-list').first().getByRole('button').first().click();
  await expect(page.getByRole('region',{name:'Case tasks'})).toBeVisible();
}
function card(page,name){
  return page.getByRole('region',{name:'Case tasks'}).locator('article.task')
    .filter({has:page.getByRole('heading',{name,exact:true})});
}
async function history(page,taskId){
  const response=await page.request.get('/api/v1/cases/'+caseId+'/tasks/'+taskId+'/secure-documents');
  expect(response.status()).toBe(200);
  return (await response.json()).results;
}
async function taskData(page){
  const response=await page.request.get('/api/v1/cases/'+caseId+'/tasks');
  expect(response.status()).toBe(200);
  return await response.json();
}
async function pdfUpload(page,pdf){
  const doc=card(page,'Live Identity PDF');
  await doc.getByRole('button',{name:'Load S3 document processing history'}).click();
  await doc.locator('input[type="file"]').setInputFiles({
    name:pdf===invalid?'synthetic_invalid.pdf':'synthetic_recovered.pdf',
    mimeType:'application/pdf',buffer:fs.readFileSync(pdf)});
  await doc.getByRole('button',{name:'Upload to private S3 quarantine'}).click();
}
test('R2: browser invalid correction, reload resume, actual web hard exit after S3 PUT, recovered HR approval',async({browser})=>{
  test.setTimeout(210000);
  const empContext=await browser.newContext(),hrContext=await browser.newContext();
  const employee=await empContext.newPage(),hr=await hrContext.newPage();
  try{
    await login(employee,'EMPLOYEE');await open(employee);
    const data=await taskData(employee);
    const task=data.tasks.find(t=>t.key==='identity_document');
    const successor=data.tasks.find(t=>t.key==='equipment_setup');
    expect(task&&successor).toBeTruthy();
    expect(successor.state).toBe('BLOCKED');

    await test.step('invalid synthetically generated PDF stays unreceived and cannot unlock',async()=>{
      await pdfUpload(employee,invalid);
      await expect(card(employee,'Live Identity PDF')).toContainText('INVALID_OR_UNSAFE_PDF');
      await employee.reload();await expect(employee.getByText('Role: EMPLOYEE')).toBeVisible();
      await open(employee);
      const records=await history(employee,task.id);
      expect(records).toHaveLength(1);
      expect(records[0].state).toBe('AWAITING_CONTENT');
      expect(records[0].quarantine_stored).toBe(false);
      expect((await taskData(employee)).tasks.find(t=>t.key==='equipment_setup').state).toBe('BLOCKED');
    });

    let replacementId;
    await test.step('corrected file creates audited supersession; browser abort before content and reload',async()=>{
      let intercepted=false;
      await employee.route('**/secure-documents/*/content',async route=>{
        intercepted=true;
        await route.abort('failed');
      });
      await pdfUpload(employee,valid);
      await expect.poll(()=>intercepted).toBe(true);
      await employee.unroute('**/secure-documents/*/content');
      await employee.reload();await expect(employee.getByText('Role: EMPLOYEE')).toBeVisible();
      await open(employee);
      const records=await history(employee,task.id);
      expect(records).toHaveLength(2);
      expect(records[0].state).toBe('AWAITING_CONTENT');
      expect(records[1].state).toBe('AWAITING_CONTENT');
      expect(records[1].revision).toBe(2);
      replacementId=records[1].id;
      expect(records[1].quarantine_stored).toBe(false);
    });

    await test.step('same-file reload resume triggers real successful S3 PUT and kills web before DB receipt',async()=>{
      expect(fs.existsSync(crashMarker)).toBe(false);
      await pdfUpload(employee,valid);
      await expect.poll(()=>fs.existsSync(crashMarker),{timeout:30000}).toBe(true);
      expect(fs.readFileSync(crashMarker,'utf8')).toContain('WEB_EXIT_79_AFTER_REAL_S3_PUT');
      await expect.poll(async()=>{
        try{return (await employee.request.get('/health/ready',{timeout:3000})).status();}
        catch{return 0;}
      },{timeout:30000}).toBe(200);
      // Both the upload and scan receipt must remain absent after hard exit.
      const records=await history(employee,task.id);
      expect(records).toHaveLength(2);
      expect(records[1].id).toBe(replacementId);
      expect(records[1].state).toBe('AWAITING_CONTENT');
      expect(records[1].quarantine_stored).toBe(false);
      expect(records[1].scan_attempts).toHaveLength(0);
    });

    await test.step('browser reload exact same file reconciles S3 412 without duplicated upload',async()=>{
      await employee.reload();await expect(employee.getByText('Role: EMPLOYEE')).toBeVisible();
      await open(employee);
      await pdfUpload(employee,valid);
      await expect(card(employee,'Live Identity PDF')).toContainText(/QUARANTINED|AWAITING_HR_REVIEW/);
      const records=await history(employee,task.id);
      expect(records).toHaveLength(2);
      expect(records[1].id).toBe(replacementId);
      expect(records[1].quarantine_stored).toBe(true);
      expect((await taskData(employee)).tasks.find(t=>t.key==='equipment_setup').state).toBe('BLOCKED');
      await expect.poll(async()=>{
        const rows=await history(employee,task.id);
        return rows.at(-1).state;
      },{timeout:60000,intervals:[500,1000,2000]}).toBe('AWAITING_HR_REVIEW');
      expect((await taskData(employee)).tasks.find(t=>t.key==='equipment_setup').state).toBe('BLOCKED');
    });

    await test.step('separate HR acceptance unlocks successor with preserved two revisions',async()=>{
      await login(hr,'HR');await open(hr);
      const doc=card(hr,'Live Identity PDF');
      await doc.getByRole('button',{name:'Load S3 document processing history'}).click();
      await expect(doc).toContainText('AWAITING_HR_REVIEW');
      await doc.getByLabel('Clean-object HR decision').selectOption('ACCEPTED');
      await doc.getByLabel('HR review evidence').fill('Actual S3, scanner, and recovery checked by assigned synthetic HR');
      await doc.getByRole('button',{name:'Record HR decision for exact clean version'}).click();
      await expect(doc).toContainText('COMPLETED');
      await hr.reload();await expect(hr.getByText('Role: HR')).toBeVisible();await open(hr);
      await expect(card(hr,'Blocked Equipment')).toContainText('READY');
      const rows=await history(hr,task.id);
      expect(rows).toHaveLength(2);
      expect(rows.at(-1).review.decision).toBe('ACCEPTED');
    });
  }finally{await Promise.allSettled([empContext.close(),hrContext.close()]);}
});
