// Use Archify's native dark SVG exporter on the checked final interactive HTML.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { pathToFileURL } = require('node:url');
const { chromium, executablePath, freshEvidence } = require('./browser_runtime.cjs');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'build/latest/evidence/diagram-export');

(async () => {
  freshEvidence('diagram-export');
  const browser = await chromium.launch({ executablePath, headless: true });
  const results = [];
  try {
    const page = await browser.newPage({ acceptDownloads: true });
    for (const mode of ['stdio', 'http']) for (const language of ['zh', 'en']) {
      const name = `${mode}.${language}`;
      await page.goto(pathToFileURL(path.join(root, 'web/diagrams', name + '.html')).href + '?theme=dark');
      await page.evaluate(async () => { await document.fonts.ready; await window.Archify.layoutStability.whenStable(); });
      await page.screenshot({ path: path.join(output, name + '.png'), fullPage: true });
      await page.locator('#btn-export').click();
      const download = page.waitForEvent('download');
      await page.getByRole('menuitem').filter({ hasText: /SVG · (深色|Dark)/i }).click();
      const target = path.join(root, 'web/diagrams', name + '.svg');
      await (await download).saveAs(target);
      results.push({ name, sha256: crypto.createHash('sha256').update(fs.readFileSync(target)).digest('hex') });
    }
    fs.writeFileSync(path.join(output, 'exports.json'), JSON.stringify(results, null, 2) + '\n');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
