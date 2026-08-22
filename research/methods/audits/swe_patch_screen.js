/* swe_patch_screen.js — a FREE, reproducible screen of SWE-bench Verified submissions.
   Claimless probe. It asks ONE question from git-tracked data alone (no AWS, no Docker, no models):
   among the patches a model gets marked RESOLVED, how far do they diverge IN SHAPE from the human
   gold fix? Shape = (files touched, lines changed, hunks). Data: results/results.json (resolved
   ids) + results/patch_stats.json (pred vs gold shape, aligned to resolved[]). This is a SCREEN,
   not a verdict: shape divergence is not proof of anything — it flags candidates for the deeper
   (AWS) diff audit, and adds an axis the pass/fail leaderboard hides. */
'use strict';
const fs = require('fs');
const OUT = __dirname;
const API = 'https://api.github.com/repos/SWE-bench/experiments/contents/evaluation/verified';
const RAW = (sub, f) => `https://raw.githubusercontent.com/SWE-bench/experiments/main/evaluation/verified/${sub}/results/${f}`;

async function getJSON(url){ try{ const r=await fetch(url); if(!r.ok) return null; return await r.json(); }catch{ return null; } }
async function getText(url){ try{ const r=await fetch(url); if(!r.ok) return null; return await r.text(); }catch{ return null; } }

async function batch(items, n, fn){ const out=[]; for(let i=0;i<items.length;i+=n){ out.push(...await Promise.all(items.slice(i,i+n).map(fn))); } return out; }
const size = (la,lr)=> (la||0)+(lr||0);

(async () => {
  const listing = await getJSON(API);
  const subs = listing.filter(x=>x.type==='dir').map(x=>x.name);
  console.log(`verified submissions: ${subs.length}`);

  const rows = await batch(subs, 8, async (sub) => {
    const res = await getJSON(RAW(sub,'results.json'));
    const ps  = await getJSON(RAW(sub,'patch_stats.json'));
    return { sub, res, ps };
  });

  // coverage
  const withPS = rows.filter(r=>r.ps && r.res && Array.isArray(r.res.resolved));
  console.log(`have results.json: ${rows.filter(r=>r.res).length} · have patch_stats.json: ${rows.filter(r=>r.ps).length} · usable(both+aligned-check next): ${withPS.length}`);

  // build a global gold-shape map by instance_id to VALIDATE the resolved[]<->patch_stats alignment
  const goldByIid = {};      // iid -> "files|lines|hunks"
  let alignOK=0, alignBad=0, conflicts=0;
  const models = [];
  for (const {sub,res,ps} of withPS) {
    const R = res.resolved;
    const P = ps.preds, G = ps.golds;
    if (!P || !G || P.lines_added.length !== R.length) { alignBad++; continue; }
    alignOK++;
    let extreme=0, moreFiles=0, sizeRatios=[], fileRatios=[], flags=[];
    for (let i=0;i<R.length;i++){
      const iid=R[i];
      const gf=G.num_files[i], gl=size(G.lines_added[i],G.lines_removed[i]);
      const pf=P.num_files[i], pl=size(P.lines_added[i],P.lines_removed[i]);
      // cross-submission gold consistency check (validates ordering empirically)
      const key=`${gf}|${gl}|${G.num_hunks[i]}`;
      if (goldByIid[iid]===undefined) goldByIid[iid]=key; else if (goldByIid[iid]!==key) conflicts++;
      const fr = pf/Math.max(gf,1), sr = pl/Math.max(gl,1);
      sizeRatios.push(sr); fileRatios.push(fr);
      if (pf>gf) moreFiles++;
      const isExtreme = fr>=3 || sr>=5 || (pl<=1 && gl>=10);
      if (isExtreme){ extreme++; flags.push({pf, gf, pl, gl, fr:+fr.toFixed(2), sr:+sr.toFixed(2)}); } // NO iid: resolved[] and patch_stats order differ (proven below), so per-instance attribution is impossible from free data
    }
    const med = a => { const s=[...a].sort((x,y)=>x-y); return s.length? s[Math.floor(s.length/2)]:0; };
    models.push({
      sub, n_resolved:R.length,
      median_size_ratio:+med(sizeRatios).toFixed(2),
      median_file_ratio:+med(fileRatios).toFixed(2),
      pct_more_files:+(100*moreFiles/R.length).toFixed(1),
      pct_extreme:+(100*extreme/R.length).toFixed(1),
      extreme_count:extreme,
      flags: flags.sort((a,b)=>b.sr-a.sr).slice(0,5)
    });
  }
  console.log(`alignment: ${alignOK} count-aligned, ${alignBad} length-mismatch. gold-consistency conflicts: ${conflicts}.`);
  console.log(conflicts>0
    ? `  -> ${conflicts} conflicts PROVE resolved[] and patch_stats are NOT in the same order. Per-instance attribution is impossible from free data; only AGGREGATE shape-divergence below is valid (each pred vs its OWN gold within a submission).`
    : `  -> ordering assumption holds; per-instance attribution possible.`);

  models.sort((a,b)=>b.pct_extreme-a.pct_extreme);
  console.log('\n== models ranked by % of resolved patches that diverge EXTREMELY in shape from the gold fix ==');
  console.log('  pct_extreme  medSizeR  %moreFiles  n_res  submission');
  for (const m of models.slice(0,15))
    console.log(`  ${String(m.pct_extreme).padStart(6)}%   ${String(m.median_size_ratio).padStart(6)}   ${String(m.pct_more_files).padStart(7)}%   ${String(m.n_resolved).padStart(4)}   ${m.sub}`);

  fs.writeFileSync(`${OUT}/screen-results.json`, JSON.stringify({
    generated_from:'SWE-bench/experiments verified (git-tracked results.json + patch_stats.json)',
    n_submissions:subs.length, n_with_patch_stats:rows.filter(r=>r.ps).length, n_aligned:alignOK,
    gold_consistency_conflicts:conflicts, models
  }, null, 1));
  console.log('\nwrote screen-results.json');
})();
