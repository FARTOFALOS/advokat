const {chromium}=require('playwright');
const {pathToFileURL}=require('url');
const path=require('path');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1280,height:1000},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(pathToFileURL(path.join(__dirname,'roadmap.html')).href,{waitUntil:'load'});
 const qa=path.join(__dirname,'qa');
 await page.screenshot({path:path.join(qa,'roadmap-desktop.png')});
 const desktop=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
 const results=[];
 for(const [name,count] of [['Обращения в суд',4],['Приложения',2],['Для себя',1],['Все',7]]){
   await page.getByRole('button',{name,exact:true}).click();
   const got=await page.locator('.file:visible').count();results.push({name,count:got});
   if(got!==count)throw Error('filter mismatch '+name);
 }
 await page.locator('#files').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(qa,'roadmap-files.png')});
 await page.setViewportSize({width:390,height:900});
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:path.join(qa,'roadmap-mobile.png')});
 const mobile=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
 const out={desktop,mobile,filters:results,errors};
 fs.writeFileSync(path.join(qa,'roadmap-qa.json'),JSON.stringify(out,null,2));
 console.log(JSON.stringify(out));
 await browser.close();
 if(errors.length||desktop.scroll>desktop.width||mobile.scroll>mobile.width)process.exitCode=1;
})().catch(e=>{console.error(String(e));process.exitCode=1});
