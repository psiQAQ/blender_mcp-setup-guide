const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, executablePath, freshEvidence } = require('./browser_runtime.cjs');
const root = path.resolve(__dirname, '..');
const base = (process.env.PAGES_BASE_URL || 'https://notes.psiqaq.cn/blender_mcp-setup-guide').replace(/\/$/, '') + '/';
const site = process.env.PAGES_SITE || path.join(root, 'build/latest/site');
const channels = [
  ['release-blender-5-1-stable', 'blender-5.1/stable'],
  ['release-blender-5-2-preview', 'blender-5.2/preview'],
];

(async () => {
  const report = { status: 'Not Run', base_url: base, checks: [] };
  const reportPath = path.join(root, 'build/latest/public-browser-tests.json');
  if (fs.existsSync(reportPath) && JSON.parse(fs.readFileSync(reportPath)).status === 'Failed') {
    throw new Error('Preserve the previous Failed report and browser-public diagnostics before retrying');
  }
  const output = freshEvidence('browser-public');
  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    const records = {};
    const metadata = await browser.newContext();
    const metadataPage = await metadata.newPage();
    const metadataPaths = ['index.json', 'publication.json', ...channels.flatMap(([, channel]) =>
      ['index.json', 'publication.json'].map(name => channel + '/' + name))];
    report.metadata = [];
    for (const relative of metadataPaths) {
      const response = await metadataPage.goto(base + relative);
      assert.equal(response.status(), 200);
      const content = await response.body();
      assert.deepEqual(content, fs.readFileSync(path.join(site, relative)));
      const destination = path.join(output, 'metadata', relative);
      fs.mkdirSync(path.dirname(destination), { recursive: true });
      fs.writeFileSync(destination, content);
      report.metadata.push({ path: relative, canonical_bytes: 'Passed' });
    }
    for (const [id, channel] of channels) {
      records[id] = JSON.parse(fs.readFileSync(path.join(site, channel, 'publication.json')));
    }
    await metadata.close();
    for (const language of ['zh', 'en']) {
      for (const width of [1270, 390]) {
        const context = await browser.newContext({ viewport: { width, height: 884 }, permissions: ['clipboard-read', 'clipboard-write'] });
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.goto(base + (language === 'en' ? 'en/' : '') + 'index.html', { waitUntil: 'networkidle' });
        assert.equal(await page.locator('.mcp-tool-card[open]').count(), 0);
        for (const [id, channel] of channels) {
          const version = records[id].extension_version;
          await page.locator(`[data-channel="${id}"]`).click();
          const panel = page.locator('#' + id);
          assert.ok(await panel.isVisible());
          assert.ok((await panel.locator('.release-version').innerText()).includes(version));
          assert.equal(await panel.locator('.copy-field input').inputValue(), base + 'index.json');
          await panel.locator('[data-copy-target]').click();
          assert.equal(await page.evaluate(() => navigator.clipboard.readText()), base + 'index.json');
          const links = await panel.locator('.download-button').evaluateAll(nodes => nodes.map(node => node.href).sort());
          assert.deepEqual(links, Object.values(records[id].packages).map(item => item.archive_url).sort());
          assert.equal(await panel.locator(`.technical-details a[href="${base + channel}/index.json"]`).count(), 1);
          const hashes = await panel.locator('.checksums code').allTextContents();
          assert.deepEqual(hashes.sort(), Object.values(records[id].packages).map(item => item.sha256).sort());
          assert.equal(await panel.locator('.known-limitations a').count(), 2);
          report.checks.push({ language, width, channel, version, copy_index: 'Passed', downloads_and_hashes: 'Passed', known_limits: 'Passed' });
        }
        assert.deepEqual(errors, []);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        await page.locator('#downloads').scrollIntoViewIfNeeded();
        const header = await page.locator('.site-header').boundingBox();
        assert.ok(header.y >= 0 && header.y < 1);
        await page.screenshot({ path: path.join(output, `${language}-${width}.png`) });
        await context.close();
      }
      const context = await browser.newContext({ javaScriptEnabled: false });
      const page = await context.newPage();
      await page.goto(base + (language === 'en' ? 'en/' : '') + 'index.html');
      assert.equal(await page.locator('.download-button:visible').count(), 6);
      await context.close();
    }
    report.status = 'Passed';
  } catch (error) {
    report.status = 'Failed';
    report.error = error.stack;
    throw error;
  } finally {
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
    await browser.close();
  }
  console.log(JSON.stringify(report));
})().catch(error => { console.error(error); process.exitCode = 1; });
