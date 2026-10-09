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
  await expect(page.getByRole('status')).not.toContainText('Unable to read workspace');
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
      await expect(manager.getByText(/Document, policy, training and activity completion require separate evidence/)).toBeVisible();
      await expect(taskCard(manager,'Manager Preparation').getByRole('button',{name:'Complete preparation'})).toHaveCount(0);
    });

    await test.step('IT has owned work, cannot complete manager evidence, CSRF is enforced',async()=>{
      await it.reload();
      await expect(it.getByRole('button',{name:'Cases (1)'})).toBeVisible();
      await it.getByRole('button',{name:/^My work \(/}).click();
      await expect(it.getByText('Equipment Setup')).toBeVisible();
      await expect(it.getByText('Workspace Access')).toBeVisible();
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
      await hrForm.getByRole('button',{name:'Accept revision and complete task'}).click();
      await expect(taskCard(hr,'Personal Details')).toContainText('COMPLETED');
      await expect(hr.getByText('2/17 mandatory tasks completed')).toBeVisible();
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

    await test.step('same-mounted-page identity switch clears HR template and pending reads',async()=>{
      // Keep the page mounted: no reload, new browser context, or remount.
      await hr.getByRole('button',{name:/Templates \(/}).click();
      const item=hr.locator('.case-list').first().getByRole('button').first();
      await expect(item).toBeVisible();
      await item.click();
      await expect(hr.getByRole('heading',{name:/Employee First Month.*PUBLISHED/})).toBeVisible();
      await hr.getByRole('button',{name:'Create next version draft'}).click();
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
