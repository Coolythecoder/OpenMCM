// Native AVM1 TextField snapshots; reads runtime fields, never substitutes the parser.
const http = require('http');
const fs = require('fs');
const path = require('path');
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../build/diagnostics/avm1-mouse');
const swf = process.argv[2] || 'text-format-standalone.swf';
const candidate = process.argv.find(argument => argument.startsWith('--candidate='))?.split('=')[1];
if(candidate && !['openParagraph','innerOpenParagraph','fontOnly'].includes(candidate))
  throw new Error('Unknown candidate diagnostic: '+candidate);
const prefix = path.basename(swf, '.swf')+(candidate ? '-'+candidate : '');
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
    await page.addInitScript(value => {window.textFormatCandidate = () => value;},candidate || '');
    page.on('pageerror', error => console.error(error));
    await page.goto('http://127.0.0.1:'+server.address().port+'/?swf='+encodeURIComponent(swf));
    await page.waitForFunction(() => window.events.some(event => event.kind === 'ready'),null,{timeout:30000});
    const results = await page.evaluate(() => window.events.find(event => event.kind === 'textFormatResults').data);
    fs.writeFileSync(path.join(root,prefix+'-formats.json'),JSON.stringify(results,null,2));
    await page.screenshot({path:path.join(root,prefix+'.png')});
    assert.equal(results.host,/host/.test(swf),'Expected host/standalone runtime');
    assert.equal(results.candidate,candidate || '','Unexpected candidate diagnostic mode');
    assert.equal(results.rows.length,candidate ? 32 : 80,'All native text cases must execute');
    if(!candidate) {
      assert.equal(results.rows.filter(row => row.mode==='production').length,8,'Production cases missing');
      assert.equal(results.rows.filter(row => row.mode==='plain').length,8,'Plain comparison cases missing');
      assert.equal(results.rows.filter(row => row.mode==='pooled').length,2,'Pooled cases missing');
      assert.equal(results.rows.filter(row => row.mode==='role').length,6,'Header/label/value roles missing');
      assert.equal(results.rows.filter(row => row.mode==='semantic').length,32,'Production semantic cases missing');
    }
    let assertedCharacters = 0;
    function verifySnapshot(name, actual, before, expectedText, overrides, embedded) {
      assert.equal(actual.text,expectedText,name+' native HTML parsing (including newline/entity semantics)');
      assert.deepEqual(actual.baseline,before.baseline,name+' next-assignment baseline changed');
      assert.equal(actual.embedFonts,embedded,name+' embedFonts changed');
      assert.equal(actual.runs.length,expectedText.length,name+' per-character snapshot length');
      for(let i=0;i<actual.runs.length;i++) {
        const expected={...before.baseline};
        for(const override of overrides) {
          if(i>=override.start && i<override.end) {
            for(const [key,value] of Object.entries(override)) {
              if(key!=='start' && key!=='end') expected[key]=value;
            }
          }
        }
        assert.equal(actual.runs[i].character,expectedText[i],name+' character '+i);
        for(const key of ['color','size','font','letterSpacing','kerning','align','leading','bold','italic','underline'])
          assert.equal(actual.runs[i].format[key],expected[key],name+' character '+i+' '+key);
        assertedCharacters++;
      }
    }
    const checkedModes = candidate ? [candidate] : ['plain','production','parsed','wrapper','pooled','role','semantic'];
    if(candidate) assert.equal(results.rows.filter(row => row.mode===candidate).length,32,'Candidate cases missing');
    const assertedRows = results.rows.filter(row => checkedModes.includes(row.mode));
    for (const row of assertedRows) {
      verifySnapshot(row.name,row.after,row.before,row.expectedText,row.expectedOverrides,row.embedded);
      if(row.nativeControl)
        assert.equal(row.after.text,row.nativeControl.text,row.name+' wrapper changed native paragraph/line-break output');
      if(row.mode === 'pooled') {
        assert.equal(row.sameField,true,'Pooled text field replaced');
        assert.equal(row.stages.length,2,'Pooled plain/HTML intermediate snapshots missing');
        for(const stage of row.stages)
          verifySnapshot(row.name+' '+stage.name,stage.after,row.before,stage.expectedText,stage.expectedOverrides,row.embedded);
      }
    }
    console.log(JSON.stringify({host:results.host,candidate,constructor:results.constructor,
      executedRows:results.rows.length,assertedRows:assertedRows.length,
      assertedCharacters,pass:true,artifact:path.join(root,prefix+'-formats.json')},null,2));
  } finally {if(browser) await browser.close();server.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
