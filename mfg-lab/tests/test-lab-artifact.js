/* test-lab-artifact.js — the gate that makes "generated" mean something.

   mfg-lab/lab.html embeds four modules and runs them in the reader's browser.
   Without this file, "the page runs the same code the batteries validate" is a
   sentence in a footer. With it, the sentence is checked:

     A1  every embedded module is BYTE-IDENTICAL to its source on disk;
     A2  the page is FRESH — rebuilding reproduces the committed bytes exactly;
     A3  the BUNDLED engine, evaluated as the browser would, reproduces the
         module's own result exactly. Byte-identity alone would not catch a
         wrapper that broke `require` or dropped an export;
     A4  the verdict rule is driven with ADVERSARIAL certificates. A page in
         this repo once shipped a verdict that survived being mutated to ignore
         its inputs, because nothing could feed it a bad one;
     A5  the page states what it may not overstate — a sampled box is not a
         proved box, and the phrasing is asserted rather than trusted;
     A6  importing the builder does NOT write the artifact. A freshness gate
         whose builder writes on import silently repairs the staleness it
         exists to detect, and this repository shipped exactly that bug once.
*/
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..', '..');
const OUT = path.join(ROOT, 'mfg-lab', 'lab.html');

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.error('   FAIL  ' + m); } };
const sha = b => crypto.createHash('sha256').update(b).digest('hex');

console.log('== lab artifact gate ==');
const html = fs.readFileSync(OUT, 'utf8');
console.log('   ' + path.relative(ROOT, OUT) + '  ' + html.length + ' bytes  sha256:' + sha(html).slice(0, 16));

/* ---------------------------------------- A6 first: importing must not write */
const before = sha(fs.readFileSync(OUT));
const builder = require(path.join(ROOT, 'mfg-lab', 'tools', 'build-lab.js'));
const after = sha(fs.readFileSync(OUT));
ok(before === after, 'A6 requiring the builder does not rewrite the artifact (a gate that repairs what it checks is not a gate)');

/* ------------------------------------------------ A1 byte-identical modules */
for (const [name, file] of builder.MODULES) {
  const src = fs.readFileSync(file, 'utf8');
  const open = '/*<<<BEGIN ' + name + '>>>*/\n';
  const close = '\n/*<<<END ' + name + '>>>*/';
  const i = html.indexOf(open), j = html.indexOf(close, i);
  if (i < 0 || j < 0) { ok(false, 'A1 ' + name + ' is not embedded at all'); continue; }
  const embedded = html.slice(i + open.length, j);
  ok(embedded === src, 'A1 ' + name + ' embedded byte-identical   [' + sha(src).slice(0, 16) + ']');
}

/* ---------------------------------------------------------- A2 freshness */
ok(builder.build() === html, 'A2 artifact is fresh with respect to the modules and the template   [rebuild reproduces the committed bytes]');

/* ------------------------------ A3 the BUNDLED engine reproduces the modules */
const m = html.match(/<script>\s*(\/\* ── GENERATED[\s\S]*?)<\/script>/);
ok(!!m, 'A3a the engine script is locatable in the page');
if (m) {
  const sandbox = { window: {}, console };
  vm.createContext(sandbox);
  vm.runInContext(m[1], sandbox, { filename: 'lab.html<engine>' });
  const LAB = sandbox.window.__lab;
  ok(LAB && typeof LAB.study === 'function' && typeof LAB.map === 'function',
     'A3b the bundle exposes both instruments (a broken require would surface here, not in a user\'s browser)');

  if (LAB) {
    const F = require('./lab-fixtures.js');
    const { study } = require('../lab/order-study.js');
    const { map } = require('../lab/failure-map.js');

    const direct = study(F.poisson1d, { tol: 1e-9, levels: [16, 32, 64] });
    const bundled = LAB.study(F.poisson1d, { tol: 1e-9, levels: [16, 32, 64] });
    ok(bundled.code === direct.code, 'A3c bundled study reaches the same verdict code as the module');
    ok(bundled.order[0] === direct.order[0] && bundled.order[1] === direct.order[1],
       'A3d and the SAME order interval, bit for bit — not merely a close one');
    ok(bundled.table.every((t, i) => t.error === direct.table[i].error),
       'A3e and the same error at every level');

    const dm = map(F.helmholtz1d, { sweep: { k: [0.5, 6] }, samples: 12, n: 32, tol: 1e-6 });
    const bm = LAB.map(F.helmholtz1d, { sweep: { k: [0.5, 6] }, samples: 12, n: 32, tol: 1e-6 });
    ok(bm.code === dm.code && JSON.stringify(bm.counts) === JSON.stringify(dm.counts),
       'A3f bundled failure map classifies identically');
    ok(JSON.stringify(bm.brackets) === JSON.stringify(dm.brackets), 'A3g and brackets the same transition');

    /* The certificate discipline must survive bundling too. */
    let threw = false;
    try { new LAB.Certificate({ claim: 'x', verdict: 'PROVED', evidence: { a: 1 } }); } catch (e) { threw = true; }
    ok(threw, 'A3h the bundled Certificate still refuses to exist without a falsifier');
  }
}

/* ------------------------------------- A4 the verdict rule, fed bad input */
const vm4 = html.match(/function verdictClass\(cert\)\{[\s\S]*?\n\}/);
ok(!!vm4, 'A4a the verdict rule is extractable — if this fails the rule moved and the checks below are testing nothing');
if (vm4) {
  const verdictClass = new Function('return (' + vm4[0].replace(/^function/, 'function') + ')')();
  ok(verdictClass({ verdict: 'PROVED' }) === 'ok', 'A4b PROVED renders as certified');
  ok(verdictClass({ verdict: 'REFUSED' }) === 'no', 'A4c REFUSED renders as NOT proved');
  ok(verdictClass({ verdict: 'NOT_CHECKED' }) === 'no', 'A4d NOT_CHECKED is not styled as a pass');
  ok(verdictClass({ verdict: 'proved' }) === 'no', 'A4e a lowercase near-miss is not styled as a pass');
  ok(verdictClass({}) === 'no' && verdictClass(null) === 'no' && verdictClass({ verdict: 42 }) === 'no',
     'A4f garbage fails closed — an absent or malformed verdict never renders as certified');
}

/* --------------------------------------------- A5 what the page may not say */
const text = html.replace(/<[^>]+>/g, ' ');
const FORBIDDEN = [
  /proves the box/i,
  /guaranteed to converge/i,
  /always converges/i,
  /consistency floor/i
];
FORBIDDEN.forEach(re => ok(!re.test(text), 'A5 the page does not overstate: ' + re));
const REQUIRED = [
  /cannot exist without a falsifier/i,
  /nothing is uploaded/i,
  /byte-identical/i
];
REQUIRED.forEach(re => ok(re.test(text), 'A5 the page states its own limits: ' + re));
ok(/sampled, not proved|SAMPLED/.test(html),
   'A5 the sampling disclaimer reaches the page (the map samples; it never proves a box)');

console.log('   ' + pass + ' PASS, ' + fail + ' FAIL');
if (fail) { console.error('lab artifact gate FAILED'); process.exit(1); }
