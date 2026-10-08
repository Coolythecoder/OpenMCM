// Executes the real compiled AVM1 panel and inspects its native TextFields.
// Provider input is fixture data; no input/HTML/formatting method is mocked.
const http = require('http');
const fs = require('fs');
const path = require('path');
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../build/diagnostics/avm1-mouse');
const swf = process.argv[2] || 'openmcm-api-v1.swf';
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
    const results = await page.evaluate(() => window.events.find(event => event.kind === 'openMCMApiResults').data);
    const artifact = path.join(root,prefix+'-results.json');
    fs.writeFileSync(artifact,JSON.stringify(results,null,2));
    assert.equal(results.checks.length,77,'All native API cases must execute');
    const failed = results.checks.filter(check => check.passed !== true);
    assert.deepEqual(failed,[],'Native API checks failed: '+failed.map(check=>check.name).join(', '));
    console.log(JSON.stringify({pass:true,checks:results.checks.length,artifact},null,2));
  } finally {if(browser) await browser.close();server.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
