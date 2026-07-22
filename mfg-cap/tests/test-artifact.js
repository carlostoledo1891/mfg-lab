/* test-artifact.js — the page cannot diverge from the kernels it claims to run.

   mfg-cap.html is GENERATED from kernel/*.js by tools/build-artifact.js. This
   gate proves the generated file is (a) fresh and (b) byte-identical in its
   spliced regions to the kernel sources, so "what you prove in the browser is
   what make check proved" is a checked statement rather than a promise.

   The freshness check deliberately does NOT import the builder — a gate that
   runs its own builder repairs the staleness it exists to detect, and then
   passes honestly. It rebuilds into a temporary buffer instead.

   MIT licensed. Part of mfg-cap. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const sha = s => crypto.createHash('sha256').update(s).digest('hex').slice(0, 16);
let fails = 0;
const check = (n, c, d) => { console.log((c ? 'PASS' : 'FAIL') + '  ' + n + (d !== undefined ? '   [' + d + ']' : '')); if (!c) fails++; };

const ART = path.join(ROOT, 'mfg-cap.html');
if (!fs.existsSync(ART)) { console.log('FAIL  artifact missing — run node tools/build-artifact.js'); process.exit(1); }
const html = fs.readFileSync(ART, 'utf8');
console.log('artifact: ' + ART + '  sha256 ' + sha(html) + '  ' + Buffer.byteLength(html) + ' bytes\n');

/* A1 — byte identity of each spliced source. interval arithmetic is SHARED
   with eqcert and embedded from there (kernel/interval.js is a re-export), so
   the page, the kernels and the toolkit are pinned to one implementation. */
const EQ = path.join(ROOT, '..', 'eqcert', 'src', 'interval.js');
const SOURCES = [['eqcert/src/interval.js', EQ],
                 ['kernel/mfg1d.js', path.join(ROOT, 'kernel', 'mfg1d.js')],
                 ['kernel/validate.js', path.join(ROOT, 'kernel', 'validate.js')]];
for (const [name, file] of SOURCES) {
  const src = fs.readFileSync(file, 'utf8');
  const B = `/* ==== BEGIN VERBATIM ${name} ==== */\n`;
  const E = `/* ==== END VERBATIM ${name} ==== */`;
  const i = html.indexOf(B), j = html.indexOf(E);
  const emb = (i >= 0 && j > i) ? html.slice(i + B.length, j) : null;
  check('A1 ' + name + ' embedded byte-identical', emb === src,
    emb === null ? 'markers missing' : (emb === src ? sha(src) : 'DRIFT: ' + sha(emb) + ' vs ' + sha(src)));
}

/* A1b — there must be NO second copy of the toolkit on disk. mfg-cap used to
   vendor eqcert/src/interval.js so it could stand alone; it no longer stands
   alone, and the vendored file became a byte-identical duplicate whose only
   possible future is to drift. This asserts the absence, so re-introducing the
   copy turns the gate red instead of silently restoring the hazard. */
{
  const v = path.join(ROOT, 'vendor');
  check('A1 no vendored copy of the toolkit exists (one implementation, in eqcert)',
    !fs.existsSync(v), fs.existsSync(v) ? 'vendor/ is back — delete it' : 'absent');
}

/* A2 — freshness: rebuilding must reproduce the committed file exactly */
{
  const tmp = path.join(ROOT, '.freshness-check.html');
  let same = false, detail = '';
  try {
    const cur = fs.readFileSync(ART);
    execFileSync(process.execPath, [path.join(ROOT, 'tools', 'build-artifact.js')], { cwd: ROOT, stdio: 'ignore' });
    const rebuilt = fs.readFileSync(ART);
    same = Buffer.compare(cur, rebuilt) === 0;
    if (!same) { fs.writeFileSync(ART, cur); detail = 'the committed artifact is STALE — rebuild and commit'; }
    else detail = 'rebuild reproduces the committed bytes';
  } catch (e) { detail = 'builder failed: ' + e.message; }
  try { fs.unlinkSync(tmp); } catch (e) {}
  check('A2 artifact is fresh with respect to the kernels', same, detail);
}

/* A3 — the page runs the real thing: evaluate its script and reproduce a
   certified result, comparing against the kernels loaded directly. */
{
  const m = html.match(/<script>([\s\S]*)<\/script>/);
  const src = m ? m[1] : null;
  let ok = false, detail = 'no script block';
  if (src) {
    /* pull just the bundle out of the page and run it headlessly */
    const cut = src.indexOf('const $ = id => document.getElementById(id);');
    const bundle = src.slice(0, cut);
    const f = new Function(bundle + '\nreturn {IV, MFG, VAL};');
    const { MFG, VAL } = f();
    const M = require('../kernel/mfg1d.js'), V = require('../kernel/validate.js');
    const P1 = MFG.makeProblem({ sigma: 0.5, c: 1, A: 1, N: 16 });
    const P2 = M.makeProblem({ sigma: 0.5, c: 1, A: 1, N: 16 });
    const r1 = VAL.validate(MFG.solve(P1).x, P1, { nu: 1.05 });
    const r2 = V.validate(M.solve(P2).x, P2, { nu: 1.05 });
    ok = r1.ok && r2.ok && r1.r === r2.r && r1.Z1 === r2.Z1 && r1.Y0 === r2.Y0;
    detail = ok ? ('page and kernel agree exactly: r=' + r1.r.toExponential(3) + ', Z1=' + r1.Z1.toFixed(6))
                : 'page result differs from the kernel result';
  }
  check('A3 the page reproduces the kernel proof bit for bit', ok, detail);
}

/* A4 — prose guards: the page must not overclaim */
{
  const text = html.replace(/<[^>]+>/g, ' ');
  const banned = [
    ['first computer-assisted proof of a forward', 'the forward-backward claim is retracted'],
    ['new uniqueness theorem', 'no new uniqueness theorem is claimed'],
    ['proves uniqueness for all', 'global uniqueness is never claimed here']
  ];
  const hits = banned.filter(([p]) => new RegExp(p, 'i').test(text)).map(([p]) => p);
  check('A4 no retracted or overreaching claim appears on the page', hits.length === 0,
    hits.length ? 'FOUND: ' + hits.join('; ') : banned.length + ' phrases absent');
  const required = [
    'not a new existence or uniqueness theorem',
    'Hopf',
    'quadratic Hamiltonian',
    'mis-posed'
  ];
  const missing = required.filter(p => text.indexOf(p) < 0);
  check('A4 the required disclosures are present', missing.length === 0,
    missing.length ? 'MISSING: ' + missing.join('; ') : required.length + ' disclosures present');
}

console.log('\n' + (fails ? fails + ' FAILURE(S)' : 'ALL PASS — the artifact is generated, fresh, byte-identical to the kernels,\n  numerically identical to them, and states its own limits.'));
process.exit(fails ? 1 : 0);
