#!/usr/bin/env node
/**
 * screenshot_svgs.js - Screenshot SVG diagrams from HTML files using Puppeteer
 *
 * Usage: node screenshot_svgs.js <html-path> <output-dir>
 *
 * Output: JSON manifest to stdout with structure:
 * {
 *   "title": "Page title from .hero h1",
 *   "diagrams": [
 *     { "file": "diagram-0.png", "title": "Section Title", "width": 1100, "height": 530 }
 *   ]
 * }
 */

// Look for puppeteer in common locations
let puppeteer;
const searchPaths = [
  'puppeteer',
  require('path').join(require('os').homedir(), 'repos/dags/node_modules/puppeteer'),
];
for (const p of searchPaths) {
  try { puppeteer = require(p); break; } catch {}
}
if (!puppeteer) {
  console.error('Error: puppeteer not found. Install with: npm install puppeteer');
  process.exit(1);
}
const path = require('path');
const fs = require('fs');

async function main() {
  const [htmlPath, outputDir] = process.argv.slice(2);
  if (!htmlPath || !outputDir) {
    console.error('Usage: node screenshot_svgs.js <html-path> <output-dir>');
    process.exit(1);
  }

  const absHtml = path.resolve(htmlPath);
  const absOut = path.resolve(outputDir);
  fs.mkdirSync(absOut, { recursive: true });

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 900, deviceScaleFactor: 4 });
  await page.goto(`file://${absHtml}`, { waitUntil: 'networkidle0' });

  // Extract page title from .hero h1
  const heroTitle = await page.evaluate(() => {
    const h1 = document.querySelector('.hero h1');
    return h1 ? h1.textContent.trim() : document.title;
  });

  // Find all .diagram-wrap svg elements
  const diagramData = await page.evaluate(() => {
    const wraps = Array.from(document.querySelectorAll('.diagram-wrap'));
    return wraps.map((wrap, i) => {
      const svg = wrap.querySelector('svg');
      if (!svg) return null;

      // Find nearest preceding h2 for section title
      let el = wrap;
      let title = `Diagram ${i + 1}`;
      while (el) {
        el = el.previousElementSibling;
        if (el && el.tagName === 'H2') {
          // Get text without the <span> subtitle
          title = el.childNodes[0]?.textContent?.trim() || el.textContent.trim();
          break;
        }
      }
      // Also check parent containers
      if (title === `Diagram ${i + 1}`) {
        const section = wrap.closest('.section');
        if (section) {
          const h2 = section.querySelector('h2');
          if (h2) {
            title = h2.childNodes[0]?.textContent?.trim() || h2.textContent.trim();
          }
        }
      }

      const vb = svg.getAttribute('viewBox');
      const [, , w, h] = vb ? vb.split(/\s+/).map(Number) : [0, 0, 800, 600];

      return { index: i, title, svgWidth: w, svgHeight: h };
    }).filter(Boolean);
  });

  const manifest = { title: heroTitle, diagrams: [] };

  for (const d of diagramData) {
    const filename = `diagram-${d.index}.png`;
    const outPath = path.join(absOut, filename);

    // Screenshot the .diagram-wrap element (includes white background + padding)
    const wrapEl = (await page.$$('.diagram-wrap'))[d.index];
    if (wrapEl) {
      await wrapEl.screenshot({ path: outPath, type: 'png' });
    }

    manifest.diagrams.push({
      file: filename,
      title: d.title,
      width: d.svgWidth,
      height: d.svgHeight
    });
  }

  await browser.close();

  // Output manifest as JSON to stdout
  console.log(JSON.stringify(manifest, null, 2));
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
