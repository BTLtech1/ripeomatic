// Smoke test of firmware/ui/index.html in headless Chromium against tools/mock_device.py.
//   python3 tools/mock_device.py &   then   node firmware/test/ui_smoke.js [screenshot-dir]
// Fails (exit 1) on any console error, failed request, or if the page doesn't reach the expected states.
const { chromium } = require('playwright');
const shots = process.argv[2] || require('os').tmpdir();
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.type() + ': ' + m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('requestfailed', r => errors.push('reqfail: ' + r.url()));

  await page.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
  await page.waitForFunction(() => document.getElementById('pill').textContent !== '…', null, { timeout: 5000 });
  const out = {};
  out.sub = await page.textContent('#sub');
  out.pill = await page.textContent('#pill');
  out.verdict0 = await page.textContent('#verdict');
  out.msg0 = await page.textContent('#msg');
  out.calwarn = await page.isVisible('#calwarn');
  out.settingsInputs = await page.locator('#settings input, #settings select').count();
  out.chart0 = await page.textContent('#chart');

  // first-run checklist: walk every step on the mock
  await page.waitForSelector('#setup:not([hidden])', { timeout: 5000 });
  out.setup0 = await page.textContent('#setupcount');
  const step = async (act, after) => { await page.click(`#steps button[data-act="${act}"]`); await page.waitForTimeout(after || 400); };
  await step('ntfynew', 600);
  out.topicLink = await page.getAttribute('#steps a[href^="https://ntfy.sh/"]', 'href');
  await page.fill('#discordurl', 'https://discord.com/api/webhooks/123/abc');
  await step('discordsave', 600);
  out.discordSaved = /Webhook saved/.test(await page.textContent('#steps'));
  await step('ntfytest', 200);
  await page.waitForFunction(() => /Alerts · working · phone · Discord/.test(document.getElementById('steps').textContent), null, { timeout: 8000 });
  await step('nudge', 3500);
  await step('motorbad', 500);
  out.flipped = /currently flipped/.test(await page.textContent('#steps'));
  await step('nudge', 3500);
  await step('motorok', 500);
  await step('jog', 3500);
  await step('sethome', 500);
  out.homeSet = /Set home · set/.test(await page.textContent('#steps'));
  await step('zero', 500);
  await page.fill('#grams', '100');
  await step('mass', 500);
  await page.fill('#grams', '200');
  await step('mass', 500);
  page.once('dialog', dlg => dlg.accept());
  await step('blade', 500);
  await page.waitForFunction(() => /Blade calibration · /.test(document.getElementById('steps').textContent) && !document.querySelector('#steps .sstep:nth-child(5):not(.done)'), null, { timeout: 30000 });
  out.setup4 = await page.textContent('#setupcount');
  await step('measure', 500);
  await page.waitForFunction(() => document.getElementById('setup').hidden, null, { timeout: 30000 });
  out.setupDone = true;

  // firmware update check
  await page.click('#d-wifi summary');
  await page.click('#btnUpdCheck');
  await page.waitForFunction(() => /newer build is available/.test(document.getElementById('updmsg').textContent) && !document.getElementById('btnUpd').hidden, null, { timeout: 8000 });
  out.updCheck = await page.textContent('#updmsg');
  out.fwinfo = await page.textContent('#fwinfo');

  // sensor test
  await page.click('#d-sensor summary');
  await page.click('#btnSensor');
  await page.waitForFunction(() => /Working/.test(document.getElementById('sstate').textContent), null, { timeout: 10000 });
  out.sensorTest = await page.textContent('#sstate');
  await page.click('#btnSensor');
  out.sensorStopped = await page.isHidden('#sensorbox');

  // measure
  await page.click('#btnMeasure');
  await page.waitForFunction(() => !document.getElementById('live').hidden, null, { timeout: 5000 });
  out.liveTxt = await page.textContent('#livetxt');
  await page.waitForFunction(() => document.getElementById('live').hidden && document.getElementById('verdict').textContent !== '—', null, { timeout: 30000 });
  out.verdict1 = await page.textContent('#verdict');
  out.kval = await page.textContent('#kval');
  out.meta = await page.textContent('#meta');
  await page.waitForFunction(() => document.querySelectorAll('#chart circle').length > 0, null, { timeout: 8000 });
  out.trendPoints = await page.locator('#chart circle').count();
  out.chartNote = await page.textContent('#chartnote');
  await page.screenshot({ path: shots + '/ui_trend.png', fullPage: true });

  // last press tab
  await page.click('.tabs button[data-tab="curve"]');
  await page.waitForFunction(() => document.querySelectorAll('#chart path.cv').length > 0, null, { timeout: 5000 });
  out.curveNote = await page.textContent('#chartnote');

  // rate
  await page.click('#rate button[data-r="firm"]');
  await page.waitForFunction(() => document.querySelector('#rate button[data-r="firm"]').classList.contains('on'), null, { timeout: 8000 });
  out.rated = await page.textContent('#meta');

  // settings save round trip
  await page.click('#d-set summary');
  await page.fill('#settings input[name="interval_h"]', '8');
  await page.click('#btnSave');
  await page.waitForTimeout(800);
  out.toast = await page.textContent('#toast');
  const st = await (await page.request.get('http://localhost:8080/api/settings')).json();
  out.savedInterval = st.interval_h;

  // wifi panel scan
  await page.click('#d-wifi summary');
  await page.waitForFunction(() => document.querySelectorAll('#ssid option').length > 1, null, { timeout: 5000 });
  out.ssidOptions = await page.locator('#ssid option').count();
  await page.screenshot({ path: shots + '/ui_panels.png', fullPage: true });

  // second measurement -> two points
  await page.click('#btnMeasure');
  await page.waitForFunction(() => !document.getElementById('live').hidden, null, { timeout: 5000 });
  await page.waitForFunction(() => document.getElementById('live').hidden, null, { timeout: 30000 });
  await page.click('.tabs button[data-tab="trend"]');
  await page.waitForFunction(() => document.querySelectorAll('#chart circle').length >= 2, null, { timeout: 8000 });
  out.trendPoints2 = await page.locator('#chart circle').count();
  out.meta2 = await page.textContent('#meta');

  out.errors = errors;
  console.log(JSON.stringify(out, null, 1));
  await browser.close();
  const problems = [];
  if (errors.length) problems.push('console/network errors');
  if (!/N\/mm/.test(out.kval) || out.kval.startsWith('—')) problems.push('no stiffness shown after measuring');
  if (out.trendPoints2 < 2) problems.push('trend chart has fewer than 2 points');
  if (!/newer build/.test(out.updCheck || '')) problems.push('update check');
  if (!out.sensorStopped || !/Working/.test(out.sensorTest || '')) problems.push('sensor test');
  if (!out.setupDone || !out.flipped || !out.homeSet || !out.topicLink || !out.discordSaved) problems.push('setup checklist did not complete');
  if (out.savedInterval !== 8) problems.push('settings round trip failed');
  if (!/you said: firm/.test(out.rated)) problems.push('rating not reflected');
  if (problems.length) { console.error('SMOKE TEST FAILED: ' + problems.join('; ')); process.exit(1); }
  console.log('smoke test passed');
})().catch(e => { console.error('TEST FAILED', e); process.exit(1); });
