// Browser checks adapted from the validated frame-top and collapsed-tools scripts.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium, executablePath, freshEvidence } = require('./browser_runtime.cjs');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'build/latest/evidence/browser');
const index = 'https://notes.psiqaq.cn/blender_mcp-setup-guide/index.json';

(async () => {
  freshEvidence('browser');
  const server = spawn(process.env.TEST_PYTHON || 'python', ['-B', path.join(__dirname, 'preview_server.py')], { cwd: root, windowsHide: true });
  let browser;
  const report = { status: 'Not Run', checks: [] };
  try {
    const base = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Preview server startup timed out')), 15000);
      server.stdout.once('data', data => { clearTimeout(timer); resolve(data.toString().trim()); });
      server.once('exit', code => { clearTimeout(timer); reject(new Error('Preview server exited: ' + code)); });
      server.once('error', reject);
    });
    browser = await chromium.launch({ executablePath, headless: true });
    for (const language of ['zh', 'en']) {
      for (const width of [1270, 390]) {
        const context = await browser.newContext({ viewport: { width, height: 884 }, permissions: ['clipboard-read', 'clipboard-write'] });
        const page = await context.newPage();
        await page.goto(base + (language === 'en' ? 'en/' : '') + 'index.html', { waitUntil: 'networkidle' });
        assert.equal(await page.locator('.mcp-tool-card[open]').count(), 0);
        for (const version of ['release-blender-5-1-stable', 'release-blender-5-2-preview']) {
          await page.locator(`[data-channel="${version}"]`).click();
          const panel = page.locator('#' + version);
          assert.ok(await panel.isVisible());
          assert.equal(await panel.locator('.copy-field input').inputValue(), index);
          await panel.locator('[data-copy-target]').click();
          assert.equal(await page.evaluate(() => navigator.clipboard.readText()), index);
          assert.equal(await panel.locator('.technical-details a[href$="/index.json"]').count(), 1);
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        await page.locator('#mcp-tools-heading').scrollIntoViewIfNeeded();
        const header = await page.locator('.site-header').boundingBox();
        assert.ok(header.y >= 0 && header.y < 1);
        await page.screenshot({ path: path.join(output, `${language}-${width}.png`) });
        report.checks.push({ language, width, index_copy: 'Passed', channel_switch: 'Passed', mobile_layout: 'Passed', sticky_header: 'Passed' });
        await context.close();
      }
      const context = await browser.newContext({ javaScriptEnabled: false });
      const page = await context.newPage();
      await page.goto(base + (language === 'en' ? 'en/' : '') + 'index.html');
      assert.equal(await page.locator('.download-button:visible').count(), 6);
      await context.close();
    }
    report.status = 'Passed';
  } catch (error) { report.status = 'Failed'; report.error = error.stack; throw error; }
  finally {
    fs.writeFileSync(path.join(root, 'build/latest/browser-tests.json'), JSON.stringify(report, null, 2) + '\n');
    if (browser) await browser.close();
    server.kill();
    await new Promise(resolve => server.exitCode !== null ? resolve() : server.once('exit', resolve));
  }
  console.log(JSON.stringify(report));
})().catch(error => { console.error(error); process.exitCode = 1; });
