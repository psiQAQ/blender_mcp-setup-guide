const path = require('node:path');
const fs = require('node:fs');
const installed = process.env.PLAYWRIGHT_MODULE || path.join(process.env.USERPROFILE || process.env.HOME,
  '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { chromium } = require(installed);
const executablePath = process.env.BROWSER_BINARY || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
if (!fs.existsSync(executablePath)) throw new Error('Set BROWSER_BINARY to an installed Chromium browser');
function freshEvidence(name) {
  if (!/^[a-z-]+$/.test(name)) throw new Error('Invalid evidence directory');
  const build = path.resolve(__dirname, '../build');
  const output = path.resolve(build, 'latest/evidence', name);
  if (!output.startsWith(build + path.sep)) throw new Error('Evidence target is outside build');
  for (let current = output; current !== build; current = path.dirname(current)) {
    if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) throw new Error('Evidence directory contains a link');
  }
  fs.rmSync(output, { recursive: true, force: true });
  fs.mkdirSync(output, { recursive: true });
  return output;
}
module.exports = { chromium, executablePath, freshEvidence };
