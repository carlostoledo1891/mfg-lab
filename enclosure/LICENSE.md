# License — Enclosure papers

© 2026 Carlos Toledo · **Enclosure**.

## The paper and its embedded verifier

This page and the verifier it carries (`verify_congest.py`) are licensed under the
**Creative Commons Attribution 4.0 International License (CC-BY 4.0)** —
https://creativecommons.org/licenses/by/4.0/. You may share and adapt them, including
for commercial purposes, provided you give appropriate credit to *Carlos Toledo /
Enclosure* and indicate any changes. The proof is meant to be re-run: download the
verifier and check it yourself.

## The certification kernel

The interval-arithmetic, radii-polynomial and exact-rational machinery this work builds
on is **`eqcert`**, released separately under the **MIT License** and attributed as such.
Those components remain under MIT.

## What is NOT included, and is not licensed here

The **solver** and the research pipeline that *produce* certified candidates (Enclosure's
proprietary engine) are **not part of this artifact** and are not published. This page
ships the *verifier* and the *certified candidate* — everything a referee needs to
independently re-verify the result — not the method used to find it.
