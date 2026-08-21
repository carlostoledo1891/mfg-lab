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
const sha = s => crypto.createHash('sha256').update(s).digest('hex').slice(0, 16);

/* interval arithmetic is SHARED: kernel/interval.js is a one-line re-export of
   eqcert, and a require() of a sibling path means nothing in a browser. So the
   page embeds eqcert's actual source, read from the toolkit and nowhere else.
   There is deliberately NO vendored fallback: mfg-cap ships inside the same
   repo as eqcert, so a second copy on disk would buy nothing and could drift —
   the failure core/interval/tests/test-single-source.js exists to prevent. */
/* UPWARD SEARCH, not a fixed ascent. Three layouts, no single count correct in all:
   monorepo research/mfg-cap/<dir> · shared export mfg-cap/<dir> · standalone with eqcert vendored
   beside the project. Measured 2026-07-29: the fixed form pointed ABOVE the export root, so the
   PUBLIC `make check` (the published repo's own Makefile) died MODULE_NOT_FOUND. Fails BY NAME. */
function upward(from, rel) {
  const _fs = require('fs'), _p = require('path');
  for (let d = from; ; d = _p.dirname(d)) {
    const hit = _p.join(d, rel);
    if (_fs.existsSync(hit)) return hit;
    if (_p.dirname(d) === d) break;
  }
  throw new Error('could not find ' + rel + ' in any directory above ' + from);
}
const EQ = upward(ROOT, path.join('core', 'interval', 'interval.js'));
const interval = fs.readFileSync(EQ, 'utf8');
/* mfg1d.js and validate.js moved to core/mfg/ in migration phase 6, and this project's kernel/
   dissolved with them — so they are found the same upward way interval.js already was. */
const mfg1d = fs.readFileSync(upward(ROOT, path.join('core', 'mfg', 'mfg1d.js')), 'utf8');
const validate = fs.readFileSync(upward(ROOT, path.join('core', 'mfg', 'validate.js')), 'utf8');

const B = n => `/* ==== BEGIN VERBATIM ${n} ==== */\n`;
const E = n => `/* ==== END VERBATIM ${n} ==== */`;

/* CommonJS shim: each kernel is wrapped so `require` resolves to its siblings. */
const bundle = `
/* The three kernel files below are spliced VERBATIM by this unit's artifact builder.
   Do not edit them here — edit the core/ lobes and rebuild; tests/test-artifact.js
   asserts byte-identity and will go red if these copies drift. */
const __mods = {};
function __def(name, fn) {
  const module = { exports: {} };
  /* Resolve by BASENAME. The old form stripped a leading './' and the '.js', which worked only
     while every kernel sat in one directory. core/mfg/validate.js now requires
     '../interval/interval.js' — and './'.replace on that yields '.interval/interval', a key that
     does not exist, so the page would have loaded with VAL undefined. A basename lookup is
     correct for every form the three spliced files use. */
  const require = n => __mods[n.split('/').pop().replace(/\.js$/, '')];
  fn(module, require);
  __mods[name] = module.exports;
}
__def('interval', function (module, require) {
${B('core/interval/interval.js')}${interval}${E('core/interval/interval.js')}
});
__def('mfg1d', function (module, require) {
${B('core/mfg/mfg1d.js')}${mfg1d}${E('core/mfg/mfg1d.js')}
});
__def('validate', function (module, require) {
${B('core/mfg/validate.js')}${validate}${E('core/mfg/validate.js')}
});
const IV = __mods.interval, MFG = __mods.mfg1d, VAL = __mods.validate;
`;

const tpl = fs.readFileSync(path.join(ROOT, 'tools', 'artifact-template.html'), 'utf8');
if (tpl.indexOf('/*@@KERNELS@@*/') < 0) throw new Error('template lost its kernel marker');
let out = tpl.replace('/*@@KERNELS@@*/', bundle);
/* ROBOTS — and why the template and the page must DISAGREE. artifact-template.html is an
   UNLISTED template that was shipping indexable under the real report's <title>, competing with
   it in search; it was given `noindex, nofollow` on 2026-08-21 and keeps it. mfg-cap.html is a
   PUBLIC page and must be indexable. The generated page inherited the refusal verbatim, so the
   flagship artifact was noindex on the live site while its PAGES.json row said `public` — a
   page held back by a directive meant for its mould. The inversion happens HERE so that neither
   file is hand-maintained and the two cannot drift apart.
   ASSERTED, not best-effort: if the template's block ever changes shape this THROWS instead of
   silently shipping whatever it found. A noindex nothing notices is the vacuous species C10
   names — the page would keep passing every gate while being invisible. */
const TPL_ROBOTS = /<!-- This is a TEMPLATE, not a page\.[\s\S]*?-->\n<meta name="robots" content="noindex, nofollow">/;
if (!TPL_ROBOTS.test(out)) {
  throw new Error('artifact-template.html lost its noindex block — refusing to build (see the ROBOTS note above)');
}
out = out.replace(TPL_ROBOTS,
  '<!-- Robots INVERTED from the template by tools/build-artifact.js: the template is unlisted and\n' +
  '     noindex, this generated page is public and must be indexable. Never hand-edit. -->\n' +
  '<meta name="robots" content="index, follow">');
/* WHERE THE ARTIFACT GOES, and it moved on 2026-08-08 (REBUILD_PLAN phase 2).
   It was ROOT/mfg-cap.html — the unit directory — while the page PUBLISHED at
   technical-reports/mfg-cap.html. Two consequences, both measured:
     · in the export, tests/test-artifact.js re-read the page at its route while the builder
       wrote beside it, so the freshness check compared the artifact TO ITSELF and printed PASS
       on a deliberately corrupted subject (recorded in that battery, 2026-07-30);
     · in the monorepo after phase 2, the rebuild dropped a transient file into the tree that
       `make -j4 check` could catch mid-walk — core/interval/tests/test-single-source.js died on ENOENT
       reading a file another battery had just deleted.
   Both disappear if the builder writes where the page lives. It now emits to the route in
   whichever tree it is run from: site/technical-reports/ here, technical-reports/ in the export.
   No stray, no race, and BUILD_OUT == ART again on both sides. */
const _destCands = [
  path.join(ROOT, '..', 'technical-reports', 'mfg-cap.html'),   /* both trees: the route */
  path.join(ROOT, 'mfg-cap.html'),                              /* pre-2026-08-08 layout */
];
const dest = _destCands.find((p) => fs.existsSync(path.dirname(p))) || _destCands[1];
/* Guard the write: a builder that writes at import scope silently repairs the
   staleness a freshness gate exists to detect (a bug this project shipped once
   elsewhere in the tree). Importing this file must have no side effect. */
if (require.main === module) {
  fs.writeFileSync(dest, out);
} else {
  module.exports = { build: () => out, dest };
}
console.log('built ' + dest);
console.log('  interval.js  ' + sha(interval) + '  ' + Buffer.byteLength(interval) + ' bytes  (from ' + path.relative(ROOT, EQ) + ')');
console.log('  mfg1d.js     ' + sha(mfg1d) + '  ' + Buffer.byteLength(mfg1d) + ' bytes');
console.log('  validate.js  ' + sha(validate) + '  ' + Buffer.byteLength(validate) + ' bytes');
console.log('  artifact     ' + sha(out) + '  ' + Buffer.byteLength(out) + ' bytes');
