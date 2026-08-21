# License — Enclosure papers

© 2026 Carlos Toledo · **Enclosure**.

**In one line: the page is CC-BY 4.0, the verifier it carries is MIT, the solver is not
published.** Two licences, one per file — never two inside one file.

## The paper page

This page — its text, figures, tables and layout — is licensed under the
**Creative Commons Attribution 4.0 International License (CC-BY 4.0)** —
https://creativecommons.org/licenses/by/4.0/. You may share and adapt it, including for
commercial purposes, provided you give appropriate credit to *Carlos Toledo / Enclosure*,
link this licence, link the canonical page, and indicate any changes.

## The verifiers it carries — MIT, not CC-BY

The verifiers embedded in these pages and offered by the download button —
**`verify_congest.py`** and **`verify_wardrop.py`** — are licensed under the **MIT License**,
not CC-BY. Run, read, modify and redistribute them freely; the one obligation is to keep the
copyright and permission notice. The full licence text, with that notice, is inside each
file: the file travels alone, so the file must say so itself.

The CC-BY attribution requirement on this page is **not** a condition on running, modifying
or redistributing those files.  The proof is meant to be re-run: download the verifier and
check it yourself.

## The certification kernel

The interval-arithmetic, radii-polynomial and exact-rational machinery this work builds
on is **`eqcert`**, released separately under the **MIT License** and attributed as such —
https://github.com/carlostoledo1891/mfg-lab/tree/main/eqcert. Those components remain under
MIT, and the sections of each verifier ported from them carry that attribution in-file.

## What is NOT included, and is not licensed here

The **solver** and the research pipeline that *produce* certified candidates (Enclosure's
proprietary engine) are **not part of this artifact** and are not published. This page
ships the *verifier* and the *certified candidate* — everything a referee needs to
independently re-verify the result — not the method used to find it.
