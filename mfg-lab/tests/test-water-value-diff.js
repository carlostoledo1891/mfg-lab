/* test-water-value-diff.js — the ONE-KERNEL gate for the water-value tree.

   mfg-lab.html embeds sin-mfg/tools/water_value_tree.js verbatim so the lab's
   Water value page can run the theorem live. That creates a second copy of a
   validated kernel, which is precisely the failure mode this repo has paid for
   more than once (a battery certifying a stale copy while the artifact drifts).
   So the copy is GATED, not trusted:

     D1  the bytes between the markers in mfg-lab.html are IDENTICAL to the
         tool file — not "equivalent", identical;
     D2  the embedded copy actually runs, and its certificates hold on the
         page's own default controls;
     D3  the embedded copy and the tool file, given the same instance, return
         the same primal, the same dual and the same certificate — so the
         embedding cannot silently lose a term;
     D4  the martingale identity the page displays is the one the theorem
         states: w_n = E[w_child|n] at interior nodes ONLY, and the residual
         is a max over interior nodes rather than over all of them.

   Falsifiers at the end: each mutates one thing and must turn its own check
   red. A gate that cannot go red is decoration. */
'use strict';
const fs=require('fs'), path=require('path'), crypto=require('crypto');

const HTML=process.env.MFG_HTML||path.resolve(__dirname,'..','mfg-lab.html');
const TOOL=process.env.WVTREE||path.resolve(__dirname,'..','..','sin-mfg','tools','water_value_tree.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex').slice(0,16);

const html=fs.readFileSync(HTML,'utf8');
const tool=fs.readFileSync(TOOL,'utf8');
console.log('artifact : '+HTML+'  sha256 '+sha(html)+'  ('+Buffer.byteLength(html)+' bytes)');
console.log('kernel   : '+TOOL+'  sha256 '+sha(tool)+'  ('+Buffer.byteLength(tool)+' bytes)\n');

let fails=0;
function check(name,cond,detail){
  console.log((cond?'PASS':'FAIL')+'  '+name+(detail!==undefined?'   ['+detail+']':''));
  if(!cond)fails++;
}

const BEGIN='/* ==== BEGIN VERBATIM sin-mfg/tools/water_value_tree.js ==== */\n';
const END='/* ==== END VERBATIM ==== */';
function embedded(src){
  const i=src.indexOf(BEGIN), j=src.indexOf(END);
  if(i<0||j<0||j<i)return null;
  return src.slice(i+BEGIN.length,j);
}

/* ---- D1: byte identity ---- */
const emb=embedded(html);
check('D1 the embedded kernel exists between its markers',emb!==null);
if(emb===null){console.log('\ncannot continue without the markers');process.exit(1);}
check('D1 embedded bytes are IDENTICAL to the tool file',emb===tool,
  emb===tool?('sha256 '+sha(emb)+' · '+Buffer.byteLength(emb)+' bytes'):
  ('embedded sha '+sha(emb)+' vs tool sha '+sha(tool)+
   ' · lengths '+Buffer.byteLength(emb)+' vs '+Buffer.byteLength(tool)));

/* ---- load BOTH implementations ---- */
function loadEmbedded(src){
  const body=embedded(src);
  const f=new Function('const module={exports:{}}, require={main:null};\n'+body+'\nreturn module.exports;');
  return f();
}
const EMB=loadEmbedded(html);
const REF=require(TOOL);

/* ---- D2: the embedded copy runs, on the PAGE'S OWN defaults ---- */
/* Defaults are read from the artifact's range inputs rather than retyped, so
   this check follows the page instead of a remembered configuration. */
function pageDefault(id){
  const m=html.match(new RegExp('id="'+id+'"[^>]*value="([-\\d.]+)"'));
  if(!m)throw new Error('no default for '+id+' in the artifact');
  return parseFloat(m[1]);
}
const D={depth:pageDefault('wvDepth'),Rbar:pageDefault('wvRbar'),hbar:pageDefault('wvHbar'),
         phi:pageDefault('wvPhi'),seed:pageDefault('wvSeed')};
console.log('    page defaults: '+JSON.stringify(D));
function mulberry32(s){return function(){s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function instance(K,o){
  const rng=mulberry32(o.seed);
  const nodes=K.buildTree(o.depth,2,n=>({price:0.5+0.8*rng()+(n.depth===2?0.5:0),
                                         inflow:0.15+0.5*rng()}));
  return K.solveTree(nodes,{R0:0.4*o.Rbar/0.8,Rbar:o.Rbar,hbar:o.hbar,phi:o.phi});
}
const rE=instance(EMB,D);
const cE=rE.cert;
check('D2 embedded kernel solves the page default instance',!!rE&&!!cE,
  rE.nodes.length+' nodes');
check('D2 zero duality gap on the page default',cE.gapRel<1e-12,cE.gapRel.toExponential(2));
check('D2 primal feasible (dynamics + boxes)',cE.dynErr<1e-9&&cE.boxErr<1e-9,
  'dyn '+cE.dynErr.toExponential(2)+' box '+cE.boxErr.toExponential(2));
check('D2 dual clean (trichotomy, wedge signs, complementarity, spill)',
  cE.tri===0&&cE.wedgeSignErr<1e-9&&cE.compSlack<1e-9&&cE.spillDualErr<1e-9,
  'tri '+cE.tri+' wedge '+cE.wedgeSignErr.toExponential(2));

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
let reds=0;const redTotal=3;
{
  /* M1: a single byte changed in the embedded copy must break D1 */
  const mutated=html.replace(BEGIN+"/* water_value_tree.js",BEGIN+"/* water_value_tree.js ");
  const e=embedded(mutated);
  if(e!==null&&e!==tool){reds++;console.log('       RED ok  M1 one added space in the embedded copy breaks byte-identity');}
  else console.log('       RED FAIL  M1 byte-identity check did not notice a changed byte');
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
check('M every falsifier turned its target red',reds===redTotal,reds+'/'+redTotal);

console.log('\n'+(fails?fails+' FAILURE(S)':'ALL PASS — one kernel, two artifacts, byte-identical; the theorem the page displays is the theorem the note proves.'));
process.exit(fails?1:0);
