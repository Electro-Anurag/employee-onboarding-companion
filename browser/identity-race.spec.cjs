'use strict';
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');

function credentials(){
  const path=process.env.M2_BROWSER_CREDENTIAL_FILE;
  if(!path)throw new Error('Missing ephemeral browser fixture');
  const result={};
  for(const line of fs.readFileSync(path,'utf8').split(/\r?\n/)){
    const found=line.trim().match(/^(HR|HR_B)\s+(\S+)\s+(\S+)$/);
    if(found)result[found[1]]={email:found[2],password:found[3]};
  }
  if(!result.HR||!result.HR_B)throw new Error('Two independent HR fixtures required');
  return result;
}
const users=credentials();
async function mountedLogin(page,role,display){
  await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
  await page.getByLabel('Email').fill(users[role].email);
  await page.getByLabel('Password').fill(users[role].password);
  await page.getByRole('button',{name:'Sign in'}).click();
  await expect(page.getByText(display,{exact:true})).toBeVisible();
}

test('R3: successfully delivered prior identity and protected payload never overwrite newer HR',async({browser})=>{
  test.setTimeout(180000);
  const context=await browser.newContext();
  const page=await context.newPage();
  try{
    await page.goto('/');
    await mountedLogin(page,'HR','Synthetic Hr');
    const oldMeResponse=await page.request.get('/api/v1/auth/me');
    expect(oldMeResponse.status()).toBe(200);
    const oldMe=await oldMeResponse.json();
    expect(oldMe.role).toBe('HR');
    let templateResponse=await page.request.get('/api/v1/templates');
    expect(templateResponse.status()).toBe(200);
    let oldTemplates=await templateResponse.json();
    if(!oldTemplates.results.length){
      await page.getByRole('button',{name:/Templates \(/}).click();
      await page.getByRole('button',{name:'Create default synthetic 17-task template'}).click();
      await expect(page.getByRole('heading',{name:/Employee First Month.*DRAFT/})).toBeVisible();
      templateResponse=await page.request.get('/api/v1/templates');
      expect(templateResponse.status()).toBe(200);
      oldTemplates=await templateResponse.json();
    }
    expect(oldTemplates.results.length).toBeGreaterThan(0);

    await test.step('old successful startup /auth/me response arrives after HR-B login',async()=>{
      let seen,releaseOld,delivered;
      const intercepted=new Promise(resolve=>{seen=resolve;});
      const release=new Promise(resolve=>{releaseOld=resolve;});
      const settled=new Promise(resolve=>{delivered=resolve;});
      let ordinal=0;
      await page.route('**/api/v1/auth/me',async route=>{
        if(++ordinal!==1){await route.continue();return;}
        seen();
        await release;
        await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(oldMe)});
        delivered();
      });
      await page.reload();
      await intercepted;
      await mountedLogin(page,'HR_B','Synthetic HR Other Organization');
      releaseOld();
      await settled; // fulfilled 200; a canceled route cannot be counted as PASS
      await expect(page.getByText('Synthetic HR Other Organization',{exact:true})).toBeVisible();
      await expect(page.getByText('Synthetic Hr',{exact:true})).toHaveCount(0);
      await page.unroute('**/api/v1/auth/me');
    });

    await test.step('old successful organization-A template payload arrives after HR-B login',async()=>{
      await page.getByRole('button',{name:'Sign out'}).click();
      await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
      let seen,releaseOld,delivered;
      const intercepted=new Promise(resolve=>{seen=resolve;});
      const release=new Promise(resolve=>{releaseOld=resolve;});
      const settled=new Promise(resolve=>{delivered=resolve;});
      let first=true;
      await page.route('**/api/v1/templates',async route=>{
        if(!first){await route.continue();return;}
        first=false;
        seen();
        await release;
        await route.fulfill({status:200,contentType:'application/json',
          body:JSON.stringify(oldTemplates)});
        delivered();
      });
      await mountedLogin(page,'HR','Synthetic Hr');
      await intercepted; // the old HR's background refresh is held
      await expect(page.getByRole('button',{name:'Sign out'})).toBeEnabled();
      await page.getByRole('button',{name:'Sign out'}).click();
      await mountedLogin(page,'HR_B','Synthetic HR Other Organization');
      releaseOld();
      await settled; // actual stale HR-A 200 is fulfilled after HR-B login
      await page.unroute('**/api/v1/templates');
      await page.getByRole('button',{name:/Templates \(/}).click();
      await expect(page.getByRole('button',{name:'Templates (0)'})).toBeVisible();
      await expect(page.getByText('Employee First Month (Synthetic)')).toHaveCount(0);
      await expect(page.locator('textarea.json-editor')).toHaveCount(0);
      await expect(page.getByText('Synthetic HR Other Organization',{exact:true})).toBeVisible();
    });
  }finally{await context.close();}
});
