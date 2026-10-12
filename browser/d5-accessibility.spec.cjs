'use strict';
// D5 focused physical Chromium keyboard/landmark/mobile acceptance.
// This is NOT a complete WCAG audit or hosted release validation.
const fs=require('node:fs');
const {test,expect}=require('@playwright/test');
const file=process.env.M2_BROWSER_CREDENTIAL_FILE;
if(!file)throw new Error('Synthetic credential-file path required for D5 browser test');
const hrLine=fs.readFileSync(file,'utf8').split(/\r?\n/).find(x=>/^HR\s/.test(x));
const parts=hrLine?.trim().split(/\s+/);
if(!parts || parts.length!==3)throw new Error('Missing synthetic HR role');
const hr={email:parts[1],password:parts[2]};

async function noHorizontalPageOverflow(page,context){
  const dimensions=await page.evaluate(()=>{
    const width=window.innerWidth;
    const scrollWidth=document.documentElement.scrollWidth;
    const offenders=Array.from(document.querySelectorAll('body *'))
      .filter(node=>{
        const rect=node.getBoundingClientRect();
        const style=getComputedStyle(node);
        return style.position!=='fixed' && style.display!=='none' &&
          rect.right>width+1 && rect.width>0 && rect.top<window.innerHeight*3;
      }).slice(0,6).map(node=>({tag:node.tagName,cls:node.className,
        text:(node.textContent||'').trim().slice(0,35),
        right:Math.round(node.getBoundingClientRect().right)}));
    return {width,scrollWidth,offenders};
  });
  expect(dimensions.scrollWidth,context+': '+JSON.stringify(dimensions))
    .toBeLessThanOrEqual(dimensions.width+1);
}

test('D5 logged-out semantic main, visible skip focus and narrow viewport layout',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Sign in'})).toBeVisible();
  await expect(page.getByRole('main')).toHaveCount(1);
  await expect(page.getByRole('banner')).toHaveCount(1);
  await expect(page.getByRole('navigation',{name:'Workspace'})).toHaveCount(0);
  await page.keyboard.press('Tab');
  const skip=page.getByRole('link',{name:'Skip to main content'});
  await expect(skip).toBeFocused();
  await expect(skip).toBeVisible();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Email')).toBeFocused();
  for(const width of [320,375,768,1440]){
    await page.setViewportSize({width,height:850});
    await noHorizontalPageOverflow(page,'Logged-out width '+width);
  }
});

test('D5 authenticated HR navigation is keyboard-operable and responsive',async({page})=>{
  await page.setViewportSize({width:320,height:760});
  await page.goto('/');
  await page.getByLabel('Email').fill(hr.email);
  await page.getByLabel('Password').fill(hr.password);
  await page.getByRole('button',{name:'Sign in'}).press('Enter');
  await expect(page.getByText('Role: HR')).toBeVisible();
  await expect(page.getByRole('main')).toHaveCount(1);
  const nav=page.getByRole('navigation',{name:'Workspace'});
  await expect(nav).toBeVisible();
  await expect(page.locator('main nav')).toHaveCount(0);
  const cases=nav.getByRole('button',{name:/^Cases \(/});
  const inbox=nav.getByRole('button',{name:'In-app inbox'});
  await expect(cases).toHaveAttribute('aria-pressed','true');
  await expect(inbox).toHaveAttribute('aria-pressed','false');
  await inbox.focus();
  await page.keyboard.press('Enter');
  await expect(inbox).toHaveAttribute('aria-pressed','true');
  await expect(page.getByRole('region',{name:'In-app inbox'})).toBeVisible();
  await cases.focus();
  await page.keyboard.press('Enter');
  await expect(cases).toHaveAttribute('aria-pressed','true');
  await expect(page.getByRole('heading',{name:'Authorized cases'})).toBeVisible();
  const form=page.locator('section.panel')
    .filter({has:page.getByRole('heading',{name:'Create an onboarding case'})});
  await expect(form).toBeVisible();
  const missing=await form.locator('input,select,textarea').evaluateAll(nodes=>
    nodes.filter(node=>{
      const input=node;
      return !input.getAttribute('aria-label') &&
        !(input.labels&&input.labels.length>0);
    }).map(x=>x.outerHTML.slice(0,120)));
  expect(missing,'Every HR case form control needs an accessible label').toEqual([]);
  for(const width of [320,375,768,1440]){
    await page.setViewportSize({width,height:860});
    await noHorizontalPageOverflow(page,'Authenticated HR width '+width);
  }
  await page.setViewportSize({width:320,height:760});
  await page.reload();
  await expect(page.getByRole('navigation',{name:'Workspace'})).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link',{name:'Skip to main content'})).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('main')).toBeFocused();
  await expect(page.getByRole('heading',{name:'Authorized cases'})).toBeVisible();
});
