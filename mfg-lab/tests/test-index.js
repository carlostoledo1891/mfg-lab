/* test-index.js — the gate for the LANDING PAGE, and for the shape of it.

   There is no separate index file. One was built and deleted the same day: it
   duplicated a landing route the artifact already had, so the "site" was a
   single page split across two files and every link between them pointed from
   mfg-lab.html back to mfg-lab.html. The hub is now the artifact's own `/`
   route, which is why this battery reads mfg-lab.html.

   WHAT IS CHECKED, AND WHY EACH ONE EXISTS

     I1  every site-absolute href on the landing page resolves THROUGH THE
         DEPLOYED ROUTE MAP. Checking the filesystem is the wrong check: these
         pages are served from rewrites, so `/mfg-cap` is right and
         `mfg-cap.html` — a real file — is a 404 in production. The route map
         lives in two places by design (the skeleton here, the deployed file
         after export), so both are tried and NEITHER-FOUND is fatal rather
         than skipped. A route check that quietly does not run is worse than
         no route check.

     I2  every in-page `data-goto` target is a route the artifact actually has.

     I3  THE SHAPE. One featured card for the Lab, exactly three receipt cards,
         and everything else in a LIST. This is asserted because it is a design
         decision that decays silently: cards are easy to add, seven cards of
         equal weight is not a hierarchy, and the wall it becomes still looks
         fine in review. The count is the falsifier.

     I4  no page presents `pip install mfg-lab` as a working command, because
         the distribution is not on PyPI. Doctrine forbids claiming the package
         exists as shipped, and the first draft of the hub printed exactly that.
*/
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..', '..');
const LABDIR = path.join(ROOT, 'mfg-lab');
const ART = path.join(LABDIR, 'mfg-lab.html');

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.error('   FAIL  ' + m); } };

const html = fs.readFileSync(ART, 'utf8');
console.log('== landing-page gate ==');
console.log('   mfg-lab/mfg-lab.html  ' + html.length + ' bytes  sha256:' +
  crypto.createHash('sha256').update(html).digest('hex').slice(0, 16));

ok(!fs.existsSync(path.join(LABDIR, 'index.html')),
   'I0 there is no separate index file — the hub is the artifact\'s own landing route');

/* Isolate the landing page: from its opening div to the next page comment. */
const a = html.indexOf('<div class="page active" id="pgStart">');
const b = html.indexOf('<!-- ============================ PAGE:', a + 10);
ok(a > 0 && b > a, 'I0b the landing page is locatable');
const start = html.slice(a, b);

/* ------------------- I1 · site-absolute links resolve through the route map */
const ROUTE_MAPS = [
  path.join(ROOT, 'vercel.json'),                                   // the export: at the tree root
  path.join(ROOT, '..', 'tools', 'public-skel', 'vercel.json'),     // the monorepo: repo-root tooling, one level above academic/
];
const mapFile = ROUTE_MAPS.find(f => fs.existsSync(f));
if (!mapFile) {
  console.error('   FAIL  I1 no route map found — looked in:\n     ' + ROUTE_MAPS.join('\n     '));
  console.error('landing-page gate FAILED'); process.exit(1);
}
const vercel = JSON.parse(fs.readFileSync(mapFile, 'utf8'));
const ROUTES = new Map(vercel.rewrites.map(r => [r.source, r.destination]));
console.log('   route map: ' + path.relative(ROOT, mapFile) + '  (' + ROUTES.size + ' routes)');

const abs = [...start.matchAll(/href="(\/[^"]*)"/g)].map(m => m[1]);
ok(abs.length >= 3, 'I1a the landing page links out to the other artifacts (' + abs.length + ' site links)');
for (const h of abs) {
  const route = h.split('#')[0];
  const dest = ROUTES.get(route);
  if (dest === undefined) { ok(false, 'I1 "' + h + '" is not a route in vercel.json — it would 404 in production'); continue; }
  ok(fs.existsSync(path.join(ROOT, dest + '.html')), 'I1 ' + route + ' -> ' + dest + '.html exists');
}
const linked = new Set(abs.map(h => h.split('#')[0]));
for (const src of ROUTES.keys())
  ok(linked.has(src) || src === '/', 'I1b every deployed route is reachable from the landing page: ' + src);

/* --------------------------------- I2 · in-page routes are real routes */
const artRoutes = new Set([...html.matchAll(/data-route="([^"]+)"/g)].map(m => m[1]));
ok(artRoutes.size >= 8, 'I2a the artifact exposes its routes (' + artRoutes.size + ')');
const gotos = [...start.matchAll(/data-goto="([^"]+)"/g)].map(m => m[1]);
ok(gotos.length >= 5, 'I2b the landing page routes inward (' + gotos.length + ' data-goto targets)');
for (const g of new Set(gotos))
  ok(artRoutes.has(g), 'I2 data-goto target is a real route: ' + g);

/* --------------------------------------------------------- I3 · THE SHAPE */
const labcards = (start.match(/class="labcard"/g) || []).length;
const receipts = (start.match(/class="rcp"/g) || []).length;
const listitems = (start.match(/<li>/g) || []).length;
ok(labcards === 1, 'I3a exactly one featured Lab card, got ' + labcards);
ok(receipts === 3, 'I3b exactly three receipt cards — more is a wall, not a hierarchy. Got ' + receipts);
ok(listitems >= 5, 'I3c the rest is a list, not more cards (' + listitems + ' entries)');
ok(/class="dirlist"/.test(start), 'I3d the list uses the list idiom');
ok(start.indexOf('class="labcard"') < start.indexOf('class="rcp"'),
   'I3e the Lab comes before the evidence for it — it is the product, not one exhibit among many');
console.log('   I3  shape: 1 Lab card · ' + receipts + ' receipts · ' + listitems + ' list entries');

/* ------------------------------------------ I4 · the package does not exist */
for (const f of ['mfg-lab.html', 'lab.html']) {
  const page = fs.readFileSync(path.join(LABDIR, f), 'utf8').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  if (!/install/i.test(page)) continue;
  ok(!/pip install mfg-lab(?![^.]{0,80}(not published|not on PyPI|from source))/i.test(page),
     'I4 ' + f + ' does not present `pip install mfg-lab` as a working command');
  ok(/not on PyPI|not published to PyPI|install (it )?from (the )?(source|repository)/i.test(page),
     'I4 ' + f + ' says plainly that the package is not published yet');
}

/* --------------------------------------------------- I5 · prose guards */
const text = start.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
[/guaranteed/i, /fastest/i, /best in the world/i].forEach(re => ok(!re.test(text), 'I5 no overreach: ' + re));
ok(!/⟨|⟩|TODO|FIXME|XXX/.test(start), 'I5 no unfilled markers');

console.log('   ' + pass + ' PASS, ' + fail + ' FAIL');
if (fail) { console.error('landing-page gate FAILED'); process.exit(1); }
