// Radar section for a searched place (default: Lawton, OK, where showers were about), for the blog.
import { chromium } from 'playwright';
import fs from 'fs';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const log = [];
p.on('pageerror', e => log.push('pageerror: ' + e.message));
await p.goto('https://brooksgroves.com/weather-station/?v=' + Date.now() + '#' + (process.env.QS || '@34.609,-98.390,Lawton,OK'), { waitUntil: 'networkidle' });
await p.waitForTimeout(3000);
const rd = await p.$('#radar-sec'); await rd.scrollIntoViewIfNeeded(); await p.waitForTimeout(6000);
await p.click('#r-play'); await p.$eval('#r-slide', e => { e.value = 11; e.dispatchEvent(new Event('input')); }); await p.waitForTimeout(3000);
await rd.screenshot({ path: 'tools/shots/radar-place.png' });
log.push(await p.evaluate(() => document.getElementById('r-time').textContent + ' tiles ' + document.querySelectorAll('#radar img.leaflet-tile-loaded').length));
fs.writeFileSync('tools/shots/errors.txt', log.join('\n'));
await b.close();
