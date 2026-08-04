/* interval.js — mfg-cap's view of the shared interval arithmetic.

   THE IMPLEMENTATION LIVES IN eqcert/src/interval.js AND ONLY THERE. This file
   is a re-export, so there is exactly one outward-rounded interval library in
   this repository rather than the two that existed before the toolkit was
   factored out (one here, one inline in the Wardrop battery). Editing a copy
   is how the two silently drift; there is no copy to edit.

   When mfg-cap is exported as a standalone repository, tools/build-artifact.js
   vendors eqcert alongside it and tests/test-artifact.js asserts the vendored
   bytes are identical to the source.

   MIT licensed. Part of mfg-cap. */
'use strict';
/* RESOLVED BY UPWARD SEARCH, NOT BY A COUNT OF `..`. There are THREE layouts this file must work
   in and no fixed ascent is correct in more than two of them:
     monorepo   research/mfg-cap/kernel  -> eqcert is 3 up
     export     mfg-cap/kernel           -> eqcert is 2 up
     standalone mfg-cap/kernel           -> eqcert is VENDORED beside the project by build-artifact
   Measured 2026-07-29: `require('../../../eqcert/src/interval.js')` was correct here and pointed
   ABOVE THE EXPORT ROOT in the shared repo, so `node mfg-cap/tests/test-cap.js` died
   MODULE_NOT_FOUND — and the published repo's own Makefile runs exactly that inside the PUBLIC `make
   check`. The published repo's own ritual could not run.
   Walking up until the library is found is correct in all three, and it FAILS BY NAME rather than
   resolving to nothing: a guard that quietly returns undefined would make a dead dependency look
   like an empty module. */
const fs = require('fs');
const path = require('path');
function upward(from, rel) {
  for (let d = from; ; d = path.dirname(d)) {
    const hit = path.join(d, rel);
    if (fs.existsSync(hit)) return hit;
    if (path.dirname(d) === d) break;
  }
  throw new Error('mfg-cap/kernel/interval.js: could not find ' + rel + ' in any directory above ' +
                  from + ' — eqcert is neither at the tree root nor vendored beside this project');
}
module.exports = require(upward(__dirname, path.join('eqcert', 'src', 'interval.js')));
