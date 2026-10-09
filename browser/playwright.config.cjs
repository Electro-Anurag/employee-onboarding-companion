'use strict';
const { defineConfig }=require('@playwright/test');

module.exports=defineConfig({
  testDir:__dirname,
  testMatch:'*.spec.cjs',
  fullyParallel:false,
  workers:1,
  retries:0,
  timeout:60000,
  expect:{timeout:12000},
  reporter:[['list']],
  use:{
    baseURL:'http://127.0.0.1:8000',
    browserName:'chromium',
    headless:true,
    viewport:{width:1440,height:900},
    actionTimeout:15000,
    navigationTimeout:15000,
    screenshot:'off',
    trace:'off',
    video:'off',
  },
});
