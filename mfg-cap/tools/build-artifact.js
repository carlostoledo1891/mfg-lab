/* build-artifact.js — GENERATE mfg-cap.html from the kernels.

   The page must not contain a second copy of the mathematics. It is assembled
   here by splicing kernel/interval.js, kernel/mfg1d.js and kernel/validate.js
   verbatim into a template, each between markers, with tiny module shims so the
   CommonJS files run unchanged in a browser. tests/test-artifact.js then asserts
   byte-identity between the spliced regions and the kernel files, so the page
   and the battery can never diverge: what you prove in the browser is what
   `make check` proved.

   Run: node tools/build-artifact.js        MIT licensed. Part of mfg-cap. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..');
const K = f => fs.readFileSync(path.join(ROOT, 'kernel', f), 'utf8');
const sha = s => crypto.createHash('sha256').update(s).digest('hex').slice(0, 16);

/* interval arithmetic is SHARED: kernel/interval.js is a one-line re-export of
   eqcert, and a require() of a sibling path means nothing in a browser. So the
   page embeds eqcert's actual source, read from the toolkit and nowhere else.
   There is deliberately NO vendored fallback: mfg-cap ships inside the same
   repo as eqcert, so a second copy on disk would buy nothing and could drift —
   the failure eqcert/tests/test-single-source.js exists to prevent. */
const EQ = path.join(ROOT, '..', 'eqcert', 'src', 'interval.js');
const interval = fs.readFileSync(EQ, 'utf8');
const mfg1d = K('mfg1d.js');
const validate = K('validate.js');

const B = n => `/* ==== BEGIN VERBATIM ${n} ==== */\n`;
const E = n => `/* ==== END VERBATIM ${n} ==== */`;

/* CommonJS shim: each kernel is wrapped so `require` resolves to its siblings. */
const bundle = `
/* The three kernel files below are spliced VERBATIM by tools/build-artifact.js.
   Do not edit them here — edit kernel/*.js and rebuild; tests/test-artifact.js
   asserts byte-identity and will go red if these copies drift. */
const __mods = {};
function __def(name, fn) {
  const module = { exports: {} };
  const require = n => __mods[n.replace('./', '').replace('.js', '')];
  fn(module, require);
  __mods[name] = module.exports;
}
__def('interval', function (module, require) {
${B('eqcert/src/interval.js')}${interval}${E('eqcert/src/interval.js')}
});
__def('mfg1d', function (module, require) {
${B('kernel/mfg1d.js')}${mfg1d}${E('kernel/mfg1d.js')}
});
__def('validate', function (module, require) {
${B('kernel/validate.js')}${validate}${E('kernel/validate.js')}
});
const IV = __mods.interval, MFG = __mods.mfg1d, VAL = __mods.validate;
`;

const tpl = fs.readFileSync(path.join(ROOT, 'tools', 'artifact-template.html'), 'utf8');
if (tpl.indexOf('/*@@KERNELS@@*/') < 0) throw new Error('template lost its kernel marker');
const out = tpl.replace('/*@@KERNELS@@*/', bundle);
const dest = path.join(ROOT, 'mfg-cap.html');
fs.writeFileSync(dest, out);
console.log('built ' + dest);
console.log('  interval.js  ' + sha(interval) + '  ' + Buffer.byteLength(interval) + ' bytes  (from ' + path.relative(ROOT, EQ) + ')');
console.log('  mfg1d.js     ' + sha(mfg1d) + '  ' + Buffer.byteLength(mfg1d) + ' bytes');
console.log('  validate.js  ' + sha(validate) + '  ' + Buffer.byteLength(validate) + ' bytes');
console.log('  artifact     ' + sha(out) + '  ' + Buffer.byteLength(out) + ' bytes');
