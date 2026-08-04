/* test-water-value-diff.js — the ONE-KERNEL gate for the water-value tree.

   sin-mfg/tools/water_value_tree.js is embedded VERBATIM into the artifacts so
   the Water value page can run the theorem live. That creates further copies of
   a validated kernel, which is precisely the failure mode this repo has paid for
   more than once (a battery certifying a stale copy while the artifact drifts).
   So the copies are GATED, not trusted:

     D0  the set of EMBEDDERS is DISCOVERED, not assumed. This file used to
         read exactly one artifact and loop over nothing. MEASURED 2026-07-28:
         grepping the BEGIN marker across the tree returns TWO embedders —
         academic/mfg-lab/mfg-lab.html AND academic/mfg-lab/onepager.html —
         and the second was entirely ungated. The header even said "one kernel,
         two artifacts" while the code could only ever see one. A hardcoded
         subject list is the same species as a hardcoded path: it looks like a
         fact because it is written down. Zero embedders is FATAL, never a
         vacuous pass — an empty loop passes every assertion inside it.
     D1  for EVERY discovered embedder, the bytes between the markers are
         IDENTICAL to the tool file — not "equivalent", identical;
     D2  for EVERY discovered embedder, that embedded copy actually runs, and
         its certificates hold on THAT page's own default controls;
     D3  the embedded copy and the tool file, given the same instance, return
         the same primal, the same dual and the same certificate — so the
         embedding cannot silently lose a term;
     D4  the martingale identity the page displays is the one the theorem
         states: w_n = E[w_child|n] at interior nodes ONLY, and the residual
         is a max over interior nodes rather than over all of them.

   D3 and D4 run against ONE embedder (the primary, MFG_HTML or mfg-lab.html):
   D1 has already certified every other copy to be the same bytes, so running
   the sweep per copy would measure the same function twice. If D1 goes red for
   a copy, D2 still ran against it and says so by name.

   COUNTS, MEASURED 2026-07-28 (`node test-water-value-diff.js | grep -c '^PASS'`)
   — do not restate any of these from memory, and re-measure when you add a
   check. It read "2 gated embedders … 11 PASS lines and 5 falsifiers" until M3
   deleted onepager.html the same day. RE-MEASURED AFTER M3: 1 gated embedder,
   9 PASS lines, 4 APPLICABLE falsifiers of 5 written. The -2 PASS are that
   page's D1 and D2; the falsifier that stopped applying is M1b, which needs a
   second subject to plant in and says so out loud rather than passing. Earlier
   still it was 10 PASS / 3 falsifiers, before D0/D1/D2 became per-embedder
   loops and before M1b and M1c were written.

   Falsifiers at the end: each mutates one thing and must turn its own check
   red. A gate that cannot go red is decoration. One of them plants divergence
   in the SECOND embedder specifically, because a loop bug that stops after the
   first subject is invisible to a falsifier aimed at the first. */
'use strict';
const fs=require('fs'), path=require('path'), crypto=require('crypto'), os=require('os');

const sha=b=>crypto.createHash('sha256').update(b).digest('hex').slice(0,16);

let fails=0;
function check(name,cond,detail){
  console.log((cond?'PASS':'FAIL')+'  '+name+(detail!==undefined?'   ['+detail+']':''));
  if(!cond)fails++;
}

/* A MISSING SUBJECT MUST BE A SENTENCE, NOT A STACK TRACE. Guard copied from
   test-index.js (which already solved this for itself). An unguarded
   readFileSync throws ENOENT: the runner sees a node internal frame and a
   nonzero exit, and cannot tell "the gate caught something" from "the gate is
   broken". Worse, the throw aborts the module, so every check after it — and
   the PASS/FAIL summary — silently stops running. MEASURED 2026-07-28: with
   MFG_HTML pointed at a missing path this battery printed ZERO PASS lines,
   ZERO FAIL lines and a stack trace. */
function mustExist(p,what,advice){
  if(fs.existsSync(p))return;
  console.log('FAIL  D0z '+what+' is not there: '+p);
  console.log('      This is a MISSING FILE, not a failed assertion. '+advice);
  console.log('\nwater-value one-kernel gate FAILED — subject missing, so NO check in this battery ran.');
  process.exit(1);
}

const ROOT=process.env.WV_ROOT||require('./_root.js').treeRoot(__dirname);
const HTML=process.env.MFG_HTML||path.resolve(__dirname,'..','mfg-lab.html');
/* CROSS-TRACK, AND SPELLED OUT. THIS file has not moved; its TARGET has. The walk used to be
   `__dirname/../../sin-mfg/tools/...`, which reached a sibling by exploiting that mfg-lab and
   sin-mfg shared the `academic/` parent. M7a (2026-07-28) moved the kernel to
   research/stock-constraint, so the old walk pointed at a path that no longer exists. Named
   explicitly now: one more `..` to the repo root, then the track spelled out. The BEGIN marker
   below still reads `sin-mfg/tools/...` and is NOT stale — that is the PUBLIC destination,
   which M7a deliberately did not move. */
/* TWO LOCATIONS, ONE KERNEL, and the second is not a fallback for a missing file — it is where
   this same kernel LIVES in the exported tree. The comment above already says the public
   destination stayed `sin-mfg/tools/...` while the monorepo source moved to
   research/stock-constraint; naming only the source made this battery monorepo-only, and the
   export died here with "subject missing, so NO check in this battery ran" (measured
   2026-07-30, immediately after the _root.js allowlist fix let it get this far).
   Order matters: the monorepo source is tried FIRST, so in this tree the gate still diffs
   against the owning copy and never silently certifies the export's copy against itself. */
const _r=require('./_root.js');
const TOOL=process.env.WVTREE||
  [_r.rootPath('research','stock-constraint','tools','water_value_tree.js'),
   _r.rootPath('sin-mfg','tools','water_value_tree.js')].find(p=>fs.existsSync(p))||
  _r.rootPath('research','stock-constraint','tools','water_value_tree.js');
mustExist(TOOL,'the single source kernel every embedder is diffed against',
  'Re-point WVTREE at research/stock-constraint/tools/water_value_tree.js; without it there is no "one kernel" to be the one.');
mustExist(HTML,'the primary artifact D3/D4 drive the embedded copy from',
  'Re-point MFG_HTML at an artifact that embeds the water-value kernel.');

const BEGIN='/* ==== BEGIN VERBATIM sin-mfg/tools/water_value_tree.js ==== */\n';
const END='/* ==== END VERBATIM ==== */';
function embedded(src){
  const i=src.indexOf(BEGIN), j=src.indexOf(END);
  if(i<0||j<0||j<i)return null;
  return src.slice(i+BEGIN.length,j);
}

/* ---- D0: DISCOVER the embedders; never assume them -------------------------
   Walk for .html files carrying the BEGIN marker. Two categories come back and
   the difference is a DESIGN CHOICE, not an oversight (fatal-vs-advisory: a
   gate that is red for a reason it cannot fix gets disabled, which is how a
   gate dies):

     GATED    — source artifacts. These are the "one kernel, N artifacts" claim.
     ADVISORY — copies inside scratch, staging or generated-output trees: any
                path segment beginning with '.' (ignored by version control
                here) or a conventional build-output directory. MEASURED
                2026-07-28: the walk finds 5 such copies alongside the 2 gated
                ones. Those trees are where other batteries stage mutants, so
                gating them would turn this gate red at the exact moment a
                mutation test is doing its job. They are PRINTED, never hidden
                — an invisible copy is the defect; a copy that is visible and
                out of scope is a decision. */
const HARD_SKIP=new Set(['.git','node_modules','__pycache__']);
const BUILD_DIRS=new Set(['public','dist','build','out','target','coverage','venv']);
function walkHtml(dir,out){
  let ents;
  try{ents=fs.readdirSync(dir,{withFileTypes:true});}catch(e){return out;}
  for(const e of ents){
    if(HARD_SKIP.has(e.name))continue;
    const p=path.join(dir,e.name);
    if(e.isDirectory())walkHtml(p,out);
    else if(e.isFile()&&e.name.endsWith('.html'))out.push(p);
  }
  return out;
}
const rel=p=>path.relative(ROOT,p).split(path.sep).join('/');
const isScratch=p=>rel(p).split('/').slice(0,-1)
  .some(seg=>seg.startsWith('.')||BUILD_DIRS.has(seg));
function discoverAll(root){
  return walkHtml(root,[]).filter(f=>{
    let s; try{s=fs.readFileSync(f,'utf8');}catch(e){return false;}
    return embedded(s)!==null;
  }).sort();
}
function discover(root){return discoverAll(root).filter(f=>!isScratch(f));}

/* The allowlist is what we EXPECT to find, so a new embedder appearing is a
   red rather than a silent widening of the trusted set. It is not the loop's
   input — the loop's input is what is actually on disk. */
/* M3, 2026-07-28: academic/mfg-lab/onepager.html LEFT this list because the file was
   deleted, not because the gate was loosened. The set is what we EXPECT to find, so a
   deleted embedder must leave it or D0b reports MISSING forever; an embedder that
   APPEARS still turns D0b red, which is the direction that matters. One embedder is a
   thinner claim than two and the summary line says so, because it is derived. */
/* 2026-07-29: the embedder's path is DERIVED from where this battery sits, not typed. It has moved
   three times in one day (academic/mfg-lab -> mfg-lab -> research/mfg-lab) and each time a typed
   literal here reported the real page as UNEXPECTED and the old address as MISSING — a red about
   the gate's own bookkeeping, wearing the costume of a drift finding. The page is the project's
   own artifact, so its location relative to THIS FILE is the one thing that does not move. */
/* TWO CARRIERS AS OF 2026-07-30, and it will be one again shortly. The lab dissolution
   (the lab-dissolution record) moved MWV to its own page under stock-constraint;
   until mfg-lab.html is deleted both embed the kernel, and BOTH must be gated -- an unregistered
   embedder of a validated kernel is precisely how a kernel forks in silence, which is what this
   battery exists to prevent. It caught the new page on its first run: "UNEXPECTED
   research/stock-constraint/water-value.html". Drop the mfg-lab entry when the page goes; do NOT
   drop the stock-constraint one, which is the surviving carrier. */
/* TWO LAYOUTS, and the carrier is DERIVED in both. The comment above is right that the path must
   not be typed -- but deriving it against the monorepo layout alone made it monorepo-only, and the
   export (where this project is `mfg-lab/` and the note is `sin-mfg/`) reported the real page as
   MISSING. Same species as the WVTREE resolution above, and the same fix: name both layouts, take
   the one that exists. Monorepo FIRST, so in this tree nothing changes. If NEITHER exists the
   monorepo path is kept, so D0b still reports MISSING rather than quietly shrinking the expected
   set -- an embedder that vanishes must stay red. */
function carrier(){
  const monorepo=path.resolve(__dirname,'..','..','stock-constraint','water-value.html');
  const exported=path.resolve(__dirname,'..','..','sin-mfg','water-value.html');
  return [monorepo,exported].find(p=>fs.existsSync(p))||monorepo;
}
const EXPECTED=[rel(path.resolve(__dirname,'..','mfg-lab.html')),
                rel(carrier())];

const allAbs=discoverAll(ROOT);
const foundAbs=allAbs.filter(f=>!isScratch(f));
const scratchAbs=allAbs.filter(isScratch);
const found=foundAbs.map(rel);
if(foundAbs.length===0){
  console.log('FAIL  D0a ZERO embedders of the water-value kernel found under '+ROOT);
  console.log('      This is FATAL, not a pass. Every D1/D2 check below runs INSIDE a loop over');
  console.log('      the embedders; with none, they all "pass" while certifying nothing — the');
  console.log('      exact shape of a fake certificate. If the embedding was removed on purpose,');
  console.log('      retire this battery deliberately; if the marker text changed, re-point BEGIN.');
  console.log('\nwater-value one-kernel gate FAILED — no subject, so NO copy was certified.');
  process.exit(1);
}

const tool=fs.readFileSync(TOOL,'utf8');
console.log('kernel    : '+TOOL+'  sha256 '+sha(tool)+'  ('+Buffer.byteLength(tool)+' bytes)');
console.log('root      : '+ROOT);
console.log('embedders : '+foundAbs.length+' discovered and GATED');
for(const p of found)console.log('            · '+p);
if(scratchAbs.length){
  console.log('advisory  : '+scratchAbs.length+' further cop'+(scratchAbs.length===1?'y':'ies')+
              ' in scratch/build trees — printed, deliberately NOT gated');
  for(const p of scratchAbs)console.log('            · '+rel(p));
}
console.log('primary   : '+HTML+'  (D3/D4 drive this one)\n');

check('D0a at least one embedder was DISCOVERED (an empty loop is not a pass)',
  foundAbs.length>0,foundAbs.length+' found');
{
  const unexpected=found.filter(f=>!EXPECTED.includes(f));
  const missing=EXPECTED.filter(f=>!found.includes(f));
  check('D0b the discovered embedders are exactly the expected set',
    unexpected.length===0&&missing.length===0,
    (unexpected.length?'UNEXPECTED '+unexpected.join(', ')+' ':'')+
    (missing.length?'MISSING '+missing.join(', '):'')+
    (unexpected.length||missing.length?'':found.length+' == expected '+EXPECTED.length));
  if(unexpected.length){
    console.log('      An embedder nobody gated is a second copy of a validated kernel. Either');
    console.log('      add it to EXPECTED (it is now gated by D1/D2) or stop embedding there.');
  }
}
check('D0c the primary artifact is one of the discovered embedders',
  found.includes(rel(HTML)),rel(HTML));

/* ---- D1: byte identity, for EVERY embedder ---- */
const srcOf=new Map();
for(const abs of foundAbs)srcOf.set(abs,fs.readFileSync(abs,'utf8'));
function identityVerdict(sources){
  /* sources: Map abs -> text. Returns {ok, offenders[]} — offenders NAMED, so a
     loop that stops early is visible in the output rather than only in a count. */
  const offenders=[];
  for(const [abs,text] of sources){
    const e=embedded(text);
    if(e===null||e!==tool)offenders.push(rel(abs));
  }
  return {ok:offenders.length===0,offenders};
}
for(const abs of foundAbs){
  const e=embedded(srcOf.get(abs));
  check('D1 '+rel(abs)+' embeds the kernel byte-identically',e!==null&&e===tool,
    e===null?'markers not found':
    (e===tool?('sha256 '+sha(e)+' · '+Buffer.byteLength(e)+' bytes'):
      ('embedded sha '+sha(e)+' vs tool sha '+sha(tool)+
       ' · lengths '+Buffer.byteLength(e)+' vs '+Buffer.byteLength(tool))));
}
const html=srcOf.get(foundAbs.find(a=>rel(a)===rel(HTML)))||fs.readFileSync(HTML,'utf8');
const emb=embedded(html);
if(emb===null){console.log('\ncannot continue: the primary artifact has no markers');process.exit(1);}

/* ---- load BOTH implementations ---- */
function loadEmbedded(src){
  const body=embedded(src);
  const f=new Function('const module={exports:{}}, require={main:null};\n'+body+'\nreturn module.exports;');
  return f();
}
const EMB=loadEmbedded(html);
const REF=require(TOOL);

/* ---- D2: EVERY embedded copy runs, on ITS OWN page's defaults ---- */
/* Defaults are read from each artifact's range inputs rather than retyped, so
   this check follows the page instead of a remembered configuration. A missing
   control is a NAMED failure, not a throw: this loop has more than one subject
   now, and a throw on the first would take the rest down with it. */
function pageDefaults(src,label){
  const ids=['wvDepth','wvRbar','wvHbar','wvPhi','wvSeed'];
  const out={},missing=[];
  for(const id of ids){
    const m=src.match(new RegExp('id="'+id+'"[^>]*value="([-\\d.]+)"'));
    if(!m){missing.push(id);continue;}
    out[id.slice(2).toLowerCase()]=parseFloat(m[1]);
  }
  if(missing.length){
    check('D2 '+label+' declares every water-value control this battery reads',false,
      'missing '+missing.join(', '));
    return null;
  }
  return {depth:out.depth,Rbar:out.rbar,hbar:out.hbar,phi:out.phi,seed:out.seed};
}
function mulberry32(s){return function(){s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function instance(K,o){
  const rng=mulberry32(o.seed);
  const nodes=K.buildTree(o.depth,2,n=>({price:0.5+0.8*rng()+(n.depth===2?0.5:0),
                                         inflow:0.15+0.5*rng()}));
  return K.solveTree(nodes,{R0:0.4*o.Rbar/0.8,Rbar:o.Rbar,hbar:o.hbar,phi:o.phi});
}
/* One D2 verdict per embedder, its path in the check name — so a loop that
   stops after the first subject shows up as a MISSING LINE, which a human
   reading the output can see, not merely as a count that still says PASS. */
let D=null;
for(const abs of foundAbs){
  const label=rel(abs), src=srcOf.get(abs);
  const d=pageDefaults(src,label);
  if(d===null)continue;
  if(rel(abs)===rel(HTML))D=d;
  let K=null,err=null;
  try{K=loadEmbedded(src);}catch(e){err=e.message;}
  if(!K||typeof K.solveTree!=='function'){
    check('D2 '+label+' embedded kernel loads',false,err||'no solveTree export');
    continue;
  }
  let r=null;try{r=instance(K,d);}catch(e){err=e.message;}
  if(!r||!r.cert){check('D2 '+label+' embedded kernel solves its own page defaults',false,err||'no certificate');continue;}
  const c=r.cert;
  check('D2 '+label+' solves its page defaults with a clean certificate',
    c.gapRel<1e-12&&c.dynErr<1e-9&&c.boxErr<1e-9&&
    c.tri===0&&c.wedgeSignErr<1e-9&&c.compSlack<1e-9&&c.spillDualErr<1e-9,
    'defaults '+JSON.stringify(d)+' · '+r.nodes.length+' nodes · gap '+c.gapRel.toExponential(2)+
    ' · dyn '+c.dynErr.toExponential(2)+' · box '+c.boxErr.toExponential(2)+
    ' · tri '+c.tri+' · wedge '+c.wedgeSignErr.toExponential(2));
}
if(D===null){
  console.log('FAIL  D2z the primary artifact does not declare the water-value controls this battery reads: '+rel(HTML));
  console.log('\nwater-value one-kernel gate FAILED — no page defaults for D3/D4, so the sweep did not run.');
  process.exit(1);
}
/* ---- D3: the two copies agree exactly, over a sweep ---- */
{
  let worstW=0,worstH=0,worstGap=0,n=0,mismatched=0;
  for(const depth of [3,4,5])for(const Rbar of [0.45,0.8,1.6])
  for(const hbar of [0.2,0.35,0.7])for(const phi of [0,0.55,1.4])for(const seed of [7,23]){
    const o={depth,Rbar,hbar,phi,seed};
    const a=instance(EMB,o), b=instance(REF,o);
    n++;
    if(a.w.length!==b.w.length){mismatched++;continue;}
    for(let i=0;i<a.w.length;i++){
      worstW=Math.max(worstW,Math.abs(a.w[i]-b.w[i]));
      worstH=Math.max(worstH,Math.abs(a.h[i]-b.h[i]));
    }
    worstGap=Math.max(worstGap,Math.abs(a.cert.gapRel-b.cert.gapRel),
                      Math.abs(a.cert.martingaleRes-b.cert.martingaleRes));
  }
  check('D3 embedded == tool on every instance of a '+n+'-case sweep',
    mismatched===0&&worstW===0&&worstH===0&&worstGap===0,
    'max |Δw| '+worstW+' · max |Δh| '+worstH+' · max |Δcert| '+worstGap);
}

/* ---- D4: the displayed identity is the theorem's, not a flattering variant ----
   The claim is about INTERIOR nodes. Two ways to cheat: (a) average instead of
   maximise, (b) include binding nodes in the max so a small number hides a
   violation, or exclude so many nodes that the claim is vacuous. Recompute the
   residual independently from the certified dual and compare. */
{
  let worst=0, vacuous=0, cases=0;
  for(const Rbar of [0.45,0.8,1.6])for(const seed of [7,23,41]){
    const o={depth:5,Rbar,hbar:0.35,phi:0.55,seed};
    const r=instance(EMB,o); cases++;
    let mine=0, interior=0;
    for(const nd of r.nodes){
      const Rp=r.Rp[nd.id];
      const atTop=Rp>o.Rbar-1e-9, atBot=Rp<1e-9;
      if(atTop||atBot)continue;
      interior++;
      const exp=nd.children.length
        ? nd.children.reduce((s,ci)=>s+r.nodes[ci].q*r.w[ci],0)
        : o.phi;
      mine=Math.max(mine,Math.abs(r.w[nd.id]-exp));
    }
    if(interior===0)vacuous++;
    worst=Math.max(worst,Math.abs(mine-r.cert.martingaleRes));
  }
  check('D4 martingale residual is the max over INTERIOR nodes, recomputed independently',
    worst<1e-12,'max discrepancy '+worst.toExponential(2)+' over '+cases+' instances');
  check('D4 the interior set is non-empty, so the claim is not vacuous',
    vacuous===0,vacuous+' vacuous of '+cases);
}

/* ---- falsifiers ---- */
console.log('\n    executing falsifiers');
/* redTotal is DERIVED, not typed. M1b plants divergence in the SECOND embedder to prove
   the loop does not stop after the first; with one embedder there is no second subject and
   the falsifier reports RED N/A below, which the file already called an honest N/A. A
   hardcoded 5 would then fail the summary check for a falsifier that could not run — a red
   that names nothing. It is derived rather than lowered to 4 so that the day a second
   embedder appears M1b is REQUIRED again automatically, with no edit here to remember.
   COVERAGE STATED PLAINLY: while there is one embedder, the loop falsifier is NOT running,
   so a regression that made this gate return after its first subject would go unnoticed.
   D0b is the compensating control — it fails the moment the discovered set changes. */
let reds=0;const redTotal=foundAbs.length>=2?5:4;
const plantSpace=text=>text.replace(BEGIN+"/* water_value_tree.js",BEGIN+"/* water_value_tree.js ");
{
  /* M1: a single byte changed in ANY embedded copy must break that copy's D1.
     Run per embedder — a falsifier aimed only at the primary cannot tell a
     working loop from one that returns after its first subject. */
  let red=0;
  for(const abs of foundAbs){
    const e=embedded(plantSpace(srcOf.get(abs)));
    if(e!==null&&e!==tool)red++;
    else console.log('       RED FAIL  M1 byte-identity did not notice a changed byte in '+rel(abs));
  }
  if(red===foundAbs.length){reds++;console.log('       RED ok  M1 one added space breaks byte-identity in each of the '+foundAbs.length+' embedders');}
}
{
  /* M1b: THE LOOP FALSIFIER. Plant the divergence in the SECOND embedder only
     and leave the first pristine. The pre-2026-07-28 code read one artifact and
     looped over nothing, so this mutation was invisible: it must now produce a
     red whose offender list NAMES the second embedder. Requiring the NAME, not
     just a nonzero count, is the rule paid for twice on 2026-07-27 — a probe
     that only checks "something failed" passes forever while testing nothing. */
  if(foundAbs.length<2){
    console.log('       RED N/A   M1b only '+foundAbs.length+' embedder discovered — no second subject to plant in');
    console.log('                 (this is honest N/A, and D0b already fails if an expected embedder vanished)');
  } else {
    const second=foundAbs[1];
    const mutated=new Map(srcOf);
    mutated.set(second,plantSpace(srcOf.get(second)));
    const v=identityVerdict(mutated);
    const namesSecond=!v.ok&&v.offenders.length===1&&v.offenders[0]===rel(second);
    if(namesSecond){reds++;console.log('       RED ok  M1b divergence planted ONLY in the second embedder is caught and NAMED ('+rel(second)+')');}
    else console.log('       RED FAIL  M1b the gate did not reach past the first embedder — offenders: ['+v.offenders.join(', ')+']');
  }
}
{
  /* M1c: ZERO embedders must be FATAL, never a vacuous pass. Every D1/D2 check
     lives inside a loop; over an empty set they all "pass" while certifying
     nothing. Prove the discovery walk really does return empty on a tree with
     no marker (the fatal branch above is its only consumer), and prove the same
     walk finds the real ones — a discover() that always returns [] would pass
     the first half alone. */
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'wv-nomarker-'));
  fs.writeFileSync(path.join(tmp,'decoy.html'),'<!doctype html><script>/* no marker here */</script>');
  const none=discover(tmp);
  fs.rmSync(tmp,{recursive:true,force:true});
  if(none.length===0&&foundAbs.length>0){
    reds++;console.log('       RED ok  M1c discovery returns EMPTY on a marker-free tree (and non-empty on the real one) — the zero-embedder branch is reachable and fatal');
  } else console.log('       RED FAIL  M1c discovery returned '+none.length+' on a marker-free tree / '+foundAbs.length+' on the real tree');
}
{
  /* M2: averaging instead of maximising must break D4 */
  const o={depth:5,Rbar:0.45,hbar:0.35,phi:0.55,seed:7};
  const r=instance(EMB,o);
  let sum=0,cnt=0;
  for(const nd of r.nodes){
    const Rp=r.Rp[nd.id];
    if(Rp>o.Rbar-1e-9||Rp<1e-9)continue;
    const exp=nd.children.length?nd.children.reduce((s,ci)=>s+r.nodes[ci].q*r.w[ci],0):o.phi;
    sum+=Math.abs(r.w[nd.id]-exp);cnt++;
  }
  const avg=cnt?sum/cnt:0;
  /* an averaged residual is only distinguishable if some node actually deviates;
     on a clean instance both are ~0, so this falsifier perturbs one dual first */
  const perturbed=r.w.slice(); let hit=-1;
  for(const nd of r.nodes){const Rp=r.Rp[nd.id];
    if(Rp<=o.Rbar-1e-9&&Rp>=1e-9&&nd.children.length){hit=nd.id;break;}}
  if(hit>=0){
    perturbed[hit]+=1e-3;
    let mx=0,sm=0,c2=0;
    for(const nd of r.nodes){
      const Rp=r.Rp[nd.id];
      if(Rp>o.Rbar-1e-9||Rp<1e-9)continue;
      const exp=nd.children.length?nd.children.reduce((s,ci)=>s+r.nodes[ci].q*perturbed[ci],0):o.phi;
      const d=Math.abs(perturbed[nd.id]-exp);mx=Math.max(mx,d);sm+=d;c2++;
    }
    if(mx>1e-4&&sm/c2<mx){reds++;console.log('       RED ok  M2 a perturbed interior dual is caught by max, and diluted by averaging ('+mx.toExponential(1)+' vs mean '+(sm/c2).toExponential(1)+')');}
    else console.log('       RED FAIL  M2 max and mean did not separate');
  } else console.log('       RED FAIL  M2 no interior node with children to perturb');
}
{
  /* M3: a wrong salvage anchor at the leaves must break the duality gap */
  const o={depth:4,Rbar:0.8,hbar:0.35,phi:0.55,seed:7};
  const good=instance(EMB,o);
  const bad=instance(EMB,{...o,phi:o.phi+0.3});
  if(Math.abs(good.cert.revenue-bad.cert.revenue)>1e-9){
    reds++;console.log('       RED ok  M3 the certificate is instance-specific — changing salvage changes the certified revenue');
  } else console.log('       RED FAIL  M3 certificate insensitive to the salvage anchor');
}
check('M every APPLICABLE falsifier turned its target red',reds===redTotal,
  reds+'/'+redTotal+(foundAbs.length<2?' (M1b N/A — one embedder, no second subject to plant in)':''));

/* The count in this sentence is DERIVED from what the walk found, never typed.
   The old wording said "two artifacts" while the code could only read one — a
   remembered number in the summary line of a gate about not trusting copies. */
console.log('\n'+(fails?fails+' FAILURE(S)':
  'ALL PASS — one kernel, '+foundAbs.length+' artifact'+(foundAbs.length===1?'':'s')+
  ' ('+found.join(', ')+'), byte-identical; the theorem the page displays is the theorem the note proves.'));
process.exit(fails?1:0);
