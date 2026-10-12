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
  const response=page.waitForResponse(r=>
    r.url().includes('/cases/'+caseId+'/tasks')&&r.status()===200);
  await page.locator('.case-list').first().getByRole('button').first().click();
  await response;
  await expect(page.getByRole('region',{name:'Case tasks'})).toBeVisible();
  // Await asynchronous case selection before opening the complete plan.
  const full=page.getByRole('button',{name:'View all steps (advanced)'});
  await expect(full).toBeVisible();
  await full.click();
  await expect(page.getByRole('region',{name:'Case tasks'})
    .locator('article.task')).toHaveCount(4);
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
    await manager.reload();
    await expect(manager.getByText('Role: MANAGER')).toBeVisible();
    await open(manager);
    await expect(card(manager,'Followup After Overdue')).toContainText('PREREQUISITE_INCOMPLETE');

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
    await manager.reload();
    await expect(manager.getByText('Role: MANAGER')).toBeVisible();
    await open(manager);
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


test('D4 E04: manager missed real meeting remains blocked until an actually elapsed reschedule is attended',async({browser})=>{
  test.setTimeout(900000);
  const managerContext=await browser.newContext(),hrContext=await browser.newContext();
  const manager=await managerContext.newPage(),hr=await hrContext.newPage();
  const scheduleAt=()=>{const start=Math.ceil(Date.now()/60000)*60000+60000;
    return {start,end:start+60000};};
  const elapse=async(page,end)=>{
    const remaining=end-Date.now()+1750;
    if(remaining>0)await page.waitForTimeout(remaining);
    expect(Date.now()).toBeGreaterThan(end);
  };
  try{
    await login(manager,'MANAGER');await open(manager);
    await login(hr,'HR');await open(hr);
    const meeting=card(manager,'Manager Recovery Check-in');
    await expect(meeting).toContainText('READY');
    await expect(card(hr,'HR Followup After Manager')).toContainText('PREREQUISITE_INCOMPLETE');
    await meeting.getByRole('button',{name:'Load activity schedule'}).click();
    await expect(meeting).toContainText('No meeting scheduled');

    const first=scheduleAt();
    await meeting.getByLabel('Meeting start (local)').fill(asDatetimeLocal(first.start));
    await meeting.getByLabel('Meeting end (local)').fill(asDatetimeLocal(first.end));
    await meeting.getByLabel('Meeting medium').selectOption('VIDEO');
    await meeting.getByLabel('Room or approved meeting reference').fill('Synthetic manager initial check-in');
    await meeting.getByLabel('Scheduling/rescheduling reason').fill(
      'Arrange assigned manager check-in with real elapsed attendance');
    await meeting.getByRole('button',{name:'Schedule meeting occurrence'}).click();
    await expect(meeting).toContainText('Revision 1:');
    await expect(meeting).toContainText('IN_PROGRESS');
    await expect(meeting.getByRole('button',{name:'Record organizer attendance'})).toHaveCount(0);

    await hr.reload();await expect(hr.getByText('Role: HR')).toBeVisible();await open(hr);
    const hrMeeting=card(hr,'Manager Recovery Check-in');
    await hrMeeting.getByRole('button',{name:'Load activity schedule'}).click();
    await expect(hrMeeting).toContainText('Synthetic manager initial check-in');
    await expect(hrMeeting.getByRole('button',{name:'Record organizer attendance'})).toHaveCount(0);
    await expect(hrMeeting.getByRole('button',{name:'Record reschedule'})).toHaveCount(0);

    await elapse(manager,first.end);
    await manager.reload();await expect(manager.getByText('Role: MANAGER')).toBeVisible();await open(manager);
    const elapsed=card(manager,'Manager Recovery Check-in');
    await elapsed.getByRole('button',{name:'Load activity schedule'}).click();
    await expect(elapsed.getByRole('button',{name:'Record organizer attendance'})).toBeVisible();
    await elapsed.getByLabel('Actual attendance outcome').selectOption('MISSED');
    await elapsed.getByLabel('Organizer attendance evidence').fill(
      'Assigned manager confirms employee missed the elapsed check-in');
    await elapsed.getByRole('button',{name:'Record organizer attendance'}).click();
    await expect(elapsed).toContainText('Attendance MISSED');
    await expect(elapsed).toContainText('IN_PROGRESS');
    await expect(elapsed).not.toContainText('COMPLETED');

    await hr.reload();await expect(hr.getByText('Role: HR')).toBeVisible();await open(hr);
    await expect(card(hr,'HR Followup After Manager')).toContainText('PREREQUISITE_INCOMPLETE');

    const replacement=scheduleAt();
    await elapsed.getByLabel('Meeting start (local)').fill(asDatetimeLocal(replacement.start));
    await elapsed.getByLabel('Meeting end (local)').fill(asDatetimeLocal(replacement.end));
    await elapsed.getByLabel('Meeting medium').selectOption('IN_PERSON');
    await elapsed.getByLabel('Room or approved meeting reference').fill('Synthetic manager recovery room');
    await elapsed.getByLabel('Scheduling/rescheduling reason').fill(
      'Reschedule following documented missed employee check-in');
    await elapsed.getByRole('button',{name:'Record reschedule'}).click();
    await expect(elapsed).toContainText('Revision 2:');
    await expect(elapsed).toContainText('Synthetic manager recovery room');
    await expect(elapsed.getByRole('button',{name:'Record organizer attendance'})).toHaveCount(0);
    await expect(card(hr,'HR Followup After Manager')).toContainText('PREREQUISITE_INCOMPLETE');

    await elapse(manager,replacement.end);
    await manager.reload();await expect(manager.getByText('Role: MANAGER')).toBeVisible();await open(manager);
    const recovered=card(manager,'Manager Recovery Check-in');
    await recovered.getByRole('button',{name:'Load activity schedule'}).click();
    await expect(recovered).toContainText('Attendance MISSED');
    await expect(recovered).toContainText('Revision 2:');
    await recovered.getByLabel('Actual attendance outcome').selectOption('ATTENDED');
    await recovered.getByLabel('Organizer attendance evidence').fill(
      'Assigned manager confirms the replacement check-in was attended after its end');
    await recovered.getByRole('button',{name:'Record organizer attendance'}).click();
    await expect(recovered).toContainText('Attendance ATTENDED');
    await expect(recovered).toContainText('COMPLETED');
    await manager.reload();await expect(manager.getByText('Role: MANAGER')).toBeVisible();await open(manager);
    await card(manager,'Manager Recovery Check-in').getByRole('button',{name:'Load activity schedule'}).click();
    await expect(card(manager,'Manager Recovery Check-in')).toContainText('Attendance MISSED');
    await expect(card(manager,'Manager Recovery Check-in')).toContainText('Attendance ATTENDED');
    await hr.reload();await expect(hr.getByText('Role: HR')).toBeVisible();await open(hr);
    await expect(card(hr,'HR Followup After Manager')).toContainText('READY');
  } finally {
    await Promise.allSettled([managerContext.close(),hrContext.close()]);
  }
});
