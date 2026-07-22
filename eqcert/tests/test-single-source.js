/* test-single-source.js — there must be exactly ONE of each delicate thing.

   This repository had two independent implementations of outward-rounded
   interval arithmetic and two of exact BigInt rationals. Nothing was wrong with
   either; the problem is that two implementations of the same delicate thing
   drift, and a drifted copy weakens every certificate downstream while still
   printing PASS. The toolkit exists to make that impossible, and this gate is
   what keeps it impossible.

   It scans the working tree for the FINGERPRINTS of a reimplementation —
   the ulp-stepping trick, the BigInt fraction reducer — and fails on any file
   that carries them without being either the toolkit itself or a declared,
   byte-identical vendored copy.

   Deliberately a text scan rather than a dependency check: a second copy is
   usually created by pasting, not by importing.

   MIT licensed. Part of eqcert. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

/* __dirname is <tree>/eqcert/tests. The tree it scans is two levels up. In the
   monorepo that is `academic/`; in the public repo it is the repo root. Either
   way the scanner walks its whole tree and the constants below are expressed
   relative to it, so the file is location-independent and reads the same in
   both places — which matters, because it ships to the public repo. */
const ROOT = path.resolve(__dirname, '..', '..');
const sha = s => crypto.createHash('sha256').update(s).digest('hex').slice(0, 16);
let fails = 0;
const check = (n, c, d) => { console.log((c ? 'PASS' : 'FAIL') + '  ' + n + (d !== undefined ? '   [' + d + ']' : '')); if (!c) fails++; };

/* The one legitimate implementation of each. */
const OWNER = {
  interval: 'eqcert/src/interval.js',
  rational: 'eqcert/src/rational.js'
};
/* Vendored copies, allowed ONLY if byte-identical to their owner. Deliberately
   EMPTY: the one entry here (mfg-cap/vendor/eqcert-interval.js) existed so
   mfg-cap could be published standalone, and it is not — so the copy bought
   nothing and could only drift. An empty map is the stronger invariant: any
   second copy anywhere is a failure, with no allowance to argue about. */
const VENDORED = {};
/* Generated files legitimately contain a spliced copy; their own gates check it.
   Everything that is not source now lives under one dot-directory, so a single
   pattern replaces the list of staging trees this used to name by shape. That
   is also better for this file specifically: it ships publicly, and a public
   file must not narrate the private build (the same defect as naming the build
   tooling in robots.txt) — one neutral entry says less than four. */
const GENERATED = [/\.html$/, /^\.work\//, /^public\//, /^[a-z0-9-]+-site\//,
                   /^\.git\//, /^node_modules\//, /^\.venv\//];
/* the scanner necessarily contains the fingerprints it searches for */
const SELF = 'eqcert/tests/test-single-source.js';

/* Fingerprints of a reimplementation, not of mere use. */
const SIGNS = {
  interval: [/BigUint64Array/, /_u64\[0\]\s*\+=/],
  rational: [/function\s+rgcd|const\s+rgcd\s*=/, /while\s*\(!Number\.isInteger\(/]
};

function walk(dir, out) {
  out = out || [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, e.name);
    const rel = path.relative(ROOT, full);
    if (GENERATED.some(re => re.test(rel))) continue;
    if (e.isDirectory()) walk(full, out);
    else if (/\.(js|mjs|py)$/.test(e.name)) out.push(rel);
  }
  return out;
}

const files = walk(ROOT);
console.log('scanned ' + files.length + ' source files under ' + ROOT + '\n');

for (const kind of Object.keys(SIGNS)) {
  const owner = OWNER[kind];
  const hits = [];
  for (const rel of files) {
    const txt = fs.readFileSync(path.join(ROOT, rel), 'utf8');
    const isImpl = SIGNS[kind].every(re => re.test(txt));
    if (!isImpl) continue;
    if (rel === owner || rel === SELF) continue;
    if (VENDORED[rel] === owner) {
      const same = fs.readFileSync(path.join(ROOT, rel), 'utf8') === fs.readFileSync(path.join(ROOT, owner), 'utf8');
      if (!same) hits.push(rel + ' (vendored copy has DRIFTED)');
      continue;
    }
    hits.push(rel);
  }
  check('one implementation of ' + kind + ' arithmetic, in ' + owner,
    hits.length === 0,
    hits.length ? 'ALSO IMPLEMENTED IN: ' + hits.join(', ') : 'no second implementation found');
}

/* The owners must actually exist and be the files the consumers import. */
for (const kind of Object.keys(OWNER)) {
  const f = path.join(ROOT, OWNER[kind]);
  check(OWNER[kind] + ' exists and is loadable', fs.existsSync(f) && !!require(f),
    fs.existsSync(f) ? sha(fs.readFileSync(f, 'utf8')) : 'MISSING');
}

/* The declared consumers must reach the shared implementation, not a copy. */
{
  const consumers = [
    ['mfg-cap/kernel/interval.js', 'eqcert/src/interval.js'],
    ['mfg-lab/tests/test-wardrop-interval.js', 'eqcert']
  ];
  let ok = true, detail = [];
  for (const [rel, needle] of consumers) {
    const txt = fs.readFileSync(path.join(ROOT, rel), 'utf8');
    if (txt.indexOf(needle) < 0) { ok = false; detail.push(rel + ' no longer references ' + needle); }
  }
  check('every declared consumer imports the shared toolkit', ok,
    ok ? consumers.length + ' consumers wired' : detail.join('; '));
}

/* Falsifier: the scan must actually be able to find a second copy. */
console.log('\n    executing falsifiers');
{
  const tmp = path.join(ROOT, 'eqcert', '.copy-probe.js');
  fs.writeFileSync(tmp, 'const _b=new ArrayBuffer(8);const _u64=new BigUint64Array(_b);\n_u64[0] += 1n;\n');
  const after = walk(ROOT).filter(rel => {
    const txt = fs.readFileSync(path.join(ROOT, rel), 'utf8');
    return SIGNS.interval.every(re => re.test(txt)) && rel !== OWNER.interval && rel !== SELF && !VENDORED[rel];
  });
  fs.unlinkSync(tmp);
  if (after.length > 0) console.log('       RED ok  X1 a planted second implementation IS detected (' + after[0] + ')');
  else { console.log('       RED FAIL  X1 the scan cannot see a second copy — it has no power'); fails++; }
}

console.log('\n' + (fails ? fails + ' FAILURE(S)' :
  'ALL PASS — one interval library, one rational library, and a scan that can\n  see a second copy if one is ever pasted in.'));
process.exit(fails ? 1 : 0);
