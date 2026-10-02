// Exercise the place search on the live site and record what happens.
import { chromium } from 'playwright';
import fs from 'fs';
const b = await chromium.launch();
const log = [];
const QS = (process.env.QS || 'Sonora|Bend|Groveland, CA|Moab, Utah|98499|Xyzzyville').split('|');
for (const [q, vp] of QS.map((q, i) => [q, i % 2 ? 390 : 1440])) {
  const p = await b.newPage({ viewport: { width: vp, height: 900 } });
  p.on('pageerror', e => log.push(`${q} pageerror: ${e.message}`));
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') log.push(`${q} console: ${m.text()}`); });
  p.on('dialog', async d => { log.push(`${q} dialog: ${d.message()}`); await d.dismiss(); });
  p.on('requestfailed', r => log.push(`${q} reqfail: ${r.url().slice(0, 120)} ${r.failure()?.errorText}`));
  p.on('response', r => { if (r.status() >= 400) log.push(`${q} http ${r.status()}: ${r.url().slice(0, 140)}`); });
  await p.goto('https://brooksgroves.com/weather-station/?v=' + Date.now(), { waitUntil: 'networkidle' });
  await p.waitForTimeout(2000);
  await p.click('#q'); await p.keyboard.type(q, { delay: 60 }); await p.waitForTimeout(2500);
  log.push(`${q} suggestions: ` + JSON.stringify(await p.$$eval('#sugg li', l => l.map(x => x.textContent))) + ' visible=' + await p.isVisible('#sugg'));
  if (q === 'Sonora' && !process.env.QS) { await p.screenshot({ path: 'tools/shots/search-suggest.png' }); await p.click('#sugg li:nth-child(1)'); }
  else if (q === 'Bend' && !process.env.QS) { await p.click('.search button'); }
  else await p.press('#q', 'Enter');
  await p.waitForTimeout(9000);
  const info = await p.evaluate(() => ({ hash: location.hash, place: document.querySelector('.now .place')?.textContent, say: document.querySelector('#now')?.innerText.slice(0, 300), live: document.getElementById('live')?.textContent, msg: document.getElementById('smsg')?.hidden ? '' : document.getElementById('smsg')?.textContent, tabsScroll: document.getElementById('tabs').scrollLeft, obs: (typeof S !== 'undefined' && S.custom) ? S.custom.obs.map(id => id + ' ' + JSON.stringify(S.custom.obsInfo[id])) : null }));
  log.push(`${q} result: ${JSON.stringify(info)}`);
  await p.screenshot({ path: `tools/shots/search-${q.replace(/\W+/g, '_')}.png`, fullPage: false });
}
fs.writeFileSync('tools/shots/errors.txt', log.join('\n'));
await b.close();
