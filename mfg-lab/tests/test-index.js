/* test-index.js — the gate for the hub page.

   AN INDEX IS A SET OF PROMISES ABOUT OTHER FILES, and it is the one page whose
   defects are invisible from inside itself: a door that opens onto nothing looks
   exactly like a door that works until somebody clicks it. This repository has
   already shipped the adjacent defect — sin-mfg.html said "the MFG Lab, its
   interactive companion piece" with NO href at all, prose asserting a
   relationship the page did not implement, and no gate could see it because the
   placeholder checker looks for unfilled markers rather than missing content.

   So every promise the index makes is checked here:

     I1  every site-absolute href resolves THROUGH THE DEPLOYED ROUTE MAP to a
         file that exists. Checking the filesystem would be the wrong check:
         these pages are served from rewrites, so `/mfg-cap` is correct and
         `mfg-cap.html` — which is what the first draft of this index used, and
         what a filesystem check would have accepted — is a 404 in production;
     I2  every route link (#/x) corresponds to a real route in mfg-lab.html;
     I3  the door with nothing behind it is NOT an anchor — an unopenable door
         must not be clickable, and this is asserted structurally rather than
         trusted to CSS;
     I4  the battery count on the page is RECOMPUTED, not remembered — and
         recomputed from the PUBLIC Makefile specifically, because this page
         ships publicly and "this repository" means the one a reader cloned.
         The monorepo runs more batteries than the public repo (it carries
         private projects), so measuring the local Makefile would print a
         number no reader can reproduce.
*/
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..', '..');
const LABDIR = path.join(ROOT, 'mfg-lab');
const IDX = path.join(LABDIR, 'index.html');

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.error('   FAIL  ' + m); } };

const html = fs.readFileSync(IDX, 'utf8');
console.log('== index gate ==');
console.log('   mfg-lab/index.html  ' + html.length + ' bytes  sha256:' +
  crypto.createHash('sha256').update(html).digest('hex').slice(0, 16));

/* ------------------- I1 · every local href resolves THROUGH THE ROUTE MAP */
/* The route map lives in two places by design: in the monorepo it is the
   skeleton that the exporter copies, and in the EXPORTED tree it is the
   deployed file at the root. This battery runs in both, so it looks in both —
   and fails loudly if neither is found rather than skipping, because a route
   check that quietly does not run is worse than no route check. (Found the
   hard way: the first version hardcoded the monorepo path and the public
   tree's own `make check` went red on export.) */
const ROUTE_MAPS = [path.join(ROOT, 'vercel.json'),
                    path.join(ROOT, 'tools', 'public-skel', 'vercel.json')];
const mapFile = ROUTE_MAPS.find(f => fs.existsSync(f));
if (!mapFile) {
  console.error('   FAIL  I1 no route map found — looked in:\n     ' + ROUTE_MAPS.join('\n     '));
  console.error('index gate FAILED'); process.exit(1);
}
const vercel = JSON.parse(fs.readFileSync(mapFile, 'utf8'));
console.log('   route map: ' + path.relative(ROOT, mapFile));
const ROUTES = new Map(vercel.rewrites.map(r => [r.source, r.destination]));
const hrefs = [...html.matchAll(/href="([^"]+)"/g)].map(m => m[1]);
const local = hrefs.filter(h => !/^(https?:|mailto:|#)/.test(h));
ok(local.length >= 5, 'I1a the index actually links somewhere (' + local.length + ' local links)');
for (const h of local) {
  const route = h.split('#')[0];
  if (!route) continue;
  const dest = ROUTES.get(route);
  if (dest === undefined) { ok(false, 'I1 "' + h + '" is not a route in vercel.json — it would 404 in production'); continue; }
  /* cleanUrls: the destination has no extension on disk. */
  ok(fs.existsSync(path.join(ROOT, dest + '.html')),
     'I1 ' + route + ' -> ' + dest + '.html exists');
}
/* And the inverse, which is the failure nobody notices: a route nothing links to. */
const linked = new Set(local.map(h => h.split('#')[0]));
for (const src of ROUTES.keys())
  ok(linked.has(src) || src === '/', 'I1b every deployed route is reachable from the index: ' + src);

/* --------------------------------- I2 · every route link is a real route */
const artifact = fs.readFileSync(path.join(LABDIR, 'mfg-lab.html'), 'utf8');
const routes = new Set([...artifact.matchAll(/data-route="([^"]+)"/g)].map(m => m[1]));
ok(routes.size >= 8, 'I2a the artifact exposes its routes (' + routes.size + ' found)');
for (const h of local) {
  const frag = h.split('#')[1];
  if (!frag || !frag.startsWith('/')) continue;
  ok(routes.has(frag), 'I2 route link points at a route that exists: #' + frag +
     (routes.has(frag) ? '' : '  [known: ' + [...routes].join(' ') + ']'));
}

/* ------------------------- I3 · a door with nothing behind it is not a link */
const unbuiltBlocks = [...html.matchAll(/<(a|div)([^>]*class="door unbuilt"[^>]*)>/g)];
ok(unbuiltBlocks.length >= 1, 'I3a the unbuilt door is present and labelled');
ok(unbuiltBlocks.every(m => m[1] === 'div'),
   'I3b it is a <div>, never an <a> — a door that opens onto nothing must not be clickable');
ok(/not built yet/i.test(html), 'I3c and it says so in words, not only in styling');
/* The inverse: no door may be BOTH a link and marked unbuilt. */
ok(!/<a[^>]*class="[^"]*unbuilt/.test(html), 'I3d no anchor carries the unbuilt class');

/* ------------------------------- I4 · the battery count is recomputed
   From the PUBLIC Makefile in either tree — the skeleton here, the deployed
   file after export — for the reason in the header. */
const MK_FILES = [path.join(ROOT, 'tools', 'public-skel', 'Makefile'), path.join(ROOT, 'Makefile')];
const mkFile = MK_FILES.find(f => fs.existsSync(f));
ok(!!mkFile, 'I4z a Makefile to count is present');
const mk = fs.readFileSync(mkFile, 'utf8');
const inCheck = mk.split('\n');
let counting = false, batteries = 0;
for (const line of inCheck) {
  if (/^check-(eqcert|lab|sin|route|cert|cap):/.test(line)) { counting = true; continue; }
  if (/^[a-z][a-z-]*:/.test(line)) { counting = false; continue; }
  if (counting && /\$\(NODE\)/.test(line)) batteries++;
}
const stated = (html.match(/id="nbat">(\d+)</) || [])[1];
ok(stated !== undefined, 'I4a the page states a battery count');
ok(Number(stated) === batteries,
   'I4b and it matches the Makefile, recomputed: page says ' + stated + ', Makefile runs ' + batteries);
console.log('   I4  batteries in the public `make check` (' + path.relative(ROOT, mkFile) + '): ' + batteries +
  (Number(stated) === batteries ? ' (page agrees)' : ' — PAGE SAYS ' + stated));

/* --------------------------------------------------- I5 · prose guards
   Whitespace is NORMALISED before matching. The first version of this gate
   reported "the house rule is not stated on the front page" while the page
   said it plainly — the phrase was split across a line break, and the pattern
   matched a single space. Same corollary as the &nbsp; lesson: match the
   variants, or the gate is measuring your line wrapping. */
const text = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
[/proves? that .* is correct/i, /guaranteed/i, /fastest/i, /best in the world/i]
  .forEach(re => ok(!re.test(text), 'I5 no overreach: ' + re));
ok(/cannot exist without a falsifier/i.test(text), 'I5 the house rule is stated on the front page');
ok(/not a claim of reproduction/i.test(text), 'I5 "in the style of" is disclaimed where it appears');
ok(!/⟨|⟩|TODO|FIXME|XXX/.test(html), 'I5 no unfilled markers');

/* ------------------------------------- I6 · the package does not exist yet
   Doctrine: never claim the Python package "exists" as shipped. The first
   draft of this page printed `pip install mfg-lab` as a working command; the
   distribution is not on PyPI, so that instruction fails for every reader who
   tries it. Caught by READING the rendered page, not by any check — which is
   why it is now a check. Applies to every page that mentions installing. */
for (const f of ['index.html', 'lab.html']) {
  const page = fs.readFileSync(path.join(LABDIR, f), 'utf8').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  if (!/mfglab|mfg-lab/.test(page)) continue;
  const claims = /pip install mfg-lab(?![^.]{0,80}(not published|not on PyPI|from source))/i.test(page);
  ok(!claims, 'I6 ' + f + ' does not present `pip install mfg-lab` as a working command');
  if (/install/i.test(page))
    ok(/not on PyPI|not published to PyPI|install (it )?from (the )?(source|repository)/i.test(page),
       'I6 ' + f + ' says plainly that the package is not published yet');
}

console.log('   ' + pass + ' PASS, ' + fail + ' FAIL');
if (fail) { console.error('index gate FAILED'); process.exit(1); }
