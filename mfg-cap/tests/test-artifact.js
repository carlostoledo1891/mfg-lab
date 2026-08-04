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
/* UPWARD SEARCH, for the reason kernel/interval.js states at length: this battery runs in the
   monorepo (project 2 deep), in the shared export (project 1 deep) and in a standalone export
   where eqcert is vendored beside the project. No fixed `..` count is right in all three, and
   the published repo's own Makefile runs this file inside the PUBLIC `make check`. Fails BY NAME. */
function upward(from, rel) {
  for (let d = from; ; d = path.dirname(d)) {
    const hit = path.join(d, rel);
    if (fs.existsSync(hit)) return hit;
    if (path.dirname(d) === d) break;
  }
  return null;
}
let fails = 0;
const check = (n, c, d) => { console.log((c ? 'PASS' : 'FAIL') + '  ' + n + (d !== undefined ? '   [' + d + ']' : '')); if (!c) fails++; };

/* The PAGE's location genuinely differs by tree and the enumeration is correct here (unlike a
   depth count): in the monorepo it sits beside its project, and the export ships it under the
   reports directory.
   technical-reports/ ADDED 2026-07-30. The papers -> technical-reports rename moved the exported
   artifact and this list was not updated with it, so the export branch resolved to nothing and
   THE PUBLIC TREE'S OWN check-cap HAD BEEN RED SINCE THE RENAME — `make public` builds the export
   and then runs the exported tree's batteries, so the whole publish ritual was failing while the
   monorepo's `make check` stayed green (in here ROOT/mfg-cap.html exists, so the first branch
   always answered and the broken one was never exercised). papers/ is KEPT: it costs one
   existsSync, and a reader checking out a pre-rename export should still get a real answer
   instead of this file's least helpful failure mode. */
const ART = [path.join(ROOT, 'mfg-cap.html'),
             upward(ROOT, path.join('technical-reports', 'mfg-cap.html')),
             upward(ROOT, path.join('papers', 'mfg-cap.html'))]
              .find(p => p && fs.existsSync(p));
if (!ART) { console.log('FAIL  artifact missing at ' + path.join(ROOT, 'mfg-cap.html') +
  ' and at no technical-reports/mfg-cap.html or papers/mfg-cap.html above it — run node tools/build-artifact.js'); process.exit(1); }
const html = fs.readFileSync(ART, 'utf8');
console.log('artifact: ' + ART + '  sha256 ' + sha(html) + '  ' + Buffer.byteLength(html) + ' bytes\n');

/* A1 — byte identity of each spliced source. interval arithmetic is SHARED
   with eqcert and embedded from there (kernel/interval.js is a re-export), so
   the page, the kernels and the toolkit are pinned to one implementation. */
const EQ = upward(ROOT, path.join('eqcert', 'src', 'interval.js'));
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

/* A2 — freshness: rebuilding must reproduce the committed file exactly.

   READ THE REBUILT BYTES WHERE THE BUILDER WRITES THEM, NOT AT ART. tools/build-artifact.js
   always emits to ROOT/mfg-cap.html; that is its output path and this battery does not get to
   choose it. In the monorepo ART *is* ROOT/mfg-cap.html, so reading back from ART happened to
   be right and this distinction was invisible for as long as the export was never exercised.

   In the EXPORT it is not right. ART resolves to technical-reports/mfg-cap.html while the
   builder still writes mfg-cap/mfg-cap.html, so re-reading ART returned the untouched original
   and A2 compared the artifact TO ITSELF. Measured 2026-07-30: with the exported artifact
   deliberately corrupted, A2 printed "PASS — rebuild reproduces the committed bytes". A check
   that passes on a corrupted subject is not a weak check, it is a fake certificate, and it was
   introduced by fixing the resolver above without following the write path. The red it replaced
   was more honest than the green.

   Cleanup is part of the check, not hygiene: when BUILD_OUT is not ART the rebuild leaves a file
   the export's allowlist does not contain, and tools/check-public.js correctly reports it as a
   stray and refuses the push. A battery may not leave litter in the tree it validates. */
{
  const BUILD_OUT = path.join(ROOT, 'mfg-cap.html');
  const strayBefore = BUILD_OUT !== ART && !fs.existsSync(BUILD_OUT);
  let same = false, detail = '';
  try {
    const cur = fs.readFileSync(ART);
    execFileSync(process.execPath, [path.join(ROOT, 'tools', 'build-artifact.js')], { cwd: ROOT, stdio: 'ignore' });
    const rebuilt = fs.readFileSync(BUILD_OUT);
    same = Buffer.compare(cur, rebuilt) === 0;
    detail = same ? 'rebuild reproduces the committed bytes'
                  : 'the committed artifact is STALE — rebuild and commit';
    /* restore only when the builder overwrote the subject itself (monorepo layout) */
    if (!same && BUILD_OUT === ART) fs.writeFileSync(ART, cur);
  } catch (e) { detail = 'builder failed: ' + e.message; }
  if (strayBefore) { try { fs.unlinkSync(BUILD_OUT); } catch (e) {} }
  check('A2 artifact is fresh with respect to the kernels', same, detail);
}

/* A3 — the page runs the real thing: evaluate its script and reproduce a
   certified result, comparing against the kernels loaded directly. */
{
  /* Block selection by ANCHOR, never by a greedy span. This used to be
     /<script>([\s\S]*)<\/script>/ — first `<script>` to LAST `</script>` —
     which is right by accident on a one-block page and wrong on every other
     shape: the span carries `</script> … <script>` in its middle and
     `new Function` dies with `SyntaxError: Unexpected token '<'`, unguarded, as
     a bare node stack that takes A4 and the summary with it. The DOM boundary
     `$` is the same anchor the bundle is cut at, so use it to pick the block
     too, and report what was found either way. */
  const DOM_CUT = 'const $ = id => document.getElementById(id);';
  const blocks = (html.match(/<script>([\s\S]*?)<\/script>/g) || [])
    .map(b => b.slice('<script>'.length, -'</script>'.length));
  const carriers = blocks.map((b, i) => ({ i, b, n: b.split(DOM_CUT).length - 1 })).filter(o => o.n > 0);
  const inv = blocks.map((b, i) => '[' + i + '] ' + b.length + ' chars').join(' · ') || 'none';
  let ok = false, detail;
  if (carriers.length !== 1 || carriers[0].n !== 1) {
    detail = 'NO UNAMBIGUOUS BUNDLE BLOCK: ' + blocks.length + ' bare block(s) [' + inv +
             '] · bundle/DOM boundary in ' + carriers.length + ' block(s), ' +
             carriers.reduce((s, o) => s + o.n, 0) + ' occurrence(s)';
  } else {
    /* pull just the bundle out of the page and run it headlessly */
    const src = carriers[0].b;
    const bundle = src.slice(0, src.indexOf(DOM_CUT));
    let MFG, VAL;
    try {
      ({ MFG, VAL } = new Function(bundle + '\nreturn {IV, MFG, VAL};')());
    } catch (e) {
      MFG = null;
      detail = 'the page bundle did not evaluate: ' + e.name + ': ' + e.message;
    }
    if (MFG) {
      const M = require('../kernel/mfg1d.js'), V = require('../kernel/validate.js');
      const P1 = MFG.makeProblem({ sigma: 0.5, c: 1, A: 1, N: 16 });
      const P2 = M.makeProblem({ sigma: 0.5, c: 1, A: 1, N: 16 });
      const r1 = VAL.validate(MFG.solve(P1).x, P1, { nu: 1.05 });
      const r2 = V.validate(M.solve(P2).x, P2, { nu: 1.05 });
      ok = r1.ok && r2.ok && r1.r === r2.r && r1.Z1 === r2.Z1 && r1.Y0 === r2.Y0;
      detail = ok ? ('page and kernel agree exactly: r=' + r1.r.toExponential(3) + ', Z1=' + r1.Z1.toFixed(6))
                  : 'page result differs from the kernel result';
    }
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
