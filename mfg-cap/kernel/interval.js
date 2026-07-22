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
module.exports = require('../../eqcert/src/interval.js');
