'use strict';
// Real Chromium + Deque axe-core automated WCAG A/AA scope.
// No remote scanner, no real employee data; not a substitute for human review.
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');
const credentialsFile=process.env.M2_BROWSER_CREDENTIAL_FILE;
if(!credentialsFile)throw Error('Missing isolated synthetic credential file');
const creds={};
for(const line of fs.readFileSync(credentialsFile,'utf8').split(/\r?\n/)){
  const match=line.trim().match(/^(HR|EMPLOYEE|IT|MANAGER)\s+(\S+)\s+(\S+)$/);
  if(match)creds[match[1]]={email:match[2],password:match[3]};
}
for(const role of ['HR','EMPLOYEE','IT','MANAGER']){
  if(!creds[role])throw Error('Missing synthetic '+role+' role');
}
const WCAG=['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa'];

async function scan(page,label){
  // Inject the version pinned by the test-only workflow, into our local browser.
  if(!await page.evaluate(()=>Boolean(window.axe))){
    await page.addScriptTag({path:require.resolve('axe-core')});
  }
  const result=await page.evaluate(async tags=>{
    const r=await window.axe.run(document,{runOnly:{type:'tag',values:tags}});
    return {
      violations:r.violations.map(v=>({id:v.id,impact:v.impact,description:v.help,
        targets:v.nodes.slice(0,5).map(n=>n.target.join(' ')),
        nodes:v.nodes.length})),
      incomplete:r.incomplete.map(v=>({id:v.id,nodes:v.nodes.length})),
      passes:r.passes.length
    };
  },WCAG);
  // Preserve only selectors and rule identifiers in CI logs; do not log text
  // captured from document nodes, passwords or embedded policy answers.
  console.log('D5_AXE_AA_CHECK',label,'passes',result.passes,
    'incomplete',result.incomplete.length,'violations',result.violations.length);
  expect(result.violations,label+': '+JSON.stringify(result.violations)).toEqual([]);
}

async function login(page,role){
  await page.goto('/');
  await page.getByLabel('Email').fill(creds[role].email);
  await page.getByLabel('Password').fill(creds[role].password);
  const submit=page.getByRole('button',{name:'Sign in'});
  await expect(submit).toBeEnabled();
  const [res]=await Promise.all([
    page.waitForResponse(r=>r.url().endsWith('/api/v1/auth/login')&&
      r.request().method()==='POST'),submit.click()
  ]);
  expect(res.status(),'Real '+role+' HTTP authentication').toBe(200);
  await expect(page.getByText('Role: '+role)).toBeVisible();
}

test('D5 axe: logged-out form and real HR workspace across four responsive widths',async({page})=>{
  test.setTimeout(120000);
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
  await scan(page,'public sign-in');
  await login(page,'HR');
  for(const width of [320,375,768,1440]){
    await page.setViewportSize({width,height:850});
    await scan(page,'HR assigned cases '+width+'px');
  }
  const nav=page.getByRole('navigation',{name:'Workspace'});
  for(const [button,heading] of [
    ['My work','My assigned tasks'],
    ['In-app inbox','Reminders and handoffs'],
    ['Templates','Versioned templates'],
    ['HR portfolio','My assigned onboarding cases']
  ]){
    await nav.getByRole('button',{name:new RegExp('^'+button)}).click();
    await expect(page.getByRole('heading',{name:heading})).toBeVisible();
    await scan(page,'HR '+button);
  }
});

test('D5 axe: HR creates a real synthetic case; all four roles view authorized case',async({browser})=>{
  test.setTimeout(200000);
  const contexts=[];
  try{
    const hrCtx=await browser.newContext({viewport:{width:375,height:820}});
    contexts.push(hrCtx);
    const hr=await hrCtx.newPage();
    await login(hr,'HR');
    const nav=hr.getByRole('navigation',{name:'Workspace'});
    await nav.getByRole('button',{name:/^Templates \(/}).click();
    await hr.getByRole('button',{name:'Create default synthetic 17-task template'}).click();
    await expect(hr.getByRole('button',{name:'Validate and publish'})).toBeVisible();
    await hr.getByRole('button',{name:'Validate and publish'}).click();
    await expect(hr.getByRole('heading',{name:/Employee First Month.*PUBLISHED/})).toBeVisible();
    await nav.getByRole('button',{name:/^Cases \(/}).click();
    const form=hr.locator('section.panel')
      .filter({has:hr.getByRole('heading',{name:'Create an onboarding case'})});
    await expect(form).toBeVisible();
    for(let i=0;i<4;i++)await form.locator('select').nth(i).selectOption({index:1});
    await form.getByLabel('Joining date').fill(
      new Date(Date.now()+21*86400000).toISOString().slice(0,10));
    const [created]=await Promise.all([
      hr.waitForResponse(r=>r.url().endsWith('/api/v1/cases')&&r.request().method()==='POST'),
      form.getByRole('button',{name:'Create case'}).click(),
    ]);
    expect(created.status()).toBe(201);
    await expect(hr.locator('.case-list').first().getByRole('button').first()).toBeVisible();
    await scan(hr,'HR with persisted case');
    await hr.locator('.case-list').first().getByRole('button').first().click();
    await expect(hr.getByRole('region',{name:'Case tasks'})).toBeVisible();
    await hr.getByRole('button',{name:'Activate case'}).click();
    await expect(hr.getByRole('region',{name:'Case tasks'})).toBeVisible();
    await scan(hr,'HR case tasks before expanded plan');
    const full=hr.getByRole('button',{name:'View all steps (advanced)'});
    if(await full.isVisible())await full.click();
    await scan(hr,'HR expanded 17-task plan');

    for(const role of ['EMPLOYEE','IT','MANAGER']){
      const ctx=await browser.newContext({viewport:{width:375,height:820}});
      contexts.push(ctx);
      const page=await ctx.newPage();
      await login(page,role);
      await scan(page,role+' workspace');
      const cases=page.locator('.case-list').first().getByRole('button');
      await expect(cases.first()).toBeVisible();
      await cases.first().click();
      await expect(page.getByRole('region',{name:'Case tasks'})).toBeVisible();
      await scan(page,role+' case task view');
    }
  }finally{
    await Promise.allSettled(contexts.map(x=>x.close()));
  }
});
