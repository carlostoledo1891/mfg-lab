#!/usr/bin/env python3
"""
test-layout.py — headless-browser layout-stability battery for mfg-lab.html.

House rule is "battery before pixels"; this is the battery FOR the pixels.
Earlier sessions recorded "no headless browser available" — that was wrong:
playwright + chromium run fine here. Anything visual claimed from now on
should be measured by this file, not asserted.

Run:  python3 test-layout.py [path-to-html]
Default target is ../mfg-lab.html relative to this script, so it works from any
cwd (the battery lives in mfg-lab/tests/, the artifact one level up).
"""
import pathlib, sys, json
from playwright.sync_api import sync_playwright

_HERE = pathlib.Path(__file__).resolve().parent
TARGET = sys.argv[1] if len(sys.argv) > 1 else str(_HERE.parent / 'mfg-lab.html')
URL = 'file://' + str(pathlib.Path(TARGET).resolve())
# The artifact is routed: pages carry the argument, #/route addresses each one.
# Checks that drive a specific experiment must ask for its route, exactly as a
# reader following a link would. ROUTES is also swept for layout stability, so
# the narrative pages are gated like the instrument pages.
URL_BENCH = URL + '#/bench&t=1'
ROUTES = ['/', '/wardrop', '/price', '/water-value', '/random-supply', '/bench',
          '/certificates', '/verification', '/program']
LONG = ('stopped at 500 iterations, residual 4.27e-2 — anti-monotone coupling, no '
        'fictitious-play guarantee. Asymmetry 0.839; the iteration does not certify '
        'an equilibrium here.')
WIDTHS = [390, 640, 900, 1280, 1600]

fails = []
def check(name, cond, detail=''):
    print(('PASS  ' if cond else 'FAIL  ') + name + (f'   [{detail}]' if detail else ''))
    if not cond: fails.append(name)

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
    b.close()

print(f"\n{len(fails)} failure(s)" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
