/* _root.js — find the TREE ROOT without counting `..`.

   WHY THIS FILE EXISTS. Batteries in this directory reach OUT of the project for three things
   that live at the tree root in every layout: `core/` (the shared toolkit), `lab/` (the JS
   instruments) and sibling projects under `research/`. They used to reach them with a fixed
   count of `..`, and that count is a fact about HOW DEEP THIS PROJECT SITS — which is not a
   property of the batteries at all, and which has now changed three times:

     academic/mfg-lab/tests   -> root was 3 up   (until 2026-07-29)
     mfg-lab/tests            -> root was 2 up   (the collapse)
     research/mfg-lab/tests   -> root is  3 up   (a paper inside research/, per the owner's rule)

   and in the PUBLIC EXPORT the same files sit at `mfg-lab/tests`, so the export and the monorepo
   disagreed by one for most of that history. Every disagreement was a live defect: measured
   2026-07-29, five files pointed above the export root and the PUBLISHED repo could not run its
   own `make check`.

   THE FIX IS TO STOP ASKING THE QUESTION. The root is the nearest directory above us that
   contains `core/` — true in the monorepo, true in the shared export, and the one marker that
   is at the root of both. Then a project can be moved to any depth and nothing here changes.

   WHY A MODULE AND NOT SIX INLINE COPIES. Six copies of a resolver is the duplication this
   repo's single-source rule exists to forbid, and the fingerprint scan would be right to dislike
   it. It is required by a PROJECT-RELATIVE path (`./_root.js`), which is the one kind of path
   that survives the project moving — so this file solves its own bootstrap problem.

   IT FAILS BY NAME. A resolver that returns undefined when it cannot find the root turns a dead
   dependency into an empty module, and this house has already paid for one battery that printed a
   green certificate having executed nothing. There is no fallback and no default.

   MIT licensed. Part of mfg-lab. */
'use strict';
const fs = require('fs');
const path = require('path');

/* The nearest ancestor containing `core/`. Marker, not a count. */
function treeRoot(from) {
  const start = from || __dirname;
  for (let d = start; ; d = path.dirname(d)) {
    if (fs.existsSync(path.join(d, 'core'))) return d;
    if (path.dirname(d) === d) break;
  }
  throw new Error('mfg-lab/tests/_root.js: no directory above ' + start + ' contains core/ — ' +
    'the tree root cannot be identified, so every out-of-project path would be a guess');
}

/* Resolve a root-relative path, e.g. rootPath('lab', 'contract.js'). Asserts the ROOT is real;
   the target itself may legitimately be absent and each caller reports that in its own words. */
function rootPath(...segs) { return path.join(treeRoot(), ...segs); }

module.exports = { treeRoot, rootPath };
