#!/usr/bin/env python3
"""
test-layout.py — headless-browser layout-stability battery for mfg-lab.html.

House rule is "battery before pixels"; this is the battery FOR the pixels.
Earlier sessions recorded "no headless browser available" — that was wrong:
playwright + chromium run fine here. Anything visual claimed from now on
should be measured by this file, not asserted.

38 checks, MEASURED 2026-07-31 by counting the PASS/FAIL lines of a full run —
not remembered. (37 on 2026-07-28, before section 6b gated the retired '/' address;
46 earlier that day, before M3 retired the section-7 subject;
44 on 2026-07-27; 28 before section 7 was added; long stated as 16.)
The count is now PINNED as `EXPECTED_CHECKS` and asserted by the last check in the
file, so the battery can no longer quietly run fewer checks than it advertises.

Section 7 is the port of three assertions rescued from an archived sibling battery.
It used to run over the target AND `onepager.html`, the only page in this tree that
exercised the mechanisms those assertions test. M3 DELETED THAT PAGE on 2026-07-28
and, in the same commit, RETIRED the nine checks it owned — deliberately, by name,
with the lost coverage itemised in the section-7 header. Nine checks is the whole
difference between 46 and 37. Read that header before adding anything here: it
records what this battery can no longer see, and what would have to exist for the
coverage to come back.

Run:  python3 test-layout.py [path-to-html]
Default target is ../mfg-lab.html relative to this script, so it works from any
cwd (the battery lives in mfg-lab/tests/, the artifact one level up).
"""
import pathlib, sys, json
from playwright.sync_api import sync_playwright

_HERE = pathlib.Path(__file__).resolve().parent
TARGET = sys.argv[1] if len(sys.argv) > 1 else str(_HERE.parent / 'index.html')
URL = 'file://' + str(pathlib.Path(TARGET).resolve())
# The artifact is routed: pages carry the argument, #/route addresses each one.
# Checks that drive a specific experiment must ask for its route, exactly as a
# reader following a link would. ROUTES is also swept for layout stability, so
# the narrative pages are gated like the instrument pages.
URL_BENCH = URL + '#/bench&t=1'
# '/' IS NOT IN THIS LIST, and its absence is the point. It was a real route until
# 2026-07-30, when the landing page it served (pgStart) was deleted for competing
# with the site homepage; the router now folds '/' and no-hash into '/bench'. This
# sweep asserts a route resolves to a page AND is marked in the nav, and a retired
# route has no nav button by construction, so leaving '/' here made the battery red
# for six hours against a deletion that was deliberate. It was NOT dropped silently:
# RETIRED_ROUTE below still gates the address, because a reader who bookmarked '#/'
# must land somewhere rather than on a blank page.
ROUTES = ['/wardrop', '/price', '/water-value', '/random-supply', '/bench']
RETIRED_ROUTE = '/'
LONG = ('stopped at 500 iterations, residual 4.27e-2 — anti-monotone coupling, no '
        'fictitious-play guarantee. Asymmetry 0.839; the iteration does not certify '
        'an equilibrium here.')
WIDTHS = [390, 640, 900, 1280, 1600]

# The advertised size of this battery. It is a CLAIM, so it is measured and then
# asserted (last check in the file) rather than written in the docstring and
# trusted. A check that stops running is otherwise indistinguishable from a check
# that passes — which is precisely how section 7 was about to lose nine of these.
EXPECTED_CHECKS = 38          # measured 2026-07-31 after 6b; includes the guard itself

fails = []
ran = []
def check(name, cond, detail=''):
    print(('PASS  ' if cond else 'FAIL  ') + name + (f'   [{detail}]' if detail else ''))
    ran.append(name)
    if not cond: fails.append(name)

def shout(lines):
    """Unmissable, on both streams — a lost gate must not scroll past as prose.

    UNCALLED since M3 (2026-07-28): its one caller was section 7's absent-subject
    alarm, which fired, was acted on, and was retired with the subject. Kept
    deliberately. The next assertion in this file to lose its subject should
    shout the same way rather than shrink the total quietly, and re-deriving
    this is how that lesson gets skipped.
    """
    bar = '#' * 78
    for ln in [bar] + ['# ' + l for l in lines] + [bar]:
        print(ln)
        print(ln, file=sys.stderr)

with sync_playwright() as p:
    b = p.chromium.launch()

    # 1. Status wrapping must never move the canvas, at any width.
    for w in WIDTHS:
        pg = b.new_page(viewport={'width': w, 'height': 900})
        pg.goto(URL_BENCH, wait_until='load'); pg.wait_for_timeout(1600)
        r = pg.evaluate("""(long) => {
            const s=document.querySelector('#sec1 .status');
            const c=document.querySelector('#sec1 canvas');
            const top=()=>Math.round(c.getBoundingClientRect().top);
            s.textContent='idle'; const a=top();
            s.textContent=long;   const b2=top();
            return {move:Math.abs(b2-a),
                    overflowX:document.documentElement.scrollWidth
                              -document.documentElement.clientWidth};
        }""", LONG)
        check(f'{w}px: long status does not move the canvas', r['move'] == 0, f"{r['move']}px")
        check(f'{w}px: no horizontal overflow', r['overflowX'] <= 0, f"{r['overflowX']}px")
        pg.close()

    # 2. Fonts resolve to the intended roles (sans + mono only).
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.goto(URL, wait_until='load'); pg.wait_for_timeout(1800)
    f = pg.evaluate("""() => {
        const g=(s,p)=>{const e=document.querySelector(s);return e?getComputedStyle(e)[p]:'';};
        return {body:g('body','fontFamily'), h1:g('h1','fontFamily'),
                val:g('.ro .v','fontFamily'), num:g('.ro .v','fontVariantNumeric')};
    }""")
    check('body is a sans stack, no serif', 'Inter' in f['body'] and 'Spectral' not in f['body'])
    check('headings are Inter Tight', 'Inter Tight' in f['h1'])
    check('certificate values are mono', 'Plex Mono' in f['val'] or 'monospace' in f['val'])
    check('certificate values use tabular figures', 'tabular-nums' in f['num'], f['num'])

    # 3. Real CLS while driving the UI must stay well inside the "good" band.
    #
    #    THIS GATE USED TO FLAKE (0.104 one run, 0.057 the next, artifact
    #    untouched). The standing rule for a flaky gate: settle the page before
    #    sampling, or state the threshold as a measured distribution — do NOT
    #    just raise it. Both were done, after finding the cause rather than
    #    guessing at it:
    #
    #      * ATTRIBUTION. Splitting the measurement showed 100% of the shift
    #        happens BEFORE the first click; solving, every bench tab switch and
    #        every route change contribute exactly 0.0000. The `buffered:true` observer had been
    #        folding page-load shifts into the "solve" bucket and hiding that.
    #      * CAUSE, PROVED not assumed. With the Google Fonts requests aborted,
    #        CLS is exactly 0.0000 on 10/10 runs; with them allowed it ranges
    #        0.017-0.107. The stylesheet was requested with `display=swap`,
    #        which repaints the whole page in the web font after first paint —
    #        a FOUT reflow. sin-mfg.html already used `display=optional`;
    #        mfg-lab.html now does too, so all three artifacts agree.
    #        Measured after the change: max 0.0471 over 10 runs, 0 exceedances.
    #      * DISTRIBUTION, not a single draw. A shift that depends on whether a
    #        font arrives before first paint is inherently a race, so one sample
    #        cannot certify it. Three loads are taken and the WORST is asserted.
    samples = []
    for _ in range(3):
        s_pg = b.new_page(viewport={'width': 1280, 'height': 900})
        s_pg.goto(URL_BENCH, wait_until='load'); s_pg.wait_for_timeout(1500)
        s_pg.evaluate("""() => {window.__cls=0;
            new PerformanceObserver(l=>{for(const e of l.getEntries())
              if(!e.hadRecentInput) window.__cls+=e.value;}).observe({type:'layout-shift',buffered:true});}""")
        s_pg.click('#solveBtn'); s_pg.wait_for_timeout(2500)
        for t in ['lq','2d','st','1']:
            s_pg.click(f'.tab[data-tab="{t}"]'); s_pg.wait_for_timeout(400)
        for r in ROUTES:
            # route via the router, not a nav click: the sections now live in
            # dropdown menus that are display:none until hovered.
            s_pg.evaluate("(r) => { location.hash = '#' + r; }", r); s_pg.wait_for_timeout(400)
        samples.append(s_pg.evaluate("() => +window.__cls.toFixed(5)"))
        s_pg.close()
    cls = max(samples)
    check('cumulative layout shift below the 0.1 "good" threshold (worst of 3 loads)',
          cls < 0.1, f"worst {cls} of {samples}")

    # 4. Tab 02 (LQ) — the one kernel the Node harness CANNOT reach, because it
    #    is setTimeout-driven. A real browser runs its timers, so the grid study
    #    and its observed-order claim are verifiable here and nowhere else.
    pg3 = b.new_page(viewport={'width': 1280, 'height': 900})
    pg3.goto(URL_BENCH, wait_until='load'); pg3.wait_for_timeout(1500)
    pg3.click('.tab[data-tab="lq"]'); pg3.wait_for_timeout(400)
    pg3.click('#lqRunBtn'); pg3.wait_for_timeout(45000)
    lq = pg3.evaluate("() => {"
        "const s=document.querySelector('#seclq .status');"
        "const rows=[...document.querySelectorAll('#lqTable tbody tr')].map("
        "tr=>[...tr.children].map(td=>td.textContent.trim()));"
        "return {status:s?s.textContent:'', orders:rows.map(r=>r[r.length-1])};}")
    finest = lq['orders'][-1] if lq['orders'] else ''
    check('LQ grid study completes', 'study complete' in lq['status'],
          lq['status'][:70])
    ok_order = finest not in ('', '—') and float(finest) >= 0.95
    check('LQ observed order converges to first order (>=0.95)', ok_order,
          f'finest {finest}')
    pg3.close()

    # 5. No console errors beyond the sandbox's blocked font fetch.
    errs = []
    pg2 = b.new_page(viewport={'width': 1280, 'height': 900})
    pg2.on('pageerror', lambda e: errs.append(str(e)))
    pg2.goto(URL_BENCH, wait_until='load'); pg2.wait_for_timeout(2500)
    pg2.click('#solveBtn'); pg2.wait_for_timeout(2000)
    for r in ROUTES:
        pg2.evaluate("(r) => { location.hash = '#' + r; }", r); pg2.wait_for_timeout(500)
    check('no uncaught page errors', not errs, '; '.join(errs)[:120])

    # 6. Routing is the new navigation, so it is gated like everything else:
    #    every route must resolve to a visible page with no horizontal overflow
    #    at every width, and a deep link must land on the page it names.
    for w in WIDTHS:
        pg4 = b.new_page(viewport={'width': w, 'height': 900})
        worst_ov, bad = 0, []
        for r in ROUTES:
            pg4.goto(URL + '#' + r, wait_until='load'); pg4.wait_for_timeout(700)
            res = pg4.evaluate("""(route) => {
                const nav=document.querySelector(`.nav[data-route="${route}"]`);
                const pages=[...document.querySelectorAll('.page')];
                const on=pages.filter(p=>p.classList.contains('active'));
                return {visible: on.length===1 && on[0].offsetHeight>0,
                        navMarked: !!nav && nav.classList.contains('active'),
                        overflowX: document.documentElement.scrollWidth
                                   - document.documentElement.clientWidth};
            }""", r)
            if not res['visible'] or not res['navMarked']: bad.append(r)
            worst_ov = max(worst_ov, res['overflowX'])
        check(f'{w}px: every deep link lands on exactly one visible page',
              not bad, 'broken: ' + ','.join(bad) if bad else f'{len(ROUTES)} routes')
        check(f'{w}px: no horizontal overflow on any route', worst_ov <= 0, f'{worst_ov}px')
        pg4.close()

    # 6b. The RETIRED address must still resolve. Deleting a route deletes its nav
    #     button, not the links and bookmarks already pointing at it, so '#/' is
    #     gated for landing rather than for being marked in a nav it left.
    pg5 = b.new_page(viewport={'width': 1280, 'height': 900})
    pg5.goto(URL + '#' + RETIRED_ROUTE, wait_until='load'); pg5.wait_for_timeout(700)
    res = pg5.evaluate("""() => {
        const on=[...document.querySelectorAll('.page')].filter(p=>p.classList.contains('active'));
        return {n:on.length, id:on.length?on[0].id:'', h:on.length?on[0].offsetHeight:0};
    }""")
    check(f'the retired {RETIRED_ROUTE} address still lands on exactly one visible page',
          res['n'] == 1 and res['h'] > 0 and res['id'] == 'pgBench',
          f"{res['n']} page(s) active: {res['id']}")
    pg5.close()

    # ---------------------------------------------------------------------
    # 7. PORTED FROM AN ARCHIVED SIBLING BATTERY, 2026-07-27.
    #
    #    A sibling browser battery, since retired with its project,
    #    held them. It held three assertions that existed NOWHERE ELSE in this
    #    tree, and each was paid for by a real defect recorded in the
    #    project's internal failure log. Deleting the battery would
    #    have deleted the only copy. The MECHANISMS transfer; that
    #    selectors (.rv, .split, .hdr, data-theme) do not, so each is
    #    re-aimed at what the academic pages actually do.
    #
    #    They used to run over the target AND its sibling onepager.html,
    #    because onepager.html was where all three mechanisms were live (it
    #    carried html{scroll-behavior:smooth}, two `new IntersectionObserver`s
    #    driving lazy module init, and two iframes built by srcdoc surgery).
    #
    #    ==================================================================
    #    THE SUBJECT WAS DELETED, AND THESE NINE CHECKS ARE RETIRED.
    #    M3, 2026-07-28, same commit as the deletion. This is option (ii) of
    #    the two the previous header named. IT IS A LOSS, WRITTEN DOWN.
    #    ==================================================================
    #
    #    WHAT HAPPENED. The previous version of this header made the subject
    #    MANDATORY rather than optional: absent, it shouted and emitted the
    #    nine checks it owned as NAMED failures instead of silently shrinking
    #    the battery from 46 to 37. That hardening did its job — it is why
    #    this deletion had to be decided instead of just happening — and it
    #    has now been spent. Keeping it would leave nine permanent reds
    #    describing a page that no longer exists, and a permanently red gate
    #    is a muted gate.
    #
    #    WHY NOT RE-POINT. Re-measured independently at M3, over every
    #    tracked .html in the tree (`git ls-files '*.html'`, grep for
    #    scroll-behavior / IntersectionObserver / srcdoc):
    #
    #      onepager.html  scroll-behavior 2 · IntersectionObserver 4 · srcdoc 1
    #      EVERY OTHER TRACKED PAGE IN THE TREE           0 · 0 · 0
    #
    #    That includes both candidates a re-pointing would reach for:
    #    site/index.html (114 KB, the HOME page — long, and entirely static)
    #    and academic/mfg-lab/index.html (296 KB, the surviving flagship).
    #    Neither carries a single one of the three, in any encoding.
    #
    #    Aiming "the measured stop is never the computed one" at a page whose
    #    computed bottom EQUALS its measured stop by construction manufactures
    #    a passing assertion with no power — strictly worse than losing the
    #    check, because the loss is visible and the powerless pass is not.
    #    So it was not done. A green run was available and was refused.
    #
    #    THE COVERAGE THIS TREE NO LONGER HAS. Nine checks, by name:
    #      1 onepager.html: still exercises the mechanisms these ported
    #        assertions test          (the subject's own licence check)
    #      2 onepager.html: prose elements found to compare
    #      3 onepager.html: page JS preserves every prose string exactly
    #      4 onepager.html: any fxOrig-recording effect preserves its text
    #      5 onepager.html: scroll drive reaches the bottom by settling,
    #        not by guard
    #      6 onepager.html: the measured stop is the page bottom (never the
    #        computed one)
    #      7 onepager.html: nothing left masked after the whole page has been
    #        scrolled
    #      8 onepager.html: a scripted scroll settles before it is sampled
    #      9 onepager.html: the instant scroll landed on its target, not
    #        part-way
    #
    #    Checks 2-4 and 5-9 SURVIVE for mfg-lab.html — the loops below still
    #    run them over the target. What is gone is their POWER, and that is
    #    the honest statement of the loss:
    #      * (a) prose-survives-the-boot-effects is still asserted, but no
    #        page left performs srcdoc iframe surgery, so no DOM-REWRITING
    #        effect is being survived. This tree can no longer prove that a
    #        line-splitter-class defect ("frente ." for "frente.") would be
    #        caught. That was the archived battery's real defect, and it is
    #        the coverage most worth restoring.
    #      * (b) measure-the-stop-never-compute-it is still asserted, but
    #        mfg-lab.html does not GROW while scrolled, so measured and
    #        computed agree trivially. The 1321px gap that made this check
    #        mean something (17024 computed vs 18345 real) has no carrier.
    #      * (c) a-scripted-scroll-settles-before-it-is-sampled is still
    #        asserted, but no page sets scroll-behavior:smooth, so nothing
    #        animates and the two samples agree trivially.
    #
    #    HOW TO GET IT BACK — and this is a real instruction, not a gesture.
    #    The day any shipped page acquires ONE of the three (a smooth-scrolling
    #    HOME, a lazily-initialised module list, an embedded srcdoc demo), add
    #    it to PORTED and restore N_POWER against it so the licence is
    #    re-earned every run. Do NOT restore the checks without N_POWER: the
    #    licence check is what stops this section from drifting back into a
    #    powerless green. And re-measure EXPECTED_CHECKS and the docstring
    #    together, never one of them.
    #    ------------------------------------------------------------------

    # Check names live in templates so the loop below cannot drift from what
    # it reports. N_POWER is deliberately absent: it existed to re-earn the
    # deleted subject's licence every run, and there is no subject to license.
    N_FOUND   = '{p}: prose elements found to compare'
    N_COUNT   = '{p}: page JS does not add or remove prose elements'
    N_EXACT   = '{p}: page JS preserves every prose string exactly'
    N_FXORIG  = '{p}: any fxOrig-recording effect preserves its text'
    N_SETTLE  = '{p}: scroll drive reaches the bottom by settling, not by guard'
    N_STOP    = '{p}: the measured stop is the page bottom (never the computed one)'
    N_MASKED  = '{p}: nothing left masked after the whole page has been scrolled'
    N_SCRSET  = '{p}: a scripted scroll settles before it is sampled'
    N_LANDED  = '{p}: the instant scroll landed on its target, not part-way'

    PORTED = [pathlib.Path(TARGET).resolve()]

    # (a) — IF CODE TOUCHES COPY, GATE THE COPY, NOT THE RENDERING.
    #     that battery's line-splitter reassembled headings from word spans and
    #     dropped the spaces at line breaks while adding one before
    #     punctuation ("frente ." for "frente."). It was visually flawless.
    #     No screenshot, layout measurement or human eyeball can see that
    #     class of bug — only string equality against the pre-effect original.
    #     It had the original in `dataset.fxOrig` because its splitter put
    #     it there. The academic pages have no splitter (yet — the paper.html
    #     design seed is spreading), so the pre-effect original is obtained
    #     STRUCTURALLY: the same file rendered in a context with JavaScript
    #     disabled. Every DOM-touching effect the page runs at boot — the
    #     auto-injected card tools, the router, the equation strips, the
    #     lazy-init observers — happens between those two renders, and prose
    #     must survive all of it byte-for-byte.
    #     The dataset.fxOrig comparison is kept as well, so the day a
    #     splitter does land here the check is already pointed at it.
    PROSE_SEL = 'p, li, h1, h2, h3, h4, figcaption, blockquote, dt, dd'
    PROSE_JS = """(sel) => {
        const norm = s => s.replace(/\\s+/g, ' ').trim();
        // Regions whose text is SUPPOSED to change: status lines, certificate
        // readouts, generated tables, injected card tools, the mode-switched
        // equation strips, and anything wrapping a live control.
        const dynamic = e =>
             e.closest('.status,.ro,table,.cardtools,.tools,label,select') !== null
          || e.querySelector('input,select,button,canvas') !== null
          || /^(eqHJB1|eqFP1|eq2dCost)$/.test(e.id || '');
        const prose = [];
        document.querySelectorAll(sel).forEach(e => { if (!dynamic(e)) prose.push(norm(e.textContent)); });
        // the fxOrig convention: an effect that rewrites an element records the
        // markup it replaced, and the rendered text must still equal it.
        const split = [];
        document.querySelectorAll('[data-fx-orig], [data-fxOrig]').forEach(e => {
            const d = document.createElement('div');
            d.innerHTML = e.dataset.fxOrig || e.getAttribute('data-fx-orig') || '';
            if (norm(d.textContent) !== norm(e.textContent))
                split.push(norm(d.textContent).slice(0, 50) + ' \\u2260 ' + norm(e.textContent).slice(0, 50));
        });
        return {prose, split};
    }"""
    for tgt in PORTED:
        u = 'file://' + str(tgt)
        c0 = b.new_context(java_script_enabled=False, viewport={'width': 1280, 'height': 900})
        p0 = c0.new_page(); p0.goto(u, wait_until='load'); p0.wait_for_timeout(400)
        before = p0.evaluate(PROSE_JS, PROSE_SEL)['prose']; c0.close()
        c1 = b.new_context(viewport={'width': 1280, 'height': 900})
        p1 = c1.new_page(); p1.goto(u, wait_until='load'); p1.wait_for_timeout(2500)
        after = p1.evaluate(PROSE_JS, PROSE_SEL); c1.close()
        # A zero-element comparison is a vacuous pass — the selector missing the
        # page's prose entirely would look identical to prose being preserved.
        check(N_FOUND.format(p=tgt.name), len(before) > 0, f'{len(before)} elements')
        if len(before) != len(after['prose']):
            check(N_COUNT.format(p=tgt.name), False,
                  f"no-JS {len(before)} vs JS {len(after['prose'])}")
        else:
            diff = [f'{a!r} ≠ {bb!r}' for a, bb in zip(before, after['prose']) if a != bb]
            check(N_EXACT.format(p=tgt.name),
                  not diff, (f'{len(diff)} changed; first: ' + diff[0][:150]) if diff
                            else f'{len(before)} elements identical')
        check(N_FXORIG.format(p=tgt.name),
              not after['split'], '; '.join(after['split'][:1]))

    # (b) — DO NOT COMPUTE THE SCROLL BOTTOM, MEASURE THE STOP.
    #     On that battery, body.scrollHeight UNDER-REPORTED (a fixed footer put the
    #     last screens behind it) and trusting it left a section 2693px below
    #     the fold while the battery reported it "still masked". Here the same
    #     failure has a different cause and the same shape: onepager.html grows
    #     while you scroll it (IntersectionObserver lazy init + iframe height
    #     messages), so a bottom computed at t=0 is 1321px short of the real one
    #     (measured 2026-07-27: 17024 then, 18345 after driving).
    #     The loop advances until scrollY stops changing, and the assertion is
    #     that it SETTLED rather than exhausting its guard — that is what makes
    #     "we reached the bottom" a measurement instead of a hope.
    #     NB the two lessons compose: the drive MUST pass behavior:'instant'.
    #     With html{scroll-behavior:smooth} live on onepager.html, a plain
    #     scrollBy animates, each 55ms step advances ~40px instead of 720, and
    #     the loop dies on its guard at 8120 of 18345 having silently examined
    #     less than half the page. Measured, both ways, before this was written.
    CONTENT_SEL = 'p, li, h1, h2, h3, h4, figcaption, blockquote, .card, section, canvas, table'
    DRIVE_JS = """async () => {
        // t0 is the bottom a battery would have TRUSTED before driving. It is
        // returned so the growth this section exists to survive is a measured
        // number rather than a claim in a comment.
        const t0 = Math.round(document.body.scrollHeight - innerHeight);
        const step = innerHeight * 0.8, MAX = 400;
        let last = -1, guard = 0;
        while (window.scrollY !== last && guard++ < MAX) {
            last = window.scrollY;
            window.scrollBy({top: step, left: 0, behavior: 'instant'});
            await new Promise(r => setTimeout(r, 55));
        }
        return {stop: Math.round(window.scrollY), steps: guard, max: MAX, t0: t0,
                computed: Math.round(document.body.scrollHeight - innerHeight),
                css: getComputedStyle(document.documentElement).scrollBehavior};
    }"""
    # Measured AFTER the drive, so an observer that only fires on scroll counts.
    MECH_JS = """() => ({
        smooth: getComputedStyle(document.documentElement).scrollBehavior === 'smooth',
        io: window.__ioNew | 0,
        srcdoc: [...document.querySelectorAll('iframe')]
                  .filter(f => f.hasAttribute('srcdoc') || !!f.srcdoc).length
    })"""
    # Wrap the constructor before a line of page script runs: counting
    # `new IntersectionObserver` at run time is immune to the encoding and
    # dynamic-construction variants a source grep has to enumerate.
    IO_WRAP = """(() => { const O = window.IntersectionObserver;
        window.__ioNew = 0; if (!O) return;
        const W = function (...a) { window.__ioNew++; return new O(...a); };
        W.prototype = O.prototype; window.IntersectionObserver = W; })()"""
    MASKED_JS = """(sel) => {
        const bad = [];
        document.querySelectorAll(sel).forEach(e => {
            if (e.offsetParent === null) return;      // display:none — not "masked", absent
            const cs = getComputedStyle(e), tr = cs.transform;
            if (parseFloat(cs.opacity) < 0.99 || cs.visibility === 'hidden'
                || (tr && tr !== 'none' && !/matrix\\(1, 0, 0, 1, 0, 0\\)/.test(tr)))
                bad.push(e.tagName + '.' + (e.className || '') + ' :: ' + (e.textContent || '').trim().slice(0, 34));
        });
        return bad;
    }"""
    for tgt in PORTED:
        pg5 = b.new_page(viewport={'width': 1280, 'height': 900})
        pg5.add_init_script(IO_WRAP)
        pg5.goto('file://' + str(tgt), wait_until='load'); pg5.wait_for_timeout(2000)
        d = pg5.evaluate(DRIVE_JS)
        pg5.wait_for_timeout(1200)
        # The subject's licence check (N_POWER) stood here and was RETIRED with
        # the subject by M3 — see the section-7 header. MECH_JS and IO_WRAP are
        # kept and still installed above, unused by any assertion today, because
        # they are the instrument that would re-earn the licence the day a
        # surviving page acquires one of the three mechanisms. Deleting them
        # would make restoring the coverage a rewrite instead of an edit.
        # mfg-lab.html's own copies of (b) and (c) below are satisfied trivially
        # (auto · 0 observers · 0 srcdoc · no growth) and are NOT the coverage.
        check(N_SETTLE.format(p=tgt.name),
              d['steps'] < d['max'], f"{d['steps']}/{d['max']} steps, scroll-behavior:{d['css']}")
        check(N_STOP.format(p=tgt.name),
              abs(d['stop'] - d['computed']) <= 2,
              f"measured {d['stop']} vs computed {d['computed']} (was {d['t0']} before driving)")
        masked = pg5.evaluate(MASKED_JS, CONTENT_SEL)
        check(N_MASKED.format(p=tgt.name),
              not masked, f'{len(masked)} masked; first: {masked[0] if masked else ""}')

        # (c) — scroll-behavior:smooth MAKES YOUR MEASUREMENT SAMPLE MID-FLIGHT.
        #     that battery's header-inversion check scrolled with scrollIntoView() and
        #     read 400ms later; the scroll was still animating, so it measured a
        #     transient and called it steady state. The fix is two-part and both
        #     parts are asserted here: scroll with behavior:'instant', and prove
        #     the page has SETTLED by sampling twice and requiring equality.
        #     Two samples that disagree mean every measurement taken at that
        #     moment is a transient, whatever it was measuring.
        s = pg5.evaluate("""async () => {
            const bottom = Math.round(document.body.scrollHeight - innerHeight);
            // Aim at something genuinely below the fold: a "scroll" that lands
            // at scrollY 0 settles trivially and tests nothing.
            const cands = [...document.querySelectorAll('h2, h3, section, .card')]
                .map(e => [e, Math.round(e.getBoundingClientRect().top + window.scrollY)])
                .filter(([, y]) => y > 0 && y <= bottom);
            if (!cands.length) return {skip: true};
            const want = bottom * 0.6;
            cands.sort((p, q) => Math.abs(p[1] - want) - Math.abs(q[1] - want));
            const t = cands[0][0];
            window.scrollTo({top: 0, left: 0, behavior: 'instant'});
            await new Promise(r => setTimeout(r, 250));
            t.scrollIntoView({behavior: 'instant', block: 'start'});
            await new Promise(r => setTimeout(r, 700));
            const a = Math.round(window.scrollY), off = Math.round(t.getBoundingClientRect().top) | 0;
            await new Promise(r => setTimeout(r, 400));
            return {skip: false, a, b: Math.round(window.scrollY), off,
                    bottom: Math.round(document.body.scrollHeight - innerHeight)};
        }""")
        if s.get('skip'):
            check(N_SCRSET.format(p=tgt.name), False, 'no scroll target found')
            check(N_LANDED.format(p=tgt.name), False, 'no scroll target found')
        else:
            check(N_SCRSET.format(p=tgt.name),
                  s['a'] == s['b'], f"scrollY {s['a']} then {s['b']} 400ms later")
            landed = abs(s['off']) <= 4 or s['a'] >= s['bottom'] - 2
            check(N_LANDED.format(p=tgt.name),
                  landed, f"target offset {s['off']}px at scrollY {s['a']} (bottom {s['bottom']})")
        pg5.close()
    b.close()

# The battery's own size is a claim, so it is the last thing asserted. Without
# this, a subject, a section or a whole loop can stop running and the only
# evidence is a smaller number that nobody diffs — which is exactly how the
# nine section-7 checks were going to disappear. `+ 1` counts this guard.
check(f'battery ran all {EXPECTED_CHECKS} checks it advertises (measured 2026-07-31)',
      len(ran) + 1 == EXPECTED_CHECKS,
      f'{len(ran) + 1} ran vs {EXPECTED_CHECKS} pinned — re-measure and update '
      f'EXPECTED_CHECKS and the docstring together, never one of them')

print(f"\n{len(ran)} checks, {len(fails)} failure(s)" if fails
      else f"\n{len(ran)} checks, ALL PASS")
sys.exit(1 if fails else 0)
