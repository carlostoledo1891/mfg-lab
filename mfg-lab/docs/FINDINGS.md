# Floor study — measured, not asserted (session 2026-07-19/20)

## Method
M1 kernel extracted brace-balanced from mfg-lab.html into `kernel_param.js`
(grid parameterized). VALIDATED against in-page values before use:
  extracted @120x240 -> iter 153, eps 7.382e-11, mass 5.251e-14
  in-page reference  -> iter 153, eps 7.38e-11,  mass 5.25e-14   (exact match)

## Result 1 — eps IS first-order in the grid, but with a tiny constant
grid refinement (converged, res~1e-6):
  30x60   h+dt 5.11e-2  |eps| 3.64e-10
  60x120  h+dt 2.53e-2  |eps| 1.66e-10
  120x240 h+dt 1.26e-2  |eps| 7.38e-11
  240x480 h+dt 6.27e-3  |eps| 3.07e-11
observed order in (h+dt): 1.11, 1.16, 1.26  -> first order CONFIRMED.
BUT |eps|/(h+dt) ~ 5e-9, i.e. the naive bound "floor = h+dt = 1.26e-2"
is ~9 ORDERS above the actual eps. Printing it would declare a genuinely
converged eps=7.4e-11 "below the floor / meaningless". VACUOUS BOUND.

## Result 2 — eps is ITERATION-limited, not grid-limited
fixed 120x240, varying iteration budget:
  res 3.03e-3 -> eps 2.40e-7
  res 1.52e-4 -> eps 1.62e-8
  res 8.32e-6 -> eps 7.14e-10
  res 9.95e-7 -> eps 7.38e-11
power-law exponent eps~res^p: 0.90, 1.08, 1.07  -> LINEAR in the residual.
eps saturates exactly when the residual saturates (153 iters); more budget
changes nothing. The residual is eps's honest companion number.

## Result 3 — the proportionality constant is NOT universal
51 converged corners (sigma x c x gamma x congestion, 60x120):
  C = |eps|/res  ranges 9.0e-7 .. 2.2e-3  = 2400x spread.
=> No single calibrated constant is defensible. We must NOT invent one.

## Result 4 — the hardcoded 1e-4 gate
`const small=Math.abs(S.eps)<1e-4` (2D herding branch) is a magic number
disconnected from the grid. Prose asserts "consistency floor ~ 1e-4" while
the 2D grid (NG=48,NT=96) gives h+dt=3.17e-2 (317x larger).
Stalled-regime probe (1D analogue, beta sweep):
  beta 0.20: res 3.53e-1, eps 2.65e-1, ratio 0.75  <- genuinely stalled
  beta 0.55: res 9.80e-7, eps 4.92e-11, ratio 5e-5 <- genuinely converged
The 1e-4 gate separates these only by luck. The DEFENSIBLE discriminator
is the residual (already computed, already displayed), not a fabricated
absolute floor on eps.

## CONCLUSION — plan revised
DO NOT print "floor = O(h+dt)". It is vacuous (9 orders too large) and
would weaken the certificate.
DO: (a) delete the fabricated 1e-4 literal and the stale "~1e-4" prose;
    (b) gate the "orbits an equilibrium" claim on the RESIDUAL, which is
        what actually limits eps;
    (c) state eps's measured first-order grid behaviour in the Method tab
        as a refinement study (real, reproducible), not as a bound.

## Result 5 — the harness was validating a stale file (process bug, found late)
`smoke.js` hardcoded `readFileSync('/home/claude/mfg/script.js')` — a path from
an earlier session's scratch dir, NOT derived from the artifact under test.
Every "23/23 green" run after the edits was reading an UNPATCHED script.
The failures I first blamed on my own new checks were the harness reporting on
the wrong file; the checks were right all along.
FIX: smoke.js now extracts <script> from the HTML at run time
(`MFG_HTML` env override for mutation testing) and prints the path + byte count
on every run. A hardcoded-path harness can silently certify the wrong artifact —
this is the same species of error as a fake certificate, and it is now
structurally impossible.

## Result 6 — mutation testing (new house practice)
A green suite proves nothing unless it can go red. Deliberately reverted each
fix and re-ran:
  mutant1 (eps gate back to 1e-4 literal)      -> 27/29  CAUGHT
  mutant2 (mass back to terminal-row, v1)      -> 28/29  CAUGHT (after strengthening)
  mutant3 (mass terminal-row, row spoofed NT)  -> 28/29  CAUGHT (after strengthening)
  true artifact                                 -> 29/29
First version of the mass check did NOT catch mutant2/3: at rest the terminal
row IS the max, so both implementations print 5.25e-14 and are indistinguishable.
Measured that the rows diverge MID-ITERATION (19 of 400 frames), so the check
now samples across 400 frames and requires both agreement at every frame AND
at least one off-terminal max. Magnitude checks are weak; semantic checks bite.

## Old vs new — 22 displayed certificates compared under identical stubs
21 identical, 1 changed. No math was touched and the numbers prove it.
The single change is a RETRACTION: the 2D herding verdict no longer claims
"orbits a genuine equilibrium" at a 4.27e-2 residual.
The artifact now claims less and proves more.
