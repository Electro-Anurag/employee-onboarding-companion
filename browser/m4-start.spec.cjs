'use strict';
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');
const path=process.env.M4_START_BROWSER_CREDENTIAL_FILE;
if(!path)throw Error('Missing isolated M4 Start browser fixture');
const users={},lines=fs.readFileSync(path,'utf8').split(/\r?\n/);
let caseId;
for(const line of lines){
  const match=line.match(/^(HR|EMPLOYEE|IT|MANAGER)\s+(\S+)\s+(\S+)$/);
  if(match)users[match[1]]={email:match[2],password:match[3]};
  const c=line.match(/^CASE\s+([\da-f-]{36})$/);
  if(c)caseId=c[1];
}
if(!caseId||['HR','EMPLOYEE','IT','MANAGER'].some(role=>!users[role]))
  throw Error('Incomplete Start browser credentials');
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
function card(page,title){
  return page.getByRole('region',{name:'Case tasks'}).locator('article.task')
    .filter({has:page.getByRole('heading',{name:title,exact:true})});
}
function localSlot(delta){
  return new Date(Date.now()+delta*60000).toISOString().slice(0,16);
}

test('R1: actual Chromium generic Start keeps all six typed M4 actions reachable',async({browser})=>{
  test.setTimeout(230000);
  const contexts=await Promise.all(Array.from({length:4},()=>browser.newContext()));
  const [it,employee,hr,manager]=await Promise.all(contexts.map(c=>c.newPage()));
  try{
    await login(it,'IT');await openCase(it);
    await test.step('ACCESS: Start, IT request, synthetic failure/retry and separate confirmation',async()=>{
      let access=card(it,'Start Access');
      await expect(access).toContainText('READY');
      await access.getByRole('button',{name:'Start',exact:true}).click();
      await expect(access).toContainText('IN_PROGRESS');
      await it.reload();await expect(it.getByText('Role: IT')).toBeVisible();await openCase(it);
      access=card(it,'Start Access');
      await expect(access.getByRole('button',{name:'Create synthetic IT request'})).toBeVisible();
      await access.getByRole('button',{name:'Create synthetic IT request'}).click();
      await expect(access).toContainText('REQUESTED');
      await access.getByLabel('Simulated failure note').fill('Synthetic access timeout for Start regression');
      await access.getByRole('button',{name:'Record synthetic failure (task remains pending)'}).click();
      await expect(access).toContainText('Failure 1: SIMULATED_TIMEOUT');
      await access.getByLabel('Simulation note').fill('Synthetic access recovered after human retry');
      await access.getByRole('button',{name:'Retry with simulated fulfillment'}).click();
      await expect(access).toContainText('SIMULATED_FULFILLED');
      await access.getByLabel('IT confirmation note').fill('IT explicitly verified synthetic access');
      await access.getByRole('button',{name:'Confirm simulated IT outcome and complete task'}).click();
      await expect(access).toContainText('COMPLETED');
      await expect(access.getByRole('button',{name:'Create synthetic IT request'})).toHaveCount(0);
    });
    await test.step('EQUIPMENT: Start then confirmed synthetic operation',async()=>{
      let device=card(it,'Start Device');
      await expect(device).toContainText('READY');
      await device.getByRole('button',{name:'Start',exact:true}).click();
      await expect(device).toContainText('IN_PROGRESS');
      await device.getByRole('button',{name:'Create synthetic IT request'}).click();
      await expect(device).toContainText('REQUESTED');
      await device.getByLabel('Simulation note').fill('Synthetic equipment provider responded');
      await device.getByRole('button',{name:'Record simulated fulfillment'}).click();
      await device.getByLabel('IT confirmation note').fill('Human confirmed synthetic device fulfillment');
      await device.getByRole('button',{name:'Confirm simulated IT outcome and complete task'}).click();
      await expect(device).toContainText('COMPLETED');
    });
    await test.step('EMPLOYEE: already-started equipment receipt remains actionable after reload',async()=>{
      await login(employee,'EMPLOYEE');await openCase(employee);
      let receipt=card(employee,'Start Receipt');
      await expect(receipt).toContainText('READY');
      await receipt.getByRole('button',{name:'Start',exact:true}).click();
      await expect(receipt).toContainText('IN_PROGRESS');
      await employee.reload();await expect(employee.getByText('Role: EMPLOYEE')).toBeVisible();
      await openCase(employee);
      receipt=card(employee,'Start Receipt');
      await receipt.getByRole('button',{name:'Load confirmed equipment evidence'}).click();
      await expect(receipt).toContainText('1 confirmed equipment record(s)');
      await expect(receipt.getByRole('button',{name:'Acknowledge confirmed synthetic equipment'})).toBeVisible();
      await receipt.getByLabel('Receipt note').fill('Employee acknowledges synthetic device receipt');
      await receipt.getByRole('button',{name:'Acknowledge confirmed synthetic equipment'}).click();
      await expect(receipt).toContainText('COMPLETED');
      await expect(receipt.getByRole('button',{name:'Acknowledge confirmed synthetic equipment'})).toHaveCount(0);
    });
    await test.step('HR ACTIVITY: Start then normal browser scheduling',async()=>{
      await login(hr,'HR');await openCase(hr);
      let activity=card(hr,'Start Activity');
      await activity.getByRole('button',{name:'Start',exact:true}).click();
      await expect(activity).toContainText('IN_PROGRESS');
      await hr.reload();await expect(hr.getByText('Role: HR')).toBeVisible();
      await openCase(hr);
      activity=card(hr,'Start Activity');
      await activity.getByRole('button',{name:'Load activity schedule'}).click();
      await activity.getByLabel('Meeting start (local)').fill(localSlot(25));
      await activity.getByLabel('Meeting end (local)').fill(localSlot(45));
      await activity.getByLabel('Room or approved meeting reference').fill('Synthetic Start activity room');
      await activity.getByLabel('Scheduling/rescheduling reason').fill('Initial appointment after generic Start');
      await activity.getByRole('button',{name:'Schedule meeting occurrence'}).click();
      await expect(activity).toContainText('Revision 1:');
      await expect(activity).toContainText('IN_PROGRESS');
      await expect(activity.getByRole('button',{name:'Record organizer attendance'})).toHaveCount(0);
    });
    await test.step('MANAGER INTRODUCTION and CHECK_IN: Start then typed schedule',async()=>{
      await login(manager,'MANAGER');await openCase(manager);
      for(const [title,reference] of [
        ['Start Introduction','Synthetic team introduction'],
        ['Start Checkin','Synthetic manager checkin']]){
        let meeting=card(manager,title);
        await meeting.getByRole('button',{name:'Start',exact:true}).click();
        await expect(meeting).toContainText('IN_PROGRESS');
        await meeting.getByRole('button',{name:'Load activity schedule'}).click();
        await meeting.getByLabel('Meeting start (local)').fill(localSlot(30));
        await meeting.getByLabel('Meeting end (local)').fill(localSlot(50));
        await meeting.getByLabel('Room or approved meeting reference').fill(reference);
        await meeting.getByLabel('Scheduling/rescheduling reason').fill('Synthetic occurrence after generic task Start');
        await meeting.getByRole('button',{name:'Schedule meeting occurrence'}).click();
        await expect(meeting).toContainText('Revision 1:');
      }
      await expect(manager.getByText('3/6 mandatory tasks completed')).toBeVisible();
      await expect(card(manager,'Start Receipt').getByRole('button',{
        name:'Acknowledge confirmed synthetic equipment'})).toHaveCount(0);
    });
  }finally{await Promise.allSettled(contexts.map(c=>c.close()));}
});
