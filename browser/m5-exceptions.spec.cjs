'use strict';
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');
const file=process.env.M5_BROWSER_CREDENTIAL_FILE;
if(!file)throw Error('M5 isolated browser fixture is required');
const users={};
let caseId;
for(const line of fs.readFileSync(file,'utf8').split(/\r?\n/)){
  const c=line.match(/^CASE\s+([\da-f-]{36})$/);
  const u=line.match(/^(HR|EMPLOYEE|IT|MANAGER)\s+(\S+)\s+(\S+)$/);
  if(c)caseId=c[1];
  if(u)users[u[1]]={email:u[2],password:u[3]};
}
if(!caseId||!users.HR||!users.MANAGER)throw Error('Missing real M5 browser identities');
async function login(page,role){
  await page.goto('/');
  await page.getByLabel('Email').fill(users[role].email);
  await page.getByLabel('Password').fill(users[role].password);
  await page.getByRole('button',{name:'Sign in'}).click();
  await expect(page.getByText('Role: '+role)).toBeVisible();
}
async function openCase(page){
  await page.getByRole('button',{name:/^Cases \(/}).click();
  await page.locator('.case-list').first().getByRole('button').first().click();
  await expect(page.getByRole('region',{name:'Case tasks'})).toBeVisible();
}
const panel=page=>page.getByRole('region',{name:'Case exceptions'});
const card=(page,title)=>page.getByRole('region',{name:'Case tasks'})
  .locator('article.task').filter({has:page.getByRole('heading',{name:title,exact:true})});

test('M5 full Chromium exception opens, refuses bypass, typed manager evidence, HR closure',async({browser})=>{
  test.setTimeout(180000);
  const managerContext=await browser.newContext();
  const hrContext=await browser.newContext();
  const manager=await managerContext.newPage(),hr=await hrContext.newPage();
  try{
    await login(manager,'MANAGER');await openCase(manager);
    await expect(card(manager,'M5 Team Introduction')).toContainText('BLOCKED');
    const exceptions=panel(manager);
    await exceptions.getByRole('button',{name:'Load current exceptions'}).click();
    await exceptions.getByRole('combobox',{name:'Exception task'}).selectOption({label:'M5 Team Introduction'});
    await exceptions.getByLabel('Blocking condition').selectOption('PREREQUISITE_BLOCKED');
    await exceptions.getByLabel('Reason (8–240 characters)').fill('Manager preparation still requires verified evidence');
    await exceptions.getByRole('button',{name:'Open exception with current-state verification'}).click();
    await expect(exceptions).toContainText('PREREQUISITE_BLOCKED');
    await expect(exceptions).toContainText('Episode 1');
    await expect(exceptions).toContainText('OPEN');

    await login(hr,'HR');await openCase(hr);
    const hrEx=panel(hr);
    await hrEx.getByRole('button',{name:'Load current exceptions'}).click();
    await expect(hrEx).toContainText('Episode 1');
    await hrEx.getByLabel('Assign owner').selectOption('MANAGER');
    await hrEx.getByRole('button',{name:'Assign',exact:true}).click();
    await expect(hrEx).toContainText('ASSIGNED');

    await manager.reload();
    await expect(manager.getByText('Role: MANAGER')).toBeVisible();
    await openCase(manager);
    await panel(manager).getByRole('button',{name:'Load current exceptions'}).click();
    await expect(panel(manager).getByRole('button',{name:'Resolve after correction'})).toBeDisabled();
    await expect(card(manager,'M5 Team Introduction')).toContainText('BLOCKED');

    const prepare=card(manager,'M5 Manager Preparation');
    await prepare.getByRole('button',{name:'Complete preparation'}).click();
    await prepare.getByLabel('First-week plan').fill('Synthetic first-week plan verified in browser');
    await prepare.getByLabel("Buddy's name").fill('Synthetic Buddy');
    await prepare.getByLabel('Workstation is ready').check();
    await prepare.getByLabel('Attestation note').fill('Manager personally verified synthetic preparation');
    await prepare.getByRole('button',{name:'Submit recorded evidence'}).click();
    await expect(card(manager,'M5 Manager Preparation')).toContainText('COMPLETED');
    await expect(card(manager,'M5 Team Introduction')).toContainText('READY');
    await panel(manager).getByRole('button',{name:'Load current exceptions'}).click();
    await expect(panel(manager)).toContainText('Underlying condition cleared');
    await panel(manager).getByRole('button',{name:'Resolve after correction'}).click();
    await expect(panel(manager)).toContainText('RESOLVED');

    await hr.reload();
    await expect(hr.getByText('Role: HR')).toBeVisible();
    await openCase(hr);
    await panel(hr).getByRole('button',{name:'Load current exceptions'}).click();
    await expect(panel(hr).getByRole('button',{name:'Close verified exception'})).toBeEnabled();
    await panel(hr).getByRole('button',{name:'Close verified exception'}).click();
    await expect(panel(hr)).toContainText('CLOSED');
    await expect(panel(hr)).toContainText('Audited exception history (4 transitions)');

    await hr.reload();
    await expect(hr.getByText('Role: HR')).toBeVisible();
    await openCase(hr);
    await panel(hr).getByRole('button',{name:'Load current exceptions'}).click();
    await expect(panel(hr)).toContainText('CLOSED');
    await expect(card(hr,'M5 Team Introduction')).toContainText('READY');
    // Read-only deterministic guidance has no model or hidden task completion.
    const guide=hr.getByRole('region',{name:'Case companion guidance'});
    await guide.getByRole('button',{name:'Analyze current case'}).click();
    await expect(guide).toContainText('no AI model call');
    await expect(guide).toContainText('No current exception episodes');
    await expect(card(hr,'M5 Team Introduction')).not.toContainText('COMPLETED');
  }finally{
    await Promise.allSettled([managerContext.close(),hrContext.close()]);
  }
});


test('M5 Chromium HR previews joining date, commits and preserves existing manager evidence',async({browser})=>{
  test.setTimeout(120000);
  const context=await browser.newContext();
  const hr=await context.newPage();
  try{
    await login(hr,'HR');await openCase(hr);
    const casePanel=hr.getByRole('region',{name:'Case tasks'});
    const datePanel=casePanel.getByRole('region',{name:'Joining date reschedule'});
    await expect(card(hr,'M5 Manager Preparation')).toContainText('COMPLETED');
    const preservedBefore=await card(hr,'M5 Manager Preparation').innerText();
    const introBefore=await card(hr,'M5 Team Introduction').innerText();
    const target=new Date(Date.now()+9*86400*1000).toISOString().slice(0,10);
    await datePanel.getByLabel('Proposed joining date').fill(target);
    await datePanel.getByRole('button',{name:'Preview date change impact'}).click();
    await expect(datePanel).toContainText('1 untouched task(s) move');
    await expect(datePanel).toContainText('1 started/completed task(s) stay unchanged');
    await datePanel.getByLabel('Joining date change reason').fill(
      'HR confirmed synthetic updated joining date with employee');
    await datePanel.getByRole('button',{name:'Approve and commit previewed date change'}).click();
    await expect(datePanel).toContainText('Current joining date: '+target);
    await expect(card(hr,'M5 Manager Preparation')).toContainText('COMPLETED');
    await expect(card(hr,'M5 Team Introduction')).toContainText('NOT_STARTED');
    const introAfter=await card(hr,'M5 Team Introduction').innerText();
    expect(introAfter).not.toBe(introBefore);
    expect(await card(hr,'M5 Manager Preparation').innerText()).toBe(preservedBefore);
    await hr.reload();
    await expect(hr.getByText('Role: HR')).toBeVisible();
    await openCase(hr);
    await expect(hr.getByRole('region',{name:'Joining date reschedule'}))
      .toContainText('Current joining date: '+target);
    await expect(card(hr,'M5 Manager Preparation')).toContainText('COMPLETED');
    await expect(card(hr,'M5 Team Introduction')).toContainText('NOT_STARTED');
  }finally{await context.close();}
});
