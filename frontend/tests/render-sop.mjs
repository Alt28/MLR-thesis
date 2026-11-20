import { chromium } from 'playwright'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import { copyFile } from 'node:fs/promises'
const dir=path.resolve('outputs/sop_system_guide')
const stem='System_SOP_1_to_3_Illustrated_Guide'
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'})
try {
 const page=await browser.newPage()
 await page.goto(pathToFileURL(path.join(dir,stem+'.html')).href)
 await page.evaluate(()=>document.fonts.ready)
 const issues=await page.locator('section').evaluateAll(sections=>sections.map((s,i)=>({page:i+1,contentBottom:s.lastElementChild.previousElementSibling.getBoundingClientRect().bottom-s.getBoundingClientRect().top,footer:s.lastElementChild.offsetTop,images:[...s.querySelectorAll('img')].every(i=>i.complete&&i.naturalWidth>0)})).filter(x=>x.contentBottom>x.footer-8||!x.images))
 if(issues.length)throw Error(JSON.stringify(issues))
 await page.pdf({path:path.join(dir,stem+'.pdf'),printBackground:true,preferCSSPageSize:true})
 await copyFile(path.join(dir,stem+'.pdf'),path.join(process.env.USERPROFILE,'Downloads',stem+'.pdf'))
 console.log('PDF created; all pages fit and screenshots loaded.')
} finally {await browser.close()}
