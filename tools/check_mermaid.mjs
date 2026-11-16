// Parses every Mermaid diagram of the repository's Markdown files. No browser is needed.
// Usage: node tools/check_mermaid.mjs   (after tools/setup.sh)
import { JSDOM } from 'jsdom';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dom = new JSDOM('<!doctype html><body></body>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
try { Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true }); } catch (e) {}
const mermaid = (await import('mermaid')).default;
mermaid.initialize({ startOnLoad: false });

const skip = new Set(['.git', 'node_modules', '.venv']);
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) =>
  skip.has(e.name) ? [] : e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);

let n = 0, bad = 0;
for (const f of walk(root).filter((f) => f.endsWith('.md') || f.endsWith('.mdx'))) {
  const s = fs.readFileSync(f, 'utf8');
  for (const m of s.matchAll(/```mermaid\n([\s\S]*?)```/g)) {
    n++;
    try { await mermaid.parse(m[1]); }
    catch (e) { bad++; console.log('BAD DIAGRAM', path.relative(root, f), String(e.message).slice(0, 200)); }
  }
}
console.log('diagrams:', n, 'bad:', bad);
process.exit(bad ? 1 : 0);
