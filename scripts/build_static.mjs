// Package the already-verified report for static hosting. No Python build required.
import { readFile, writeFile, mkdir, copyFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(root, 'dist');
const reportPath = 'reports/retail_analysis.html';
const report = await readFile(path.join(root, reportPath), 'utf8');
const validation = JSON.parse(await readFile(path.join(root, 'outputs/validation.json'), 'utf8'));
if (validation.status !== 'passed') throw new Error('Analysis validation must pass before deployment.');
const files = new Set([reportPath, 'assets/fonts/OFL.txt']);
const targets = [...report.matchAll(/href="([^"]+)"/g)].map(match => match[1]);
for (const href of targets) {
  if (href.startsWith('#') || /^(https?:|mailto:)/.test(href)) continue;
  const relative = path.posix.normalize(path.posix.join('reports', href.split('#')[0]));
  if (!/^(docs|outputs|powerbi|reports)\//.test(relative) || relative.includes('..')) {
    throw new Error(`Unexpected public report link: ${href}`);
  }
  await stat(path.join(root, relative));
  files.add(relative);
}
await mkdir(output, { recursive: true });
for (const relative of files) {
  const destination = path.join(output, relative);
  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(path.join(root, relative), destination);
}
// The original relative links also resolve correctly from the domain root.
const description = 'Retail sales and customer analytics: sales trends, customer behavior, returns, and data quality across 1.59 million records.';
const homepage = report.replace('</head>', `<meta name="description" content="${description}"><meta property="og:title" content="Retail Sales &amp; Customer Analytics"><meta property="og:description" content="${description}"><meta property="og:type" content="website"></head>`);
await writeFile(path.join(output, 'index.html'), homepage);
await writeFile(path.join(output, '404.html'), '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found</title><body style="font-family:system-ui;max-width:650px;margin:80px auto;padding:24px"><h1>Page not found</h1><p><a href="/">Return to the retail analysis report</a></p></body></html>');
let bytes = Buffer.byteLength(homepage);
for (const file of files) bytes += (await stat(path.join(output, file))).size;
console.log(`Static report ready: ${files.size + 2} files, ${(bytes / 1024 / 1024).toFixed(2)} MB.`);
console.log('Verified all local report links. Output: dist/');
