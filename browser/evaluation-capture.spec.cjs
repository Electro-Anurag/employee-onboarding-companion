'use strict';
/* Real browser, real Django/PostgreSQL, fictional users only.
   Produces an unedited test-context video + screenshots; does NOT claim to
   record a hosted production service, full J01-J05, or external model AI.
*/
const fs=require('node:fs');
const path=require('node:path');
const {test,expect}=require('@playwright/test');
const credsPath=process.env.M2_BROWSER_CREDENTIAL_FILE;
const output=process.env.EOC_EVALUATION_CAPTURE_DIR;
if(!credsPath || !output)throw Error('Private local synthetic fixture and output directory required');
const accounts={};
for(const line of fs.readFileSync(credsPath,'utf8').split(/\r?\n/)){
  const match=line.trim().match(/^(HR|EMPLOYEE|IT|MANAGER)\s+(\S+)\s+(\S+)$/);
  if(match)accounts[match[1]]={email:match[2],password:match[3]};
}
for(const role of ['HR','EMPLOYEE','IT','MANAGER']){
  if(!accounts[role])throw Error('Missing synthetic role '+role);
}
fs.mkdirSync(output,{recursive:true,mode:0o700});

async function shot(page,name){
  await page.screenshot({path:path.join(output,name+'.png'),fullPage:false});
}
async function login(page,role){
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
  await page.getByLabel('Email').fill(accounts[role].email);
  await page.getByLabel('Password').fill(accounts[role].password);
  const submit=page.getByRole('button',{name:'Sign in'});
  await expect(submit).toBeEnabled();
  const [response]=await Promise.all([
    page.waitForResponse(x=>x.url().endsWith('/api/v1/auth/login')&&
      x.request().method()==='POST'),
    submit.click(),
  ]);
  expect(response.status(),'real '+role+' sign-in').toBe(200);
  await expect(page.getByText('Role: '+role)).toBeVisible();
  const guide=page.locator('details.evaluation-guide');
  await expect(guide).toBeVisible();
  await guide.locator('summary').click();
  await expect(guide.getByText('Evaluation walkthrough')).toBeVisible();
  await expect(guide).toContainText('deterministic guidance is not model AI');
}
async function logout(page){
  await page.getByRole('button',{name:'Sign out'}).click();
  await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
}

test('real synthetic four-role evaluation walkthrough with recorded UI evidence',async({browser})=>{
  test.setTimeout(210000);
  const context=await browser.newContext({
    viewport:{width:1280,height:820},
    recordVideo:{dir:output,size:{width:1280,height:820}},
  });
  const page=await context.newPage();
  const evidence=[];
  try{
    await page.goto('/');
    await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
    await shot(page,'01-public-sign-in');
    evidence.push('01-public-sign-in');

    await login(page,'HR');
    await shot(page,'02-hr-role-guide');
    evidence.push('02-hr-role-guide');
    await page.getByRole('navigation',{name:'Workspace'})
      .getByRole('button',{name:/^Templates/}).click();
    await page.getByRole('button',{name:'Create default synthetic 17-task template'}).click();
    await expect(page.getByRole('button',{name:'Validate and publish'})).toBeVisible();
    await page.getByRole('button',{name:'Validate and publish'}).click();
    await expect(page.getByRole('heading',{name:/Employee First Month.*PUBLISHED/})).toBeVisible();
    await shot(page,'03-hr-published-template');
    evidence.push('03-hr-published-template');

    await page.getByRole('navigation',{name:'Workspace'}).getByRole('button',{name:/^Cases/}).click();
    const form=page.locator('section.panel')
      .filter({has:page.getByRole('heading',{name:'Create an onboarding case'})});
    await expect(form).toBeVisible();
    for(let i=0;i<4;i++)await form.locator('select').nth(i).selectOption({index:1});
    await form.getByLabel('Joining date').fill(
      new Date(Date.now()+21*86400000).toISOString().slice(0,10));
    const [created]=await Promise.all([
      page.waitForResponse(x=>x.url().endsWith('/api/v1/cases')&&x.request().method()==='POST'),
      form.getByRole('button',{name:'Create case'}).click(),
    ]);
    expect(created.status()).toBe(201);
    const option=page.locator('.case-list').first().getByRole('button').first();
    await expect(option).toContainText('CREATED');
    await option.click();
    await expect(page.getByRole('button',{name:'Activate case'})).toBeVisible();
    await page.getByRole('button',{name:'Activate case'}).click();
    await expect(page.getByRole('region',{name:'Case tasks'})).toContainText('PRE_JOINING');
    await shot(page,'04-hr-case-activated');
    evidence.push('04-hr-case-activated');
    await logout(page);

    await login(page,'MANAGER');
    await page.getByRole('navigation',{name:'Workspace'}).getByRole('button',{name:/^Cases/}).click();
    await page.locator('.case-list').first().getByRole('button').first().click();
    await expect(page.getByRole('region',{name:'Case tasks'})).toBeVisible();
    await page.getByRole('button',{name:'View all steps (advanced)'}).click();
    const manager=page.getByRole('region',{name:'Case tasks'})
      .locator('article.task')
      .filter({has:page.getByRole('heading',{name:'Manager Preparation',exact:true})});
    await expect(manager).toContainText('READY');
    await manager.getByRole('button',{name:'Complete preparation'}).click();
    await manager.getByLabel('First-week plan')
      .fill('Synthetic first-week orientation and mentoring plan');
    await manager.getByLabel("Buddy's name").fill('Synthetic Buddy');
    await manager.getByLabel('Workstation is ready').check();
    await manager.getByLabel('Attestation note').fill('Fictional readiness confirmed');
    await manager.getByRole('button',{name:'Submit recorded evidence'}).click();
    await expect(manager).toContainText('COMPLETED');
    await shot(page,'05-manager-real-typed-evidence');
    evidence.push('05-manager-real-typed-evidence');
    await logout(page);

    await login(page,'EMPLOYEE');
    await page.getByRole('navigation',{name:'Workspace'}).getByRole('button',{name:/^Cases/}).click();
    await page.locator('.case-list').first().getByRole('button').first().click();
    await expect(page.getByRole('region',{name:'Case tasks'})).toBeVisible();
    await shot(page,'06-employee-assigned-work');
    evidence.push('06-employee-assigned-work');
    await logout(page);

    await login(page,'IT');
    await page.getByRole('navigation',{name:'Workspace'}).getByRole('button',{name:/^Cases/}).click();
    await page.locator('.case-list').first().getByRole('button').first().click();
    await expect(page.getByRole('region',{name:'Case tasks'})).toBeVisible();
    await shot(page,'07-it-assigned-case');
    evidence.push('07-it-assigned-case');
    await logout(page);

    await login(page,'HR');
    await page.getByRole('navigation',{name:'Workspace'}).getByRole('button',{name:'HR portfolio'}).click();
    await expect(page.getByRole('heading',{name:'My assigned onboarding cases'})).toBeVisible();
    await shot(page,'08-hr-portfolio-after-manager-evidence');
    evidence.push('08-hr-portfolio-after-manager-evidence');

    const record={
      kind:'LOCAL_CI_SYNTHETIC_CHROMIUM_RECORDING_NOT_HOSTED_ACCEPTANCE',
      source_sha:process.env.GITHUB_SHA||'unknown',
      roles:['HR','MANAGER','EMPLOYEE','IT'],
      frames:evidence,
      backend:'Django/PostgreSQL commands, not mocked API responses',
      boundaries:['No real employee data','No external HR/IT provisioning',
        'No hosted real S3/scanner proven by this clip',
        'No actual LLM inference shown','Not complete J01-J05'],
    };
    fs.writeFileSync(path.join(output,'capture-manifest.json'),
      JSON.stringify(record,null,2)+'\n',{mode:0o600});
    console.log('EOC_EVALUATION_SYNTHETIC_FOUR_ROLE_RECORDING_PASS',evidence.length);
  } finally{
    await context.close(); // writes Playwright .webm recording even if assertion failed.
  }
});
