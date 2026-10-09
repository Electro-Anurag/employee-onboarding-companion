'use strict';
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');

function fixture(){
  const path=process.env.M4_BROWSER_CREDENTIAL_FILE;
  if(!path)throw Error('Missing isolated M4 browser fixture file');
  const data=fs.readFileSync(path,'utf8').split(/\r?\n/),users={};
  let caseId;
  for(const row of data){
    const caseMatch=row.match(/^CASE\s+([\da-f-]{36})$/);
    const roleMatch=row.match(/^(HR|EMPLOYEE|IT|MANAGER)\s+(\S+)\s+(\S+)$/);
    if(caseMatch)caseId=caseMatch[1];
    if(roleMatch)users[roleMatch[1]]={email:roleMatch[2],password:roleMatch[3]};
  }
  if(!caseId || ['HR','EMPLOYEE','IT','MANAGER'].some(r=>!users[r]))
    throw Error('M4 fixture credentials or case incomplete');
  return {caseId,users};
}
const {caseId,users}=fixture();
async function login(page,role){
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
  await page.getByLabel('Email').fill(users[role].email);
  await page.getByLabel('Password').fill(users[role].password);
  await page.getByRole('button',{name:'Sign in'}).click();
  await expect(page.getByText('Role: '+role)).toBeVisible();
}
function card(page,name){
  return page.getByRole('region',{name:'Case tasks'}).locator('article.task')
    .filter({has:page.getByRole('heading',{name,exact:true})});
}
async function open(page){
  await page.getByRole('button',{name:/^Cases \(/}).click();
  await expect(page.locator('.case-list').first().getByRole('button').first()).toBeVisible();
  await page.locator('.case-list').first().getByRole('button').first().click();
  await expect(page.getByRole('region',{name:'Case tasks'})).toBeVisible();
}
function dateInput(minutesAhead){
  const date=new Date(Date.now()+minutesAhead*60000);
  // UTC runner/browser intentionally matches the synthetic UTC fixture.
  return date.toISOString().slice(0,16);
}

test('M4 real Chromium quiz grading, meeting revisions and independent attendance',async({browser})=>{
  test.setTimeout(180000);
  const contexts=await Promise.all(Array.from({length:4},()=>browser.newContext()));
  const [employee,hr,manager,it]=await Promise.all(contexts.map(c=>c.newPage()));
  try{
    await test.step('synthetic training answers stay hidden; failed attempt cannot complete',async()=>{
      await login(employee,'EMPLOYEE');await open(employee);
      await expect(card(employee,'Workplace Training')).toContainText('READY');
      await card(employee,'Workplace Training').getByRole('button',{name:'View assigned training'}).click();
      const training=card(employee,'Workplace Training');
      await expect(training).toContainText('synthetic-workplace_training-v1');
      await training.getByLabel('How should a team member be treated?').selectOption('B');
      await training.getByLabel('Which system should be used for a synthetic task?').selectOption('B');
      await training.getByRole('button',{name:'Submit answers for server grading'}).click();
      await expect(training).toContainText('Attempt 1: 0 points — NOT PASSED');
      await expect(training).toContainText('IN_PROGRESS');
      await expect(employee.getByText('0/4 mandatory tasks completed')).toBeVisible();

      await login(it,'IT');await open(it);
      await expect(card(it,'Workplace Training').getByRole('button',{name:'Submit answers for server grading'})).toHaveCount(0);
      await login(hr,'HR');await open(hr);
      await card(hr,'Workplace Training').getByRole('button',{name:'View assigned training'}).click();
      await expect(card(hr,'Workplace Training').getByRole('button',{name:'Submit answers for server grading'})).toHaveCount(0);
    });
    await test.step('correct employee retry creates immutable typed training completion',async()=>{
      const training=card(employee,'Workplace Training');
      await training.getByLabel('How should a team member be treated?').selectOption('A');
      await training.getByLabel('Which system should be used for a synthetic task?').selectOption('A');
      await training.getByRole('button',{name:'Submit answers for server grading'}).click();
      await expect(training).toContainText('COMPLETED');
      await expect(employee.getByText('1/4 mandatory tasks completed')).toBeVisible();
      await training.getByRole('button',{name:'View assigned training'}).click();
      await expect(training).toContainText('Attempt 1: 0 points — NOT PASSED');
      await expect(training).toContainText('Attempt 2: 2 points — PASSED');
      await employee.reload();
      await expect(employee.getByText('Role: EMPLOYEE')).toBeVisible();
      await open(employee);
      await expect(card(employee,'Workplace Training')).toContainText('COMPLETED');
      await expect(employee.getByText('1/4 mandatory tasks completed')).toBeVisible();
    });
    await test.step('HR schedules a real future occurrence and cannot forge future attendance',async()=>{
      const session=card(hr,'Scheduled Orientation');
      await expect(session).toContainText('READY');
      await session.getByRole('button',{name:'Load activity schedule'}).click();
      await expect(session).toContainText('No meeting scheduled');
      await session.getByLabel('Meeting start (local)').fill(dateInput(15));
      await session.getByLabel('Meeting end (local)').fill(dateInput(30));
      await session.getByLabel('Meeting medium').selectOption('VIDEO');
      await session.getByLabel('Room or approved meeting reference').fill('Synthetic video room one');
      await session.getByLabel('Scheduling/rescheduling reason').fill('Initial synthetic new employee orientation');
      await session.getByRole('button',{name:'Schedule meeting occurrence'}).click();
      await expect(session).toContainText('Revision 1:');
      await expect(session).toContainText('IN_PROGRESS');
      await expect(session.getByRole('button',{name:'Record organizer attendance'})).toHaveCount(0);
      await expect(hr.getByText('1/4 mandatory tasks completed')).toBeVisible();
      await open(employee);
      await card(employee,'Scheduled Orientation').getByRole('button',{name:'Load activity schedule'}).click();
      await expect(card(employee,'Scheduled Orientation')).toContainText('Synthetic video room one');
      await expect(card(employee,'Scheduled Orientation').getByRole('button',{name:'Cancel current occurrence (task remains incomplete)'})).toHaveCount(0);
      await login(manager,'MANAGER');await open(manager);
      await expect(card(manager,'Scheduled Orientation').getByRole('button',{name:'Schedule meeting occurrence'})).toHaveCount(0);
    });
    await test.step('reasoned cancellation preserves unresolved task; HR reschedules revision 2',async()=>{
      const session=card(hr,'Scheduled Orientation');
      await session.getByLabel('Cancellation reason').fill('Synthetic organizer unavailable for this time');
      await session.getByRole('button',{name:'Cancel current occurrence (task remains incomplete)'}).click();
      await expect(session).toContainText('Cancelled: Synthetic organizer unavailable');
      await expect(session.getByRole('button',{name:'Record organizer attendance'})).toHaveCount(0);
      await expect(hr.getByText('1/4 mandatory tasks completed')).toBeVisible();
      await session.getByLabel('Meeting start (local)').fill(dateInput(16));
      await session.getByLabel('Meeting end (local)').fill(dateInput(31));
      await session.getByLabel('Meeting medium').selectOption('IN_PERSON');
      await session.getByLabel('Room or approved meeting reference').fill('Synthetic replacement meeting room');
      await session.getByLabel('Scheduling/rescheduling reason').fill('Reschedule after reasoned cancellation');
      await session.getByRole('button',{name:'Record reschedule'}).click();
      await expect(session).toContainText('Revision 2:');
      await expect(session).toContainText('Synthetic replacement meeting room');
      await expect(hr.getByText('1/4 mandatory tasks completed')).toBeVisible();
      await hr.reload();await expect(hr.getByText('Role: HR')).toBeVisible();await open(hr);
      await card(hr,'Scheduled Orientation').getByRole('button',{name:'Load activity schedule'}).click();
      await expect(card(hr,'Scheduled Orientation')).toContainText('Revision 1:');
      await expect(card(hr,'Scheduled Orientation')).toContainText('Revision 2:');
    });
    await test.step('completed-in-the-past fixture must need HR attendance and unlock its successor',async()=>{
      await expect(card(manager,'Manager Followup')).toContainText('PREREQUISITE_INCOMPLETE');
      const elapsed=card(hr,'Elapsed Orientation');
      await expect(elapsed).toContainText('IN_PROGRESS');
      await elapsed.getByRole('button',{name:'Load activity schedule'}).click();
      await expect(elapsed).toContainText('Past synthetic session');
      await elapsed.getByLabel('Organizer attendance evidence').fill(
        'Assigned HR recorded attendance for the elapsed synthetic fixture');
      await elapsed.getByRole('button',{name:'Record organizer attendance'}).click();
      await expect(card(hr,'Elapsed Orientation')).toContainText('COMPLETED');
      await expect(hr.getByText('2/4 mandatory tasks completed')).toBeVisible();
      await manager.reload();await expect(manager.getByText('Role: MANAGER')).toBeVisible();
      await open(manager);
      await expect(card(manager,'Manager Followup')).not.toContainText('PREREQUISITE_INCOMPLETE');
      await hr.reload();await expect(hr.getByText('Role: HR')).toBeVisible();await open(hr);
      await card(hr,'Elapsed Orientation').getByRole('button',{name:'Load activity schedule'}).click();
      await expect(card(hr,'Elapsed Orientation')).toContainText('Attendance ATTENDED');
      await expect(card(hr,'Scheduled Orientation')).not.toContainText('COMPLETED');
    });
  } finally {await Promise.all(contexts.map(c=>c.close()));}
});
