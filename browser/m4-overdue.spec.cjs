'use strict';
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');

const fixturePath=process.env.M4_OVERDUE_BROWSER_CREDENTIAL_FILE;
if(!fixturePath)throw Error('Missing isolated M4 overdue browser fixture');
const users={};
let caseId;
for(const row of fs.readFileSync(fixturePath,'utf8').split(/\r?\n/)){
  const c=row.match(/^CASE\s+([\da-f-]{36})$/);
  const u=row.match(/^(HR|EMPLOYEE|IT|MANAGER)\s+(\S+)\s+(\S+)$/);
  if(c)caseId=c[1];
  if(u)users[u[1]]={email:u[2],password:u[3]};
}
if(!caseId||!users.HR||!users.MANAGER)throw Error('Incomplete overdue browser fixture');

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
function asDatetimeLocal(ms){return new Date(ms).toISOString().slice(0,16);}

test('R6: real Chromium overdue cancel-reschedule genuinely elapses, attendance unlocks successor',async({browser})=>{
  test.setTimeout(390000);
  const hrContext=await browser.newContext(),managerContext=await browser.newContext();
  const hr=await hrContext.newPage(),manager=await managerContext.newPage();
  try{
    await login(hr,'HR');await open(hr);
    await login(manager,'MANAGER');await open(manager);
    const activity=card(hr,'Overdue Orientation');
    await expect(activity).toContainText('READY');
    await expect(card(manager,'Followup After Overdue')).toContainText('PREREQUISITE_INCOMPLETE');
    await activity.getByRole('button',{name:'Load activity schedule'}).click();
    await expect(activity).toContainText('No meeting scheduled');
    const first=Date.now()+10*60000;
    await activity.getByLabel('Meeting start (local)').fill(asDatetimeLocal(first));
    await activity.getByLabel('Meeting end (local)').fill(asDatetimeLocal(first+15*60000));
    await activity.getByLabel('Room or approved meeting reference').fill('Synthetic cancelled overdue room');
    await activity.getByLabel('Scheduling/rescheduling reason').fill(
      'Recovery planning after original mandatory due date');
    await activity.getByRole('button',{name:'Schedule meeting occurrence'}).click();
    await expect(activity).toContainText('Revision 1:');
    await expect(activity).toContainText('IN_PROGRESS');
    await activity.getByLabel('Cancellation reason').fill(
      'Synthetic organizer cancelled the original booked recovery meeting');
    await activity.getByRole('button',{
      name:'Cancel current occurrence (task remains incomplete)'}).click();
    await expect(activity).toContainText('Cancelled:');
    await expect(activity).not.toContainText('COMPLETED');

    // Real user-facing scheduling requires at least 60 seconds advance notice;
    // datetime-local controls support minute precision. Elapse the replacement
    // in actual wall time, without clock mocks, ORM, or direct API attendance.
    const replacementStart=Math.ceil(Date.now()/60000)*60000+60000;
    const replacementEnd=replacementStart+60000;
    await activity.getByLabel('Meeting start (local)').fill(
      asDatetimeLocal(replacementStart));
    await activity.getByLabel('Meeting end (local)').fill(
      asDatetimeLocal(replacementEnd));
    await activity.getByLabel('Meeting medium').selectOption('IN_PERSON');
    await activity.getByLabel('Room or approved meeting reference').fill(
      'Synthetic real-time overdue replacement');
    await activity.getByLabel('Scheduling/rescheduling reason').fill(
      'Actual booked replacement after overdue cancellation');
    await activity.getByRole('button',{name:'Record reschedule'}).click();
    await expect(activity).toContainText('Revision 2:');
    await expect(activity).toContainText('Synthetic real-time overdue replacement');
    await expect(activity.getByRole('button',{name:'Record organizer attendance'})).toHaveCount(0);
    await expect(card(manager,'Followup After Overdue')).toContainText('PREREQUISITE_INCOMPLETE');

    const remaining=replacementEnd-Date.now()+1500;
    if(remaining>0)await hr.waitForTimeout(remaining);
    expect(Date.now()).toBeGreaterThan(replacementEnd);
    await hr.reload();await expect(hr.getByText('Role: HR')).toBeVisible();await open(hr);
    const elapsed=card(hr,'Overdue Orientation');
    await elapsed.getByRole('button',{name:'Load activity schedule'}).click();
    await expect(elapsed).toContainText('Revision 1:');
    await expect(elapsed).toContainText('Cancelled:');
    await expect(elapsed).toContainText('Revision 2:');
    await expect(elapsed.getByRole('button',{name:'Record organizer attendance'})).toBeVisible();
    await elapsed.getByLabel('Organizer attendance evidence').fill(
      'HR independently verified attendance after actual overdue replacement elapsed');
    await elapsed.getByRole('button',{name:'Record organizer attendance'}).click();
    await expect(elapsed).toContainText('COMPLETED');
    await expect(elapsed).toContainText('Attendance ATTENDED');
    await manager.reload();await expect(manager.getByText('Role: MANAGER')).toBeVisible();
    await open(manager);
    await expect(card(manager,'Followup After Overdue')).toContainText('READY');
  }finally{
    await Promise.allSettled([hrContext.close(),managerContext.close()]);
  }
});
