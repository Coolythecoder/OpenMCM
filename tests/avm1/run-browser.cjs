// Native Ruffle AVM1 mouse/text entry against the compiled production classes.
// This is a portable regression fixture, not Skyrim/Scaleform verification.
const http = require('http');
const fs = require('fs');
const path = require('path');
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../build/diagnostics/avm1-mouse');
const swf = process.argv[2] || 'openmcm-browser.swf';
const prefix = path.basename(swf, '.swf');
const mime = {'.html':'text/html','.js':'text/javascript','.wasm':'application/wasm','.swf':'application/x-shockwave-flash'};
const server = http.createServer((req,res) => {
  const requested = decodeURIComponent(req.url.split('?')[0]);
  const file = requested === '/' ? path.join(__dirname,'index.html') : path.resolve(root,'.'+requested);
  if (requested !== '/' && !file.startsWith(root + path.sep)) {res.writeHead(403).end();return;}
  fs.readFile(file,(error,data) => {
    if(error) {res.writeHead(404).end(String(error));return;}
    res.writeHead(200,{'content-type':mime[path.extname(file)] || 'application/octet-stream'}).end(data);
  });
});
(async () => {
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  let browser;
  try {
    browser = await chromium.launch({headless:true,channel:'msedge'});
    const page = await browser.newPage({viewport:{width:1280,height:720}});
    await page.goto('http://127.0.0.1:'+server.address().port+'/?swf='+encodeURIComponent(swf));
    await page.waitForFunction(() => window.events.some(event => event.kind === 'ready'),null,{timeout:30000});
    const results = await page.evaluate(() => window.events.find(event => event.kind === 'browserChecks').data);
    assert.equal(results.checks.length,22);
    assert.deepEqual(results.checks.filter(check=>!check.passed),[]);
    const snapshot = () => page.evaluate(() => window.fixturePlayer.browserSnapshot());
    const wait = predicate => page.waitForFunction(predicate,null,{timeout:10000});
    // Hover selects the native row. The toolbar does not steal/reset its target.
    await page.mouse.move(280,144);
    await page.mouse.click(410,152);
    await page.mouse.click(495,120);
    await wait(() => window.fixturePlayer.browserSnapshot().names.length === 1);
    assert.equal((await snapshot()).names[0].name,'XPMSE');
    await page.mouse.click(517,152); // hide
    await wait(() => window.fixturePlayer.browserSnapshot().names.length === 0);
    await page.mouse.click(600,120); // hidden
    await wait(() => window.fixturePlayer.browserSnapshot().names.length === 1);
    assert.equal((await snapshot()).names[0].id,3);
    await page.mouse.click(517,152); // unhide
    await page.mouse.click(400,120); // all
    await page.mouse.click(900,120); // search
    await wait(() => window.fixturePlayer.browserSnapshot().action === 'search');
    await page.keyboard.type('alpha');
    await page.keyboard.press('Enter');
    await wait(() => window.fixturePlayer.browserSnapshot().state === 0);
    assert.deepEqual((await snapshot()).names.map(row=>row.name),['Alpha']);
    await page.mouse.click(1120,120); // clear must not collide with MovieClip.clear
    await wait(() => window.fixturePlayer.browserSnapshot().names.length === 3);
    await page.mouse.click(900,120);
    await wait(() => window.fixturePlayer.browserSnapshot().action === 'search');
    await page.keyboard.type('alpha');
    await page.keyboard.press('Enter');
    await wait(() => window.fixturePlayer.browserSnapshot().state === 0);
    assert.deepEqual((await snapshot()).names.map(row=>row.name),['Alpha']);
    const events = await page.evaluate(() => window.events);
    const providerTerminals = events.filter(event => event.kind==='modEvent' &&
      ['SKICP_inputAccepted','SKICP_menuAccepted','SKICP_dialogCanceled'].includes(event.data.name));
    assert.deepEqual(providerTerminals,[],'Browser dialogs must not wake provider setting callbacks');
    // Ruffle's display frame can trail synchronous ExternalInterface state.
    await page.waitForTimeout(150);
    await page.screenshot({path:path.join(root,prefix+'-browser.png')});
    await page.mouse.click(285,120); // select Alpha after filtering
    await wait(() => window.fixturePlayer.browserSnapshot().mode === 'pages');
    assert.equal((await snapshot()).selected,2);
    const artifact = path.join(root,prefix+'-results.json');
    fs.writeFileSync(artifact,JSON.stringify({checks:results.checks,nativeMouse:true,searchTextInput:true,
      noProviderDialogCallbacks:true,selectedRawID:2,events},null,2));
    console.log(JSON.stringify({pass:true,compiledChecks:results.checks.length,nativeMouse:true,searchTextInput:true,artifact},null,2));
  } finally {if(browser) await browser.close();server.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
