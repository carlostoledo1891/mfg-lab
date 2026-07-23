/* test-byo-artifact.js — the gate that makes byo.html's "generated" claim real.
 *
 *   A1 the kernel is embedded BYTE-IDENTICAL to lab/mfg-byo.js;
 *   A2 the page is FRESH — rebuilding reproduces the committed bytes;
 *   A3 the BUNDLED kernel, evaluated as a browser would, reproduces the module's
 *      certified result exactly (byte-identity alone would miss a broken shim);
 *   A4 importing the builder does NOT write the artifact;
 *   A5 the page states its limits and overstates nothing.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..', '..');
const OUT = path.join(ROOT, 'mfg-lab', 'byo.html');
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.error('   FAIL  ' + m); } };

const html = fs.readFileSync(OUT, 'utf8');
console.log('== byo artifact gate ==');
console.log('   mfg-lab/byo.html  ' + html.length + ' bytes  sha256:' + sha(html).slice(0, 16));

/* A4 first: importing must not write. */
const before = sha(fs.readFileSync(OUT));
const builder = require(path.join(ROOT, 'mfg-lab', 'tools', 'build-byo.js'));
ok(before === sha(fs.readFileSync(OUT)), 'A4 requiring the builder does not rewrite the artifact');

/* A1 byte-identical kernel */
const src = fs.readFileSync(builder.KERNEL, 'utf8');
const open = '/*<<<BEGIN mfg-byo.js>>>*/\n', close = '\n/*<<<END mfg-byo.js>>>*/';
const i = html.indexOf(open), j = html.indexOf(close, i);
ok(i > 0 && j > i && html.slice(i + open.length, j) === src, 'A1 mfg-byo.js embedded byte-identical   [' + sha(src).slice(0, 16) + ']');

/* A2 freshness */
ok(builder.build() === html, 'A2 artifact is fresh (rebuild reproduces committed bytes)');

/* A3 bundled kernel reproduces the module */
const m = html.match(/window\.__mfgbyo = \(function\(\)\{[\s\S]*?\}\)\(\);/);
ok(!!m, 'A3a the bundled engine is locatable');
if (m) {
  const sandbox = { window: {}, document: undefined };
  vm.createContext(sandbox);
  vm.runInContext(m[0], sandbox, { filename: 'byo.html<engine>' });
  const B = sandbox.window.__mfgbyo;
  ok(B && typeof B.solve === 'function' && typeof B.verdictOf === 'function', 'A3b the bundle exposes solve + verdictOf');
  if (B) {
    const K = require(builder.KERNEL);
    const opts = { cost: m2 => 0.6 * Math.pow(Math.max(m2, 0), 1.5), terminal: x => 4 * (x - 0.8) ** 2, NX: 60, NT: 80, maxIter: 200 };
    const a = K.solve(opts), b = B.solve(opts);
    ok(a.verdict === b.verdict, 'A3c bundled solve reaches the same verdict');
    ok(a.exploitability === b.exploitability, 'A3d and the SAME exploitability, bit for bit');
    ok(B.verdictOf(true, 0.5).verdict === 'NOT_AN_EQUILIBRIUM', 'A3e the bundled verdict gate still refuses an exploitable fixed point');
  }
}

/* A5 prose */
const text = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
[/guaranteed to converge/i, /always an equilibrium/i, /solves any/i].forEach(re => ok(!re.test(text), 'A5 no overreach: ' + re));
[/nothing is uploaded/i, /byte-identity/i, /not an equilibrium/i].forEach(re => ok(re.test(text), 'A5 states its limits: ' + re));

console.log('   ' + pass + ' PASS, ' + fail + ' FAIL');
if (fail) { console.error('byo artifact gate FAILED'); process.exit(1); }
