'use strict';
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');

function credentials(){
  const path=process.env.M2_BROWSER_CREDENTIAL_FILE;
  if(!path)throw new Error('Synthetic credential-file path is required');
  const lines=fs.readFileSync(path,'utf8').split(/\r?\n/);
  const result={};
  for(const line of lines){
    const match=line.trim().match(/^(HR|EMPLOYEE|IT|MANAGER)\s+(\S+)\s+(\S+)$/);
    if(match)result[match[1]]={email:match[2],password:match[3]};
  }
  for(const role of ['HR','EMPLOYEE','IT','MANAGER']){
    if(!result[role])throw new Error('Incomplete ephemeral test fixture for '+role);
  }
  return result;
}
const users=credentials();

async function login(page,role){
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
  await page.getByLabel('Email').fill(users[role].email);
  await page.getByLabel('Password').fill(users[role].password);
  await expect(page.getByRole('button',{name:'Sign in'})).toBeEnabled();
  await page.getByRole('button',{name:'Sign in'}).click();
  await expect(page.getByText('Role: '+role)).toBeVisible();
  await expect(page.getByRole('navigation',{name:'Workspace'})).toBeVisible();
  // The neutral empty status toast is intentionally omitted for clarity.
  await expect(page.getByRole('status').filter({hasText:'Unable to read workspace'})).toHaveCount(0);
}
function caseButton(page){
  return page.locator('.case-list').first().getByRole('button').first();
}
function taskCard(page,title){
  return page.getByRole('region',{name:'Case tasks'}).locator('article.task')
    .filter({has:page.getByRole('heading',{name:title,exact:true})});
}
async function openCase(page){
  await page.getByRole('button',{name:/^Cases \(/}).click();
  await expect(caseButton(page)).toBeVisible();
  await caseButton(page).click();
  await expect(page.getByRole('region',{name:'Case tasks'})).toBeVisible();
  const full=page.getByRole('button',{name:'View all steps (advanced)'});
  if(await full.isVisible())await full.click();
}

test('four-role real-browser case, template, dependency and evidence journey',async({browser})=>{
  test.setTimeout(220000);
  const hrContext=await browser.newContext();
  const itContext=await browser.newContext();
  const managerContext=await browser.newContext();
  const employeeContext=await browser.newContext();
  const hr=await hrContext.newPage();
  const it=await itContext.newPage();
  const manager=await managerContext.newPage();
  const employee=await employeeContext.newPage();
  let caseId,managerTaskId;

  try{
    await test.step('HR signs in with real session/CSRF and publishes immutable template',async()=>{
      await login(hr,'HR');
      await expect(hr.getByRole('button',{name:/Templates \(/})).toBeVisible();
      await hr.getByRole('button',{name:/Templates \(/}).click();
      await hr.getByRole('button',{name:'Create default synthetic 17-task template'}).click();
      await expect(hr.getByRole('heading',{name:/Employee First Month.*DRAFT/})).toBeVisible();
      await hr.getByRole('button',{name:'Validate and publish'}).click();
      await expect(hr.getByRole('heading',{name:/Employee First Month.*PUBLISHED/})).toBeVisible();
      await expect(hr.getByRole('button',{name:'Create next version draft'})).toBeVisible();
    });

    await test.step('HR creates case using UI; non-HR cannot see unactivated case',async()=>{
      await hr.getByRole('button',{name:/^Cases \(/}).click();
      const form=hr.locator('section.panel').filter({has:hr.getByRole('heading',{name:'Create an onboarding case'})});
      await expect(form).toBeVisible();
      await form.locator('select').nth(0).selectOption({index:1});
      await form.locator('select').nth(1).selectOption({index:1});
      await form.locator('select').nth(2).selectOption({index:1});
      await form.locator('select').nth(3).selectOption({index:1});
      const join=new Date(Date.now()+21*86400000).toISOString().slice(0,10);
      await form.getByLabel('Joining date').fill(join);
      const [response]=await Promise.all([
        hr.waitForResponse(x=>x.url().endsWith('/api/v1/cases')&&x.request().method()==='POST'),
        form.getByRole('button',{name:'Create case'}).click()
      ]);
      expect(response.status()).toBe(201);
      const body=await response.json();
      caseId=body.case_id;
      expect(caseId).toMatch(/^[0-9a-f-]{36}$/);
      await expect(caseButton(hr)).toContainText('CREATED');

      await login(it,'IT');
      await expect(it.getByRole('button',{name:'Cases (0)'})).toBeVisible();
      await expect(it.getByRole('button',{name:'My work (0)'})).toBeVisible();
      expect((await it.request.get('/api/v1/cases/'+caseId)).status()).toBe(404);
      expect((await it.request.get('/api/v1/cases/'+caseId+'/tasks')).status()).toBe(404);
      await expect(it.getByRole('button',{name:/Templates \(/})).toHaveCount(0);
    });

    await test.step('HR activates 17 tasks; AND prerequisites block downstream work',async()=>{
      await openCase(hr);
      await expect(hr.getByRole('region',{name:'Case tasks'}).locator('article.task')).toHaveCount(0);
      await hr.getByRole('button',{name:'Activate case'}).click();
      await expect(hr.getByRole('region',{name:'Focused current work'}).locator('article.task')).toHaveCount(1);
      await expect(hr.getByRole('region',{name:'Focused current work'})).not.toContainText('Blocked: PREREQUISITE_INCOMPLETE');
      await hr.getByRole('button',{name:'View all steps (advanced)'}).click();
      await expect(hr.getByRole('region',{name:'Case tasks'}).locator('article.task')).toHaveCount(17);
      await expect(taskCard(hr,'Manager Preparation')).toContainText('READY');
      await expect(taskCard(hr,'Workspace Access')).toContainText('PREREQUISITE_INCOMPLETE');
      await expect(taskCard(hr,'Team Introduction')).toContainText('PREREQUISITE_INCOMPLETE');
      await expect(hr.getByText('0/17 mandatory tasks completed')).toBeVisible();
      await expect(hr.getByRole('button',{name:'Begin Day 1 (joining date required)'})).toBeVisible();
      await hr.getByRole('button',{name:'Begin Day 1 (joining date required)'}).click();
      await expect(hr.getByRole('status')).toContainText('JOIN_DATE_NOT_REACHED');
      await expect(hr.getByRole('region',{name:'Case tasks'})).toContainText('PRE_JOINING');
      await hr.reload();
      await expect(hr.getByText('Role: HR')).toBeVisible();
      await openCase(hr);
      await expect(hr.getByRole('region',{name:'Case tasks'}).locator('article.task')).toHaveCount(17);
    });

    await test.step('Manager completes ONLY typed preparation; task and progress persist',async()=>{
      await login(manager,'MANAGER');
      await expect(manager.getByRole('button',{name:/^My work \(/})).toBeVisible();
      await manager.getByRole('button',{name:/^My work \(/}).click();
      await expect(manager.getByText('Manager Preparation')).toBeVisible();
      await openCase(manager);
      const card=taskCard(manager,'Manager Preparation');
      await expect(card).toContainText('READY');
      const allTasks=await manager.request.get('/api/v1/cases/'+caseId+'/tasks');
      expect(allTasks.status()).toBe(200);
      managerTaskId=(await allTasks.json()).tasks.find(x=>x.key==='manager_preparation').id;
      await card.getByRole('button',{name:'Complete preparation'}).click();
      await card.getByLabel('First-week plan').fill('Prepare orientation schedule and first-week deliverables.');
      await card.getByLabel("Buddy's name").fill('Synthetic Buddy');
      await card.getByLabel('Workstation is ready').check();
      await card.getByLabel('Attestation note').fill('Synthetic manager readiness confirmed.');
      await card.getByRole('button',{name:'Submit recorded evidence'}).click();
      await expect(taskCard(manager,'Manager Preparation')).toContainText('COMPLETED');
      await expect(manager.getByText('1/17 mandatory tasks completed')).toBeVisible();
      await expect(taskCard(manager,'Team Introduction')).not.toContainText('PREREQUISITE_INCOMPLETE');
      await expect(taskCard(manager,'Workspace Access')).toContainText('PREREQUISITE_INCOMPLETE');
      await manager.getByText('Evaluation limits',{exact:true}).click();
      await expect(manager.getByText(/secure PDF intake, external AI and automatic background reminders/)).toBeVisible();
      await expect(taskCard(manager,'Manager Preparation').getByRole('button',{name:'Complete preparation'})).toHaveCount(0);
    });

    await test.step('IT has owned work, cannot complete manager evidence, CSRF is enforced',async()=>{
      await it.reload();
      await expect(it.getByRole('button',{name:'Cases (1)'})).toBeVisible();
      await it.getByRole('button',{name:/^My work \(/}).click();
      await expect(it.getByText(/No tasks currently need your action/)).toBeVisible();
      const blockedWork=(await (await it.request.get('/api/v1/cases/'+caseId+'/tasks')).json()).tasks;
      expect(blockedWork.find(t=>t.key==='equipment_setup').state).toBe('BLOCKED');
      expect(blockedWork.find(t=>t.key==='workspace_access').state).toBe('BLOCKED');
      await openCase(it);
      await expect(taskCard(it,'Manager Preparation').getByRole('button',{name:'Complete preparation'})).toHaveCount(0);
      await expect(taskCard(it,'Workspace Access')).toContainText('PREREQUISITE_INCOMPLETE');
      const csrfDenied=await it.request.post('/api/v1/cases/'+caseId+'/tasks/'+managerTaskId+'/attest-manager',
        {data:{prepared_fields:{first_week_plan:'Unauthorized work',buddy_name:'Bad actor',workstation_ready:true},note:'Nope'}});
      expect(csrfDenied.status()).toBe(403);
      const token=(await (await it.request.get('/api/v1/auth/csrf')).json()).csrf_token;
      const forbidden=await it.request.post('/api/v1/cases/'+caseId+'/tasks/'+managerTaskId+'/attest-manager',
        {headers:{'X-CSRFToken':token,'Idempotency-Key':'00000000-0000-4000-8000-000000000010',
          'If-Match':'"case:'+caseId+':v3"'},data:{
            prepared_fields:{first_week_plan:'Unauthorized work',buddy_name:'Bad actor',workstation_ready:true},note:'Nope'}});
      expect(forbidden.status()).toBe(404);
      await expect(it.getByRole('region',{name:'Case tasks'})).toContainText('1/17 mandatory tasks completed');
    });

    await test.step('Employee sees assigned tasks but cannot manage template or manager evidence',async()=>{
      await login(employee,'EMPLOYEE');
      await expect(employee.getByRole('button',{name:'Cases (1)'})).toBeVisible();
      await expect(employee.getByRole('button',{name:/^My work \(/})).toBeVisible();
      await employee.getByRole('button',{name:/^My work \(/}).click();
      await expect(employee.getByText('Identity Document')).toBeVisible();
      await expect(employee.getByRole('button',{name:/Templates \(/})).toHaveCount(0);
      await openCase(employee);
      await expect(taskCard(employee,'Manager Preparation').getByRole('button',{name:'Complete preparation'})).toHaveCount(0);
      await expect(employee.getByRole('region',{name:'Case tasks'})).toContainText('1/17 mandatory tasks completed');
      expect((await employee.request.get('/api/v1/templates')).status()).toBe(403);
    });

    await test.step('Employee form revision and independent HR acceptance truly complete a task',async()=>{
      const formCard=taskCard(employee,'Personal Details');
      await formCard.getByLabel('Preferred name').fill('Synthetic Candidate');
      await formCard.getByLabel('Contact email').fill('candidate@example.test');
      await formCard.getByRole('button',{name:'Submit immutable form revision'}).click();
      await expect(formCard).toContainText('Pending HR review');
      await expect(employee.getByText('1/17 mandatory tasks completed')).toBeVisible();

      await openCase(hr);
      const hrForm=taskCard(hr,'Personal Details');
      await hrForm.getByRole('button',{name:'Load form history'}).click();
      await expect(hrForm).toContainText('Pending HR review');
      await hrForm.getByLabel('HR review note').fill('Synthetic form reviewed and accepted.');
      // Verified HR acceptance removes this card from focused work.
      // Assert the server decision and the UI's completed-history presentation.
      const [formApproval]=await Promise.all([
        hr.waitForResponse(response=>response.url().includes('/form-submissions/')&&
          response.url().endsWith('/review')&&response.request().method()==='POST'),
        hrForm.getByRole('button',{name:'Accept revision and complete task'}).click(),
      ]);
      const approvalResult=await formApproval.json();
      expect(formApproval.status(),
        'FORM_HR_APPROVAL_HTTP_'+formApproval.status()+
        ': '+(approvalResult?.error?.code||'NO_ERROR_CODE')).toBe(201);
      expect(approvalResult.result?.decision).toBe('ACCEPTED');
      expect(approvalResult.result?.task_completion).toBe('COMPLETED');
      await expect.poll(async()=>{
        const response=await hr.request.get('/api/v1/cases/'+caseId+'/tasks');
        expect(response.status()).toBe(200);
        const current=await response.json();
        return current.tasks.find(t=>t.key==='personal_details')?.state;
      },{timeout:12000}).toBe('COMPLETED');
      await expect(hr.getByText('2/17 mandatory tasks completed')).toBeVisible();

      // Default focuses on actionable work; future blocked steps are absent.
      const focus=hr.getByRole('button',{name:'Return to focused work'});
      if(await focus.isVisible())await focus.click();
      const caseView=hr.getByRole('region',{name:'Case tasks'});
      const completed=caseView.locator('details[aria-label="Completed onboarding steps"]');
      await expect(completed.locator('summary').first()).toHaveText('Completed steps (2)');
      await expect(caseView.locator('article.task').filter({
        has:caseView.getByRole('heading',{name:'Workspace Access',exact:true}),
      })).toHaveCount(0);
      await completed.locator('summary').first().click();
      const personal=completed.locator('article.task').filter({
        hasText:'Personal Details',
      });
      await expect(personal).toContainText('COMPLETED');
      await personal.getByText('Review completed evidence',{exact:true}).click();
      await personal.getByRole('button',{name:'Load form history'}).click();
      await expect(personal).toContainText('Revision 1: ACCEPTED');

      // An explicitly opened full plan still provides prerequisite visibility.
      await hr.getByRole('button',{name:'View all steps (advanced)'}).click();
      await expect(taskCard(hr,'Personal Details')).toContainText('COMPLETED');
      await expect(taskCard(hr,'Workspace Access')).toContainText('PREREQUISITE_INCOMPLETE');
      await hr.reload();
      await expect(hr.getByText('Role: HR')).toBeVisible();
      await openCase(hr);
      await expect(taskCard(hr,'Personal Details')).toContainText('COMPLETED');
    });

    await test.step('M4 IT action stays blocked until the required identity-document evidence',async()=>{
      // Default M2 template requires BOTH identity_document and personal_details
      // before EQUIPMENT. M3 form acceptance alone cannot unlock IT work.
      await it.reload();
      await expect(it.getByText('Role: IT')).toBeVisible();
      await openCase(it);
      const equipment=taskCard(it,'Equipment Setup');
      await expect(equipment).toContainText('BLOCKED');
      await expect(equipment).toContainText('PREREQUISITE_INCOMPLETE');
      await expect(equipment.getByRole('button',{name:'Create synthetic IT request'})).toHaveCount(0);
      await expect(equipment.getByRole('button',{name:'Confirm simulated IT outcome and complete task'})).toHaveCount(0);
    });

    await test.step('employee acknowledges only the exact frozen synthetic policy edition',async()=>{
      await openCase(employee);
      const card=taskCard(employee,'Conduct Ack');
      await expect(card).toContainText('READY');
      await card.getByRole('button',{name:'View assigned policy'}).click();
      await expect(card.getByText('Assigned edition: synthetic-conduct-v1')).toBeVisible();
      await expect(card).toContainText('not an employment agreement');
      await card.getByLabel(/I have read and explicitly acknowledge/).check();
      await card.getByRole('button',{name:'Record version-specific acknowledgement'}).click();
      await expect(taskCard(employee,'Conduct Ack')).toContainText('COMPLETED');
      await expect(employee.getByText('3/17 mandatory tasks completed')).toBeVisible();
      await expect(taskCard(employee,'Workspace Access')).toContainText('PREREQUISITE_INCOMPLETE');
    });

    await test.step('M3 employee document rejection, revision and HR acceptance unlock M4 equipment',async()=>{
      await openCase(employee);
      const document=taskCard(employee,'Identity Document');
      await expect(document).toContainText('READY');
      const fixture=Buffer.from([
        'SYNTHETIC DOCUMENT V1',
        'IDENTITY EXAMPLE: DEMO-IDENTITY-001',
        'NO REAL PERSON OR IDENTITY DATA',
        ''
      ].join(String.fromCharCode(10)),'utf8');
      await document.locator('input[type="file"]').setInputFiles({
        name:'synthetic_identity.txt',mimeType:'text/plain',buffer:fixture});
      await document.getByRole('button',{name:'Upload synthetic document'}).click();
      await expect(taskCard(employee,'Identity Document')).toContainText('Pending HR review');
      await expect(employee.getByText('3/17 mandatory tasks completed')).toBeVisible();

      await openCase(hr);
      let hrDoc=taskCard(hr,'Identity Document');
      await hrDoc.getByRole('button',{name:'Load document history'}).click();
      await hrDoc.getByLabel('HR decision').selectOption('REJECTED');
      await hrDoc.getByLabel('Reason / review evidence').fill('Please submit a replacement demo fixture');
      await hrDoc.getByRole('button',{name:'Record independent HR document decision'}).click();
      await expect(hrDoc).toContainText('REJECTED');
      await expect(taskCard(hr,'Equipment Setup')).toContainText('PREREQUISITE_INCOMPLETE');

      await openCase(employee);
      const doc2=taskCard(employee,'Identity Document');
      await doc2.getByRole('button',{name:'Load document history'}).click();
      await doc2.locator('input[type="file"]').setInputFiles({
        name:'synthetic_identity.txt',mimeType:'text/plain',buffer:fixture});
      await doc2.getByRole('button',{name:'Upload synthetic document'}).click();
      await expect(doc2).toContainText('Revision 2');

      await openCase(hr);
      hrDoc=taskCard(hr,'Identity Document');
      await hrDoc.getByRole('button',{name:'Load document history'}).click();
      await hrDoc.getByLabel('HR decision').selectOption('ACCEPTED');
      await hrDoc.getByLabel('Reason / review evidence').fill('Approved exact synthetic demo fixture');
      await hrDoc.getByRole('button',{name:'Record independent HR document decision'}).click();
      await expect(taskCard(hr,'Identity Document')).toContainText('COMPLETED');
      await expect(hr.getByText('4/17 mandatory tasks completed')).toBeVisible();
      await expect(taskCard(hr,'Equipment Setup')).toContainText('READY');
    });

    await test.step('IT simulation failure, explicit retry and human signoff unlock equipment',async()=>{
      await openCase(it);
      let equipment=taskCard(it,'Equipment Setup');
      await expect(equipment).toContainText('READY');
      await equipment.getByRole('button',{name:'Create synthetic IT request'}).click();
      await expect(taskCard(it,'Equipment Setup')).toContainText('IN_PROGRESS');
      equipment=taskCard(it,'Equipment Setup');
      await equipment.getByRole('button',{name:'Inspect IT operation'}).click();
      await expect(equipment).toContainText('REQUESTED');
      await equipment.getByLabel('Simulated failure cause').selectOption('SIMULATED_TIMEOUT');
      await equipment.getByLabel('Simulated failure note').fill('Synthetic provider timeout requires an explicit retry');
      await equipment.getByRole('button',{name:'Record synthetic failure (task remains pending)'}).click();
      await expect(equipment).toContainText('Failure 1: SIMULATED_TIMEOUT');
      await expect(it.getByText('4/17 mandatory tasks completed')).toBeVisible();
      await equipment.getByLabel('Simulation note').fill('Synthetic provider recovered on explicit retry');
      await equipment.getByRole('button',{name:'Retry with simulated fulfillment'}).click();
      await expect(equipment).toContainText('SIMULATED_FULFILLED');
      await expect(it.getByText('4/17 mandatory tasks completed')).toBeVisible();
      await equipment.getByLabel('IT confirmation note').fill(
        'Assigned IT owner separately verified the synthetic outcome');
      await equipment.getByRole('button',{name:'Confirm simulated IT outcome and complete task'}).click();
      await expect(taskCard(it,'Equipment Setup')).toContainText('COMPLETED');
      await expect(it.getByText('5/17 mandatory tasks completed')).toBeVisible();
      await it.reload();
      await expect(it.getByText('Role: IT')).toBeVisible();
      await openCase(it);
      await expect(taskCard(it,'Equipment Setup')).toContainText('COMPLETED');
    });

    await test.step('same-mounted-page identity switch clears HR template and pending reads',async()=>{
      // Keep the page mounted: no reload, new browser context, or remount.
      await hr.getByRole('button',{name:/Templates \(/}).click();
      const item=hr.locator('.case-list').first().getByRole('button').first();
      await expect(item).toBeVisible();
      await item.click();
      await expect(hr.getByRole('heading',{name:/Employee First Month.*PUBLISHED/})).toBeVisible();
      await hr.getByRole('button',{name:'Create next version draft'}).click();
      await hr.getByText('Edit task JSON (advanced)',{exact:true}).click();
      await expect(hr.locator('textarea.json-editor')).toBeVisible();
      await hr.locator('textarea.json-editor').fill('OLD_HR_PRIVATE_DRAFT_CONTENT');
      // Clone's own refresh must finish BEFORE installing the held-response
      // interceptor; otherwise it holds busy=true and disables Sign out.
      await expect(hr.getByRole('button',{name:'Sign out'})).toBeEnabled();

      // An in-flight HR-owned request must be discarded after login changes.
      let releaseResponse;
      let intercepted;
      const held=new Promise(resolve=>{intercepted=resolve;});
      const release=new Promise(resolve=>{releaseResponse=resolve;});
      let markSettled;
      const settled=new Promise(resolve=>{markSettled=resolve;});
      await hr.route('**/api/v1/templates',async route=>{
        intercepted();
        await release;
        try{
          await route.continue();
        }catch(error){
          // A request cancelled during logout may be handled by Chromium.
          // Other route errors still fail this acceptance test.
          if(!String(error).includes('Route is already handled') &&
             !String(error).includes('Target closed'))throw error;
        }finally{
          markSettled();
        }
      });
      await hr.getByRole('button',{name:'Sign out'}).click();
      await expect(hr.getByRole('heading',{name:'Sign in'})).toBeVisible();
      // Re-auth as HR, allowing its background refresh to stall on /templates.
      await login(hr,'HR');
      await held;
      await hr.getByRole('button',{name:'Sign out'}).click();
      await expect(hr.getByRole('heading',{name:'Sign in'})).toBeVisible();
      await login(hr,'IT');
      releaseResponse();
      await settled;
      await hr.unroute('**/api/v1/templates');
      await expect(hr.getByText('Role: IT')).toBeVisible();
      await expect(hr.getByText('OLD_HR_PRIVATE_DRAFT_CONTENT')).toHaveCount(0);
      await expect(hr.locator('textarea.json-editor')).toHaveCount(0);
      await expect(hr.getByRole('button',{name:/Templates \(/})).toHaveCount(0);
      await expect(hr.getByRole('button',{name:'Cases (1)'})).toBeVisible();
    });

    await test.step('sign out removes protected UI and rejects session reads',async()=>{
      for(const page of [it,manager,employee,hr]){
        await page.getByRole('button',{name:'Sign out'}).click();
        await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
        await expect(page.getByRole('navigation',{name:'Workspace'})).toHaveCount(0);
        const me=await page.request.get('/api/v1/auth/me');
        expect(me.status()).toBe(401);
      }
    });
  }finally{
    await Promise.allSettled([hrContext.close(),itContext.close(),managerContext.close(),employeeContext.close()]);
  }
});
