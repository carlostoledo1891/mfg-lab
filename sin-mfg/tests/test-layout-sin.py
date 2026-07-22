#!/usr/bin/env python3
"""
test-layout-sin.py — headless-browser layout battery for sin-mfg.html.

The note never had one; it carried the deprecated serif/cream identity while
mfg-lab moved to the sans+mono "instrument" identity. This checks the migration:
sans+mono roles resolve, no serif, tabular figures on the readouts, the (long)
status string does not move the canvas at five viewports, no horizontal overflow,
real CLS inside the "good" band, and no uncaught page errors.

Run:  python3 test-layout-sin.py [path-to-html]
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
TARGET = sys.argv[1] if len(sys.argv) > 1 else str(HERE.parent / 'sin-mfg.html')
URL = 'file://' + str(pathlib.Path(TARGET).resolve())
# sin-mfg's ACTUAL longest status string (the NOT-AN-EQUILIBRIUM message, 225
# chars) — the worst case the reservation must absorb. Testing the second-longest
# would under-reserve and pass a layout that still shifts on the real message.
LONG = ('NOT AN EQUILIBRIUM — the price path is a fixed point (residual 4.27e-2) but '
        'the dispatch violates hydro budget 1.00e-1, complementarity 3.00e-1, w dual '
        'feasibility. A converged iteration is necessary, not sufficient; no '
        'equilibrium is claimed here.')
WIDTHS = [390, 640, 900, 1280, 1600]

fails = []


def check(name, cond, detail=''):
    print(('PASS  ' if cond else 'FAIL  ') + name + (f'   [{detail}]' if detail else ''))
    if not cond:
        fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch()

    # 1. status wrapping must never move the first canvas, at any width
    for w in WIDTHS:
        pg = b.new_page(viewport={'width': w, 'height': 900})
        pg.goto(URL, wait_until='load')
        pg.wait_for_timeout(1600)
        r = pg.evaluate("""(long) => {
            const s=document.querySelector('#status');
            const c=document.querySelector('#cvPrice');
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

    # 2. fonts resolve to the intended roles — sans + mono only, no serif
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.goto(URL, wait_until='load')
    pg.wait_for_timeout(1800)
    f = pg.evaluate("""() => {
        const g=(s,p)=>{const e=document.querySelector(s);return e?getComputedStyle(e)[p]:'';};
        return {body:g('body','fontFamily'), h1:g('h1','fontFamily'),
                val:g('.ro .v','fontFamily'), num:g('.ro .v','fontVariantNumeric')};
    }""")
    check('body is a sans stack, no serif', 'Inter' in f['body'] and 'Spectral' not in f['body'] and 'serif' not in f['body'].replace('sans-serif', ''))
    check('headings are Inter Tight', 'Inter Tight' in f['h1'])
    check('certificate values are mono', 'Plex Mono' in f['val'] or 'monospace' in f['val'])
    check('certificate values use tabular figures', 'tabular-nums' in f['num'], f['num'])

    # 3. real CLS while driving the solve must stay well inside "good"
    pg.evaluate("""() => {window.__cls=0;
        new PerformanceObserver(l=>{for(const e of l.getEntries())
          if(!e.hadRecentInput) window.__cls+=e.value;}).observe({type:'layout-shift',buffered:true});}""")
    pg.click('#solveBtn')
    pg.wait_for_timeout(3000)
    cls = pg.evaluate("() => +window.__cls.toFixed(5)")
    check('cumulative layout shift below the 0.1 "good" threshold', cls < 0.1, str(cls))

    # 4. no console errors (beyond the sandbox's blocked font fetch)
    errs = []
    pg2 = b.new_page(viewport={'width': 1280, 'height': 900})
    pg2.on('pageerror', lambda e: errs.append(str(e)))
    pg2.goto(URL, wait_until='load')
    pg2.wait_for_timeout(2000)
    pg2.click('#solveBtn')
    pg2.wait_for_timeout(2000)
    check('no uncaught page errors', not errs, '; '.join(errs)[:120])
    b.close()

print(f"\n{len(fails)} failure(s)" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
