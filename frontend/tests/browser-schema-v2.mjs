// Artificial software fixtures, isolated storage. No result is transportation research evidence.
import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, mkdir, readFile, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const temporary = await mkdtemp(path.join(tmpdir(), 'transit-schema-v2-'))
const screenshots = path.join(root, 'frontend/test-results/schema-v2')
await mkdir(screenshots, {recursive:true})
const python = path.join(root, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python')
const url = 'http://127.0.0.1:8766'
const server = spawn(python, ['main.py','web','--no-browser','--port','8766'], {
  cwd:root, env:{...process.env,MLR_STORAGE_DIR:path.join(temporary,'state'),MLR_DATASET_LIBRARY_DIR:path.join(temporary,'library')}, windowsHide:true,
})
let browser, page, logs = ''
server.stdout.on('data', data=>logs+=data)
server.stderr.on('data', data=>logs+=data)
const pause = ms=>new Promise(resolve=>setTimeout(resolve,ms))
async function until(check, description, timeout=60000) {
  const end=Date.now()+timeout
  while(Date.now()<end) {if(await check()) return; await pause(150)}
  throw new Error(`Timed out: ${description}`)
}
try {
  await until(async()=>{try{return(await fetch(url+'/api/health')).ok}catch{return false}}, 'server startup')
  const executable = process.env.PLAYWRIGHT_BROWSER_PATH || ['C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Google/Chrome/Application/chrome.exe'].find(existsSync)
  browser = await chromium.launch({headless:true,...(executable?{executablePath:executable}:{})})
  page = await browser.newPage({viewport:{width:1440,height:1000}, acceptDownloads:true})
  const errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  const dialog = ()=>page.getByRole('dialog').last()
  const close = async()=>{await dialog().getByRole('button',{name:'Close dialog'}).click();await until(async()=>await page.getByRole('dialog').count()===0,'dialog closes')}
  const current = ()=>page.locator('[data-workflow]:visible')
  const action = ()=>current().getByRole('button',{name:/^(Train & evaluate|Generate predictions)$/,exact:true})
  const navigate = async(name)=>{await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name,exact:true}).click()}
  const upload = async(file)=>{
    await current().getByLabel('Upload transportation dataset').setInputFiles(file)
    await current().locator('.dataset-file-card').getByText(path.basename(file),{exact:true}).waitFor()
    await until(async()=>await action().count()>0,'upload inspection finished')
  }
  const state = async()=>{
    const id=await page.evaluate(()=>localStorage.getItem('transit-experiment'))
    return (await page.request.get(url+'/api/experiments/'+id)).json()
  }
  const advanced = async()=>{const details=page.locator('.analysis-settings > details');if(await details.getAttribute('open')===null)await details.locator('summary').first().click()}
  const columns=['Record ID','Passenger Volume','Vehicle Frequency','Station / Stop','Time of Day','Day of Week','Month of Year','Actual Waiting Time','Transport Mode']
  const rows=Array.from({length:120},(_,i)=>[
    `QA-${i+1}`,i<5?5000:10+(i%29)*7,2+i%17,['A','B','C'][i%3],i%4>1?'Night':'Morning',
    i%5>2?'Tuesday':'Monday',i%7>3?'February':'January',8+(i%29)*.2+(i%17)*.15+(i%3)*.5,'Bus',
  ])
  const csv = values=>[columns,...values].map(row=>row.join(',')).join('\n')
  const training=path.join(temporary,'ARTIFICIAL_BUS_TEST.csv')
  const blank=path.join(temporary,'ARTIFICIAL_BLANK_TARGET_TEST.csv')
  await writeFile(training,csv(rows))
  await writeFile(blank,csv(rows.map(row=>row.map((v,i)=>i===7?'':v))))
  const libraryPath=path.join(temporary,'library')
  await mkdir(libraryPath,{recursive:true})
  await writeFile(path.join(libraryPath,'QA_BUS_SOURCE.csv'),csv(rows.map(row=>row.map((v,i)=>i===2||i===7?'':v))))
  await writeFile(path.join(libraryPath,'QA_TRAIN_SOURCE.csv'),csv(rows.map(row=>row.map((v,i)=>i===7?'':i===8?'Train':v))))
  await writeFile(path.join(libraryPath,'library.json'),JSON.stringify([
    {id:'qa-bus',title:'QA Bus source review',filename:'QA_BUS_SOURCE.csv',mode:'Bus',records:120,recordLabel:'artificial test rows',kind:'source_review'},
    {id:'qa-train',title:'QA Train predictors',filename:'QA_TRAIN_SOURCE.csv',mode:'Train',records:120,recordLabel:'artificial test rows',kind:'collected'},
  ]))
  await page.goto(url)
  await page.getByRole('heading',{name:'Model training',exact:true}).waitFor()
  await page.screenshot({path:path.join(screenshots,'training-empty.png'),fullPage:true})
  assert.equal(await page.getByText(/Predict unknown waiting time/).count(),0)
  await page.route('**/api/datasets/library',route=>route.fulfill({status:404,contentType:'application/json',body:JSON.stringify({detail:'API route not found.'})}))
  await page.getByRole('button',{name:'Dataset Library',exact:true}).click()
  await page.getByText(/This window is connected to an older server/).waitFor()
  assert.equal(await page.getByText('No datasets found',{exact:true}).count(),0)
  await page.getByText('Library unavailable',{exact:true}).waitFor()
  await close()
  await page.unroute('**/api/datasets/library')
  await page.getByRole('button',{name:'Dataset Library',exact:true}).click()
  await page.getByRole('button',{name:'Import QA Bus source review',exact:true}).click()
  await page.getByText('5/6 predictors complete',{exact:true}).waitFor()
  await until(async()=>await page.getByRole('dialog').count()===0,'bus library closes')
  assert.ok(await action().isDisabled())
  assert.equal(await page.getByLabel('Confirm prediction input availability').count(),0)
  await page.getByRole('button',{name:'Dataset Library',exact:true}).click()
  await page.getByRole('button',{name:'Import QA Train predictors',exact:true}).click()
  await page.getByText('6/6 predictors detected',{exact:true}).waitFor()
  await until(async()=>await page.getByRole('dialog').count()===0,'train library closes')
  assert.equal(await page.getByLabel('Prediction dataset mode').inputValue(),'train')
  await page.getByText(/No trained Train model is available for these six predictors/).waitFor()
  await page.getByLabel('Confirm prediction input availability').check()
  assert.ok(await action().isDisabled())
  assert.equal(await action().getAttribute('aria-describedby'),'model-block-reason')

  assert.ok(await action().isDisabled())
  assert.equal((await (await page.request.get(url+'/api/experiments')).json()).length,0)
  await upload(blank)
  await page.getByText('6/6 predictors detected',{exact:true}).waitFor()
  await page.getByLabel('Prediction dataset preview').waitFor()
  assert.ok(await action().isDisabled())
  assert.equal((await (await page.request.get(url+'/api/experiments')).json()).length,0)
  assert.equal(await current().locator('.accuracy-summary').count(),0)
  await page.screenshot({path:path.join(screenshots,'blank-target-preview.png'),fullPage:true})
  await navigate('Training')
  await upload(training)
  await page.getByText('6 predictors + recorded waiting time',{exact:true}).waitFor()
  await advanced()
  await page.getByRole('button',{name:'Research documentation',exact:true}).click()
  await dialog().getByLabel('Confirm recorded waiting times').check()
  await dialog().getByLabel('Confirm training input availability').check()
  await dialog().getByLabel('Data source type').selectOption('simulated')
  await dialog().getByLabel('Dataset source / reference').fill('ARTIFICIAL SOFTWARE TEST ONLY')
  await dialog().getByLabel('What does one row represent?').fill('Artificial Bus fixture; not recorded transport evidence.')
  await dialog().getByRole('button',{name:'Save research notes'}).click()
  await until(async()=>await page.getByRole('dialog').count()===0,'notes saved')
  await page.getByRole('button',{name:'Edit interaction terms'}).click()
  for(const candidate of ['Passenger Volume × Vehicle Frequency','Passenger Volume × Time of Day','Vehicle Frequency × Time of Day','Passenger Volume × Day of Week']) {
    assert.equal(await dialog().getByRole('checkbox',{name:candidate,exact:true}).count(),1)
  }
  await dialog().getByRole('checkbox',{name:'Passenger Volume × Time of Day',exact:true}).check()
  await dialog().getByRole('button',{name:'Approve selected interactions'}).click()
  await until(async()=>await page.getByRole('dialog').count()===0,'interactions saved')
  await action().click()
  if((await state()).flagged) {
    await page.getByRole('dialog').waitFor()
    const reason=dialog().locator('textarea').last()
    await reason.fill('Retain artificial extreme values to exercise the software review workflow.')
    await dialog().getByRole('button',{name:'Continue Analysis',exact:true}).click()
  }
  await until(async()=>['complete','error'].includes((await state()).status),'models complete')
  let saved=await state()
  assert.equal(saved.status,'complete',saved.error)
  await page.getByRole('button',{name:'View Details',exact:true}).waitFor()
  assert.equal(saved.config.schema_version,'station-calendar-v2')
  assert.equal(saved.config.classification_approved,false)
  assert.equal(saved.config.category_scoring,'automatic')
  assert.equal(Object.values(saved.distribution).reduce((a,b)=>a+b,0),saved.test)
  assert.deepEqual(saved.study_metrics.map(row=>row.Arm),['A','B','C'])
  assert.ok(saved.study_metrics.every(row=>row['Test Rows']===saved.test))
  for(let i=1;i<=3;i++) {
    await page.getByRole('button',{name:`View SOP ${i} evidence`,exact:true}).click()
    if(i===3) {
      const factors=dialog().getByRole('table',{name:'Classification factors'})
      await factors.waitFor()
      assert.equal(await factors.locator('tbody tr').count(),7)
      await dialog().screenshot({path:path.join(screenshots,'sop3-pending.png')})
    }
    await close()
  }
  // Blank targets reuse models, keep actual blank, and never acquire evaluation metrics.
  const before=JSON.stringify(saved.metrics)
  await upload(blank)
  await page.getByLabel('Confirm prediction input availability').check()
  await until(()=>action().isEnabled(),'compatible model selected')
  await action().click()
  await page.getByRole('table',{name:'Prediction-only results'}).waitFor()
  assert.equal(JSON.stringify((await state()).metrics),before)
  assert.equal(await current().locator('.accuracy-summary').count(),0)
  const downloadEvent=page.waitForEvent('download')
  await page.getByRole('button',{name:'Download all prediction results'}).click()
  const predictionCsv=await readFile(await (await downloadEvent).path(),'utf8')
  assert.match(predictionCsv,/Vehicle Frequency/)
  assert.ok(!predictionCsv.includes('Observed Vehicle Frequency'))
  assert.match(predictionCsv.split('\n')[1],/^"",/)
  assert.ok(!predictionCsv.includes('Error (actual'))
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}))
  await page.screenshot({path:path.join(screenshots,'predictions.png'),fullPage:true,animations:'disabled'})
  // Navigation keeps the prediction upload/result separate from training state.
  await navigate('Training')
  await current().locator('.dataset-file-card').getByText(path.basename(training),{exact:true}).waitFor()
  assert.equal(JSON.stringify((await state()).metrics),before)
  await navigate('Test & Predict')
  await current().getByRole('table',{name:'Prediction-only results'}).waitFor()
  await current().locator('.dataset-file-card').getByText(path.basename(blank),{exact:true}).waitFor()
  // A labeled upload on Prediction never silently trains or overwrites a model.
  const experimentCount=(await (await page.request.get(url+'/api/experiments')).json()).length
  await current().getByLabel('Upload transportation dataset').setInputFiles(training)
  await current().getByRole('alert').getByText(/This file contains recorded Actual Waiting Time/).waitFor()
  assert.equal((await (await page.request.get(url+'/api/experiments')).json()).length,experimentCount)
  assert.equal(JSON.stringify((await state()).metrics),before)
  await current().getByRole('button',{name:'Use the previous valid dataset'}).click()
  await action().click()
  await current().getByRole('table',{name:'Prediction-only results'}).waitFor()

  await page.setViewportSize({width:390,height:844})
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'mobile page fits viewport')
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}))
  await page.screenshot({path:path.join(screenshots,'mobile.png'),fullPage:true,animations:'disabled'})
  await page.setViewportSize({width:1440,height:1000})
  // Explicitly unknown stations are blocked rather than assigned a reference station's effect.
  const unseen=path.join(temporary,'UNSEEN_STATION.csv')
  await writeFile(unseen,csv(rows.slice(0,2).map(row=>row.map((v,i)=>i===3?'NEVER TRAINED':i===7?'':v))))
  await upload(unseen)
  await page.getByLabel('Confirm prediction input availability').check()
  await action().click()
  await page.getByRole('alert').getByText(/Unseen station/).first().waitFor()
  // A Train upload cannot use the fitted Bus model.
  const train=path.join(temporary,'TRAIN_INPUT.csv')
  await writeFile(train,csv(rows.slice(0,2).map(row=>row.map((v,i)=>i===8?'Train':i===7?'':v))))
  await upload(train)
  await page.getByLabel('Confirm prediction input availability').check()
  assert.ok(await action().isDisabled())
  await page.reload()
  await page.getByRole('heading',{name:'Test & predict',exact:true}).waitFor()
  assert.equal(await current().getByRole('table',{name:'Prediction-only results'}).count(),0)
  await navigate('Training')
  await page.getByRole('button',{name:'View Details',exact:true}).waitFor()
  assert.equal((await state()).id,saved.id)
  // Approving category mappings is independent from interaction approval.
  await advanced()
  await page.getByRole('button',{name:'Classification definitions',exact:true}).click()
  const categorySelects=dialog().locator('select[aria-label$=" severity"]')
  assert.ok(await categorySelects.count()>=9)
  for(let i=0;i<await categorySelects.count();i++) await categorySelects.nth(i).selectOption(String(i%4))
  await dialog().getByLabel('Classification approval rationale').fill('Artificial mapping test only; not an operational classification standard.')
  assert.ok(!await dialog().getByLabel('Approve revised classification').isChecked())
  await dialog().getByLabel('Approve revised classification').check()
  await dialog().getByRole('button',{name:'Save severity definitions'}).click()
  await until(async()=>await page.getByRole('dialog').count()===0,'classification saved')
  await action().click()
  await until(async()=>['complete','error'].includes((await state()).status),'approved classification analysis')
  saved=await state()
  assert.equal(saved.status,'complete',saved.error)
  assert.equal(saved.config.classification_approved,true)
  assert.equal(saved.distribution['Pending configuration']||0,0)
  await page.getByRole('button',{name:'View Details',exact:true}).waitFor()
  await until(()=>page.getByRole('button',{name:'View Predictions',exact:true}).isEnabled(),'training prediction row ready')
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}))
  await page.screenshot({path:path.join(screenshots,'training-results.png'),fullPage:true,animations:'disabled'})
  await page.getByRole('button',{name:'View SOP 3 evidence',exact:true}).click()
  await dialog().getByRole('table',{name:'Classification factors'}).waitFor()
  await dialog().screenshot({path:path.join(screenshots,'sop3-approved-test.png')})
  await close()
  const bundle=await page.request.get(`${url}/api/experiments/${saved.id}/download/excel`)
  assert.equal(bundle.status(),200)
  assert.equal(errors.length,0,errors.join('\n'))
  console.log('PASS: new schema preview, pending no-model state, separate training/prediction pages, preserved navigation state, wrong-page rejection, separate modes, declarations, interaction picker, IQR review, A/B/C evaluation, SOP 1-3, explicit category approval, blank-target inference, CSV export, unseen-station rejection, persistence, mobile layout. Artificial software tests only.')
} catch(error) {
  if(page) await page.screenshot({path:path.join(screenshots,'failure.png'),fullPage:true}).catch(()=>{})
  console.error(logs.slice(-5000))
  throw error
} finally {
  await browser?.close()
  server.kill()
}
