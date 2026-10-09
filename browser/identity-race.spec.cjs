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

/*
 * Test-only wire observation. A route.fulfill promise is NOT evidence that
 * application code consumed response.json() or finished the React continuation.
 * The injected header identifies only our captured stale 200, not later fetches.
 */
async function installConsumptionProbe(context){
  await context.addInitScript(()=>{
    const nativeFetch=window.fetch.bind(window);
    let releaseHeldOwners;
    const ownerGate=new Promise(resolve=>{releaseHeldOwners=resolve;});
    const probe={
      consumed:{identity:0,templates:0},
      ordinaryOwnerJson:[],
      heldOwnerFetches:[],
      heldOwnerJson:[],
      ownersReleased:false,
      releaseOwners(){
        this.ownersReleased=true;
        releaseHeldOwners();
      },
    };
    window.__r3Probe=probe;
    window.fetch=async(...args)=>{
      const input=args[0];
      const url=typeof input==='string'?input:input.url;
      const parsed=new URL(url,location.href);
      const owner=parsed.pathname==='/api/v1/owners'?parsed.searchParams.get('role'):null;
      // Only the OLD refresh can start owner requests after the stale template
      // JSON was consumed. The newer HR-B refresh is allowed to settle first.
      const heldOwner=Boolean(owner&&probe.consumed.templates===1);
      if(heldOwner)probe.heldOwnerFetches.push(owner);
      const response=await nativeFetch(...args);
      if(heldOwner)await ownerGate;
      const marker=response.headers.get('x-r3-delayed-response');
      if(marker==='identity'||marker==='templates'||owner){
        const readJson=response.json.bind(response);
        response.json=async()=>{
          const body=await readJson();
          if(marker==='identity'||marker==='templates')probe.consumed[marker]++;
          if(owner){
            (heldOwner?probe.heldOwnerJson:probe.ordinaryOwnerJson).push(owner);
          }
          return body;
        };
      }
      return response;
    };
  });
}

async function awaitStaleContinuation(page,marker,dependentOwners=0){
  await page.waitForFunction(({marker,dependentOwners})=>{
    const p=window.__r3Probe;
    return p&&p.consumed[marker]===1&&
      (dependentOwners===0||
        (p.ownersReleased&&p.heldOwnerJson.length===dependentOwners));
  },{marker,dependentOwners});
  // JSON consumption wakes the async continuation via microtasks; the old
  // template refresh also resumes from Promise.all(owner JSONs). Cross a task
  // boundary and two paint frames before asserting the rendered identity/data.
  await page.evaluate(async()=>{
    await new Promise(resolve=>setTimeout(resolve,0));
    await new Promise(resolve=>requestAnimationFrame(resolve));
    await new Promise(resolve=>requestAnimationFrame(resolve));
  });
}

test('R3: successfully delivered prior identity and protected payload never overwrite newer HR',async({browser})=>{
  test.setTimeout(180000);
  const context=await browser.newContext();
  await installConsumptionProbe(context);
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
        await route.fulfill({status:200,contentType:'application/json',
          headers:{'x-r3-delayed-response':'identity'},body:JSON.stringify(oldMe)});
        delivered();
      });
      await page.reload();
      await intercepted;
      await mountedLogin(page,'HR_B','Synthetic HR Other Organization');
      releaseOld();
      await settled;
      await awaitStaleContinuation(page,'identity');
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
          headers:{'x-r3-delayed-response':'templates'},
          body:JSON.stringify(oldTemplates)});
        delivered();
      });
      await mountedLogin(page,'HR','Synthetic Hr');
      await intercepted; // the old HR's background refresh is held
      await expect(page.getByRole('button',{name:'Sign out'})).toBeEnabled();
      await page.getByRole('button',{name:'Sign out'}).click();
      // Prove B's separate-organization refresh consumed ALL owner responses
      // before releasing A's pending template response.
      await page.evaluate(()=>{window.__r3Probe.ordinaryOwnerJson=[];});
      await mountedLogin(page,'HR_B','Synthetic HR Other Organization');
      await page.waitForFunction(()=>window.__r3Probe.ordinaryOwnerJson.length===3);
      releaseOld();
      await settled;
      // The stale template JSON must be consumed, and its three dependent
      // owner reads must actually be pending, not merely queued by Playwright.
      await page.waitForFunction(()=>{
        const p=window.__r3Probe;
        return p.consumed.templates===1&&p.heldOwnerFetches.length===3;
      });
      const before=await page.evaluate(()=>({
        ownerJson:window.__r3Probe.heldOwnerJson.length,
        released:window.__r3Probe.ownersReleased,
      }));
      expect(before).toEqual({ownerJson:0,released:false});
      let continuationSettled=false;
      const continuation=awaitStaleContinuation(page,'templates',3).then(()=>{
        continuationSettled=true;
      });
      expect(continuationSettled).toBe(false);
      await page.evaluate(()=>window.__r3Probe.releaseOwners());
      await continuation;
      expect(continuationSettled).toBe(true);
      await page.unroute('**/api/v1/templates');
      await page.getByRole('button',{name:/Templates \(/}).click();
      await expect(page.getByRole('button',{name:'Templates (0)'})).toBeVisible();
      await expect(page.getByText('Employee First Month (Synthetic)')).toHaveCount(0);
      await expect(page.locator('textarea.json-editor')).toHaveCount(0);
      await expect(page.getByText('Synthetic HR Other Organization',{exact:true})).toBeVisible();
    });
  }finally{await context.close();}
});
