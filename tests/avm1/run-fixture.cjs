// Genuine browser input is dispatched to Ruffle; no ActionScript handlers are called by this runner.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../../build/diagnostics/avm1-mouse');
const swf = process.argv[2] || 'fixture.swf';
const diagnostics = process.argv.includes('--diagnostics');
const boundary = process.argv.includes('--boundary');
const flow = process.argv.includes('--flow');
const reentry = process.argv.includes('--emulator-reentry');
const prefix = (swf === 'fixture.swf' ? '' : path.basename(swf, '.swf') + '-') + (flow ? (reentry ? 'flow-reentry-' : 'flow-') : boundary ? 'boundary-' : diagnostics ? 'probe-on-' : 'probe-off-');
const mime = {'.html':'text/html','.js':'text/javascript','.wasm':'application/wasm','.swf':'application/x-shockwave-flash'};
const server = http.createServer((req, res) => {
  const requested = decodeURIComponent(req.url.split('?')[0]);
  const file = path.resolve(root, '.' + (requested === '/' ? '/index.html' : requested));
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  fs.readFile(requested === '/' ? path.join(__dirname, 'index.html') : file, (err, bytes) => {
    if (err) { res.writeHead(404).end(String(err)); return; }
    res.writeHead(200, {'content-type':mime[path.extname(file)] || 'application/octet-stream'}).end(bytes);
  });
});
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({headless:true, channel:'msedge'});
    const page = await browser.newPage({viewport:{width:1280,height:720}});
    page.on('console', message => console.log(message.type() + ': ' + message.text()));
    page.on('pageerror', error => console.error('PAGE ERROR', error));
    await page.goto('http://127.0.0.1:' + server.address().port + '/?swf=' + encodeURIComponent(swf) + '&diagnostics=' + diagnostics + '&boundary=' + boundary + '&flow=' + flow);
    await page.waitForFunction(() => window.events.some(event => event.kind === 'ready'), null, {timeout:30000});
    if (flow) {
      await require('./run-interaction.cjs')(page, root, prefix, {reentry});
      return;
    }
    if (boundary) {
      const phaseResults = [];
      const state = () => page.evaluate(() => window.fixturePlayer.ruffle().callExternalInterface('boundarySnapshot'));
      const step = action => page.evaluate(action => window.fixturePlayer.ruffle().callExternalInterface('boundaryStep', action), action);
      const clickCanary = async phase => {
        const before = await state();
        await page.mouse.click(506, 288);
        await page.waitForTimeout(100);
        const after = await state();
        phaseResults.push({phase, addedPresses:after.presses - before.presses, after});
      };
      await clickCanary('beforeOpen');
      await step('open');
      await clickCanary('open');
      await step('repeatOpen');
      await clickCanary('repeatOpen');
      await page.mouse.move(220, 144);
      await page.waitForTimeout(100);
      await page.mouse.click(220, 144);
      await page.waitForTimeout(200);
      await page.screenshot({path:path.join(root,prefix + 'after-mcm-click.png')});
      await step('close');
      await clickCanary('close');
      await step('open');
      await step('endPage');
      await clickCanary('endPage');
      await step('open');
      await step('unload');
      await page.waitForTimeout(100);
      await clickCanary('unload');
      const events = await page.evaluate(() => window.events);
      const selected = events.filter(event => event.kind === 'modEvent' && event.data.name === 'SKICP_modSelected' && event.data.num === 1);
      // SkyUI does not hide the complete Journal or globally disable hit tests.
      // This injected canary is deliberately independent of SystemPage's input
      // flags, so it remains interactive. It is not a normal Journal control.
      const expectedPresses = [1, 1, 1, 1, 1, 1];
      const noBlanketIsolation = phaseResults.every(result => result.after.journalVisible && result.after.journalHitTestDisable !== true && !result.after.ownershipPresent);
      const pass = phaseResults.every((result, index) => result.addedPresses === expectedPresses[index]) && selected.length === 1 && noBlanketIsolation;
      fs.writeFileSync(path.join(root, prefix + 'events.json'), JSON.stringify({phaseResults,selectedXPMSE:selected.length,events}, null, 2));
      console.log('BOUNDARY RESULT', JSON.stringify({pass,selectedXPMSE:selected.length,noBlanketIsolation,phaseResults}));
      process.exitCode = pass ? 0 : 1;
      return;
    }
    await page.mouse.move(600, 650);
    await page.waitForTimeout(100);
    await page.mouse.move(220, 144);
    await page.waitForTimeout(200);
    await page.mouse.click(220, 144);
    await page.waitForTimeout(500);
    await page.screenshot({path:path.join(root,prefix + 'after-click.png')});
    if (diagnostics) {
      const installed = await page.evaluate(() => window.events.find(event => event.kind === 'probeInstalled')?.data);
      if (!installed?.present || !installed.listening || !installed.overlayPresent || installed.listenerReferences !== 1)
        throw new Error('Probe was not installed exactly once: ' + JSON.stringify(installed));
      const overlay = await page.evaluate(() => {
        const data = window.fixturePlayer.ruffle().callExternalInterface('probeSnapshot');
        window.recordAVM1('probeAfterClick', data);
        return data;
      });
      fs.writeFileSync(path.join(root, prefix + 'events.json'), JSON.stringify(await page.evaluate(() => window.events), null, 2));
      if (overlay.overlayText.split('\n').length !== 4 || overlay.textHeight > overlay.fieldHeight - 4 || overlay.textWidth > overlay.fieldWidth - 4)
        throw new Error('Diagnostic overlay clipped or not four lines: ' + JSON.stringify(overlay));
      const stopped = await page.evaluate(() => window.fixturePlayer.ruffle().callExternalInterface('stopDiagnostics'));
      if (!stopped?.stopped || stopped.listening || stopped.overlayPresent || stopped.listenerReferences !== 0)
        throw new Error('Probe did not detach cleanly: ' + JSON.stringify(stopped));
      await page.mouse.click(1260, 10);
      await page.waitForTimeout(100);
      const after = await page.evaluate(() => window.fixturePlayer.ruffle().callExternalInterface('probeSnapshot'));
      if (after.downs !== stopped.downs) throw new Error('Stopped probe still observed input');
    }
    const events = await page.evaluate(() => window.events);
    fs.writeFileSync(path.join(root, prefix + 'events.json'), JSON.stringify(events, null, 2));
    const selected = events.filter(event => event.kind === 'modEvent' && event.data.name === 'SKICP_modSelected' && event.data.num === 1);
    console.log('RESULT', JSON.stringify({selectedXPMSE:selected.length, diagnostics, rowPress:events.filter(event => event.kind === 'rowPress').length}));
    process.exitCode = selected.length === 1 ? 0 : 1;
  } finally { if(browser) await browser.close(); server.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
