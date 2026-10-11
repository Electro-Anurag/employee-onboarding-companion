'use strict';
// Targeted reproduction of T02, not a replacement for four-role acceptance.
// Runs on a disposable PostgreSQL database and synthetic accounts only.
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');

const credentialsPath=process.env.M2_BROWSER_CREDENTIAL_FILE;
if(!credentialsPath)throw Error('Synthetic credential file required');
const credentials={};
for(const line of fs.readFileSync(credentialsPath,'utf8').split(/\r?\n/)){
  const match=line.match(/^(HR|EMPLOYEE)\s+(\S+)\s+(\S+)$/);
  if(match)credentials[match[1]]={email:match[2],password:match[3]};
}
if(!credentials.HR||!credentials.EMPLOYEE)
  throw Error('Missing one of two synthetic test roles');

async function login(page,role){
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
  await page.getByLabel('Email').fill(credentials[role].email);
  await page.getByLabel('Password').fill(credentials[role].password);
  await page.getByRole('button',{name:'Sign in'}).click();
  await expect(page.getByText('Role: '+role)).toBeVisible();
}

function card(page){
  return page.getByRole('region',{name:'Case tasks'}).locator('article.task')
    .filter({has:page.getByRole('heading',{name:'Conduct Ack',exact:true})});
}

async function selectCaseWithAllTasks(page){
  await expect(page.getByRole('button',{name:/^Cases \(/})).toBeVisible();
  await page.getByRole('button',{name:/^Cases \(/}).click();
  const list=page.locator('.case-list').first().getByRole('button');
  await expect(list.first()).toBeVisible();
  await list.first().click();
  const region=page.getByRole('region',{name:'Case tasks'});
  await expect(region).toBeVisible();
  const expand=region.getByRole('button',{name:'View all steps (advanced)'});
  if(await expand.isVisible())await expand.click();
  await expect(region.locator('article.task')).toHaveCount(17);
}

test('T02 focused: assigned policy read preserves Conduct Ack card and genuine acknowledgement',async({browser})=>{
  test.setTimeout(115000);
  const hrCtx=await browser.newContext();
  const employeeCtx=await browser.newContext();
  const hr=await hrCtx.newPage();
  const employee=await employeeCtx.newPage();
  const browserErrors=[];
  employee.on('pageerror',error=>browserErrors.push('PAGE:'+error.message.slice(0,300)));
  employee.on('console',message=>{
    if(message.type()==='error')
      browserErrors.push('CONSOLE:'+message.text().slice(0,300));
  });
  let caseId=null;
  try{
    await test.step('create/activate genuine synthetic onboarding case',async()=>{
      await login(hr,'HR');
      await hr.getByRole('button',{name:/Templates \(/}).click();
      await hr.getByRole('button',{name:'Create default synthetic 17-task template'}).click();
      await expect(hr.getByRole('heading',{name:/Employee First Month.*DRAFT/})).toBeVisible();
      await hr.getByRole('button',{name:'Validate and publish'}).click();
      await expect(hr.getByRole('heading',{name:/Employee First Month.*PUBLISHED/})).toBeVisible();
      await hr.getByRole('button',{name:/^Cases \(/}).click();
      const form=hr.locator('section.panel')
        .filter({has:hr.getByRole('heading',{name:'Create an onboarding case'})});
      await expect(form).toBeVisible();
      for(let i=0;i<4;i++)await form.locator('select').nth(i).selectOption({index:1});
      const join=new Date(Date.now()+21*86400000).toISOString().slice(0,10);
      await form.getByLabel('Joining date').fill(join);
      const [created]=await Promise.all([
        hr.waitForResponse(r=>r.url().endsWith('/api/v1/cases')&&
          r.request().method()==='POST'),
        form.getByRole('button',{name:'Create case'}).click(),
      ]);
      expect(created.status()).toBe(201);
      caseId=(await created.json()).case_id;
      expect(caseId).toMatch(/^[0-9a-f-]{36}$/);
      await selectCaseWithAllTasks(hr).catch(async error=>{
        // Created cases have no instantiated tasks until activation.
        if(!String(error).includes('toHaveCount'))throw error;
      });
      const region=hr.getByRole('region',{name:'Case tasks'});
      await expect(region.getByRole('button',{name:'Activate case'})).toBeVisible();
      await region.getByRole('button',{name:'Activate case'}).click();
      await expect(hr.getByRole('region',{name:'Case tasks'})).toContainText('0/17 mandatory tasks completed');
    });
    await test.step('employee reads exact frozen policy without losing the card',async()=>{
      await login(employee,'EMPLOYEE');
      await selectCaseWithAllTasks(employee);
      const conduct=card(employee);
      await expect(conduct).toHaveCount(1);
      await expect(conduct).toContainText('READY');
      const [read]=await Promise.all([
        employee.waitForResponse(r=>r.url().includes('/assigned-policy')&&
          r.request().method()==='GET'),
        conduct.getByRole('button',{name:'View assigned policy'}).click(),
      ]);
      const policy=await read.json();
      expect(read.status()).toBe(200);
      expect(policy.policy?.version).toBe('synthetic-conduct-v1');
      expect(policy.policy?.text).toContain('not an employment agreement');
      try{
        // Never weaken this assertion: a good GET cannot substitute for UI.
        await expect(conduct).toHaveCount(1);
        await expect(conduct.getByText('Assigned edition: synthetic-conduct-v1'))
          .toBeVisible();
      }catch(error){
        const region=employee.getByRole('region',{name:'Case tasks'});
        const state={
          // No passwords, emails, questions, identity data or document bytes.
          case_id:caseId,caseTasksVisible:await region.isVisible().catch(()=>false),
          page:employee.url(),
          cardCount:await conduct.count().catch(()=>-1),
          allTaskCount:await region.locator('article.task').count().catch(()=>-1),
          focusedVisible:await region.getByRole('button',{name:'View all steps (advanced)'})
            .isVisible().catch(()=>false),
          headings:(await region.locator('article.task h4').allTextContents().catch(()=>[])).slice(0,20),
          alerts:(await employee.getByRole('alert').allTextContents().catch(()=>[])).slice(0,8),
          errors:browserErrors.slice(0,8),
        };
        throw Error('POLICY_FOCUSED_CARD_DISAPPEARANCE '+JSON.stringify(state)+
          '; original='+String(error));
      }
      await expect(conduct).toContainText('not an employment agreement');
    });
    await test.step('employee must explicitly acknowledge and persistence survives reload',async()=>{
      const conduct=card(employee);
      await conduct.getByLabel(/I have read and explicitly acknowledge/).check();
      await conduct.getByRole('button',{name:'Record version-specific acknowledgement'}).click();
      await expect(employee.getByText('1/17 mandatory tasks completed')).toBeVisible();
      await expect(card(employee)).toContainText('COMPLETED');
      await employee.reload();
      await expect(employee.getByText('Role: EMPLOYEE')).toBeVisible();
      await selectCaseWithAllTasks(employee);
      await expect(card(employee)).toContainText('COMPLETED');
      await card(employee).getByRole('button',{name:'View assigned policy'}).click();
      await expect(card(employee)).toContainText('Acknowledged and stored as immutable evidence');
      await expect(card(employee).getByRole('button',{
        name:'Record version-specific acknowledgement'})).toHaveCount(0);
    });
  }finally{
    await employeeCtx.close();
    await hrCtx.close();
  }
});