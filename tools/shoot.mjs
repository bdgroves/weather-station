// Screenshots of the live site, run in Actions (real network: tiles, CDN scripts).
import { chromium } from 'playwright';
import fs from 'fs';
const b = await chromium.launch();
const errs = [];
for (const [name, vp, hash] of [['desk', { width: 1440, height: 900 }, ''], ['phone', { width: 390, height: 844 }, ''], ['sonora', { width: 1440, height: 900 }, 'sonora'], ['dv-phone', { width: 390, height: 844 }, 'death-valley']]) {
  const p = await b.newPage({ viewport: vp });
  p.on('pageerror', e => errs.push(`${name}: ${e.message}`));
  p.on('console', m => { if (m.type() === 'error') errs.push(`${name} console: ${m.text()}`); });
  await p.goto('https://brooksgroves.com/weather-station/?v=' + Date.now() + '#' + hash, { waitUntil: 'networkidle' });
  await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } window.scrollTo(0, 0); });
  await p.waitForTimeout(3000);
  errs.push(`${name} status: ` + await p.evaluate(() => (document.getElementById('live')?.textContent || '?') + ' | ' + (document.getElementById('live-sub')?.textContent || '')));
  await p.screenshot({ path: `tools/shots/${name}.png`, fullPage: true });
  const rd = await p.$('#radar-sec'); if (rd) { await rd.scrollIntoViewIfNeeded(); await p.waitForTimeout(4000); await p.click('#r-play'); await p.$eval('#r-slide', e => { e.value = 11; e.dispatchEvent(new Event('input')); }); await p.waitForTimeout(2500); await rd.screenshot({ path: `tools/shots/${name}-radar.png` }); }
  const fz = await p.$('#freeze'); if (fz) { const g = await fz.evaluateHandle(e => e.closest('.g3')); await g.asElement().screenshot({ path: `tools/shots/${name}-freeze.png` }); errs.push(`${name} freeze: ` + (await fz.innerText()).replace(/\s+/g, ' ')); }
  errs.push(`${name} radar: ` + await p.evaluate(() => document.getElementById('r-time')?.textContent + ' tiles loaded: ' + [...document.querySelectorAll('#radar img.leaflet-tile-loaded')].length));
  const v = await p.$('#v-sec'); if (v) await v.screenshot({ path: `tools/shots/${name}-verify.png` });
  errs.push(`${name} verify: ` + await p.evaluate(() => document.getElementById('v-say')?.innerText || ''));
}
fs.writeFileSync('tools/shots/errors.txt', errs.join('\n'));
await b.close();
