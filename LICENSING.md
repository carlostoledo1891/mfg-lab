# LICENSING — which licence governs which file, and how to tell

**One sentence: the code is MIT, the Enclosure papers are CC-BY 4.0, and one file never
carries two licences.**

GitHub shows a single MIT badge for this repository, because a repository can only advertise
one licence. That badge is accurate for everything except the papers. This file is the scope
statement for it.

## The rule

**A licence here is a property of the work, not of its address.** Nothing below is decided by
which folder a file sits in or which URL serves it. Rename a directory, re-organise the tree,
publish a page at a different address — the licence does not move with the path, because it
was never attached to the path. There are two steps, and no third:

1. **If a document states its own licence, that statement governs it.** Each Enclosure paper
   states **CC-BY 4.0** twice, both times inside the page itself: in a licence paragraph you
   can read in the footer, and in the machine-readable `license` field of its JSON-LD block.
   The verifier each paper carries states **MIT** inside its own bytes — decode the download
   and the first line you read is `SPDX-License-Identifier: MIT`.
2. **Otherwise the root [`LICENSE`](LICENSE) governs, and it is MIT.**

So: to learn what you may do with a file, look inside the file, then fall back to the root
`LICENSE`. You never need to know where it came from, and no rearrangement of this repository
can change your answer.

## The inventory

| The work | Licence | Stated where | Where it sits today |
|---|---|---|---|
| the certification toolkit — interval arithmetic, exact rationals, radii-polynomial / Krawczyk, `Certificate` | **MIT** | root [`LICENSE`](LICENSE) | `eqcert/**` |
| the computer-assisted proof of a stationary equilibrium — kernels, generator, batteries | **MIT** | root [`LICENSE`](LICENSE) | `mfg-cap/**`, and the page itself at `papers/mfg-cap.html` |
| the interactive artifacts and their batteries | **MIT** | root [`LICENSE`](LICENSE) | `mfg-lab/**` |
| the `mfglab` Python package (`pip install mfg-lab`, `import mfglab`) — kernels, cross-language differentials, batteries | **MIT** | root [`LICENSE`](LICENSE) | `python/**` |
| the Lab instruments — a convergence study and a failure map you run on **your own** solver, plus the bring-your-own-MFG kernel | **MIT** | root [`LICENSE`](LICENSE) | `lab/**`, with their batteries in `mfg-lab/tests/` |
| the research note, its kernels, references and batteries | **MIT** | root [`LICENSE`](LICENSE) | `sin-mfg/**`, and the page itself at `papers/stock-constraint.html` |
| the repository scaffolding — `LICENSE`, `LICENSING.md`, `README.md`, `CITATION.cff`, `Makefile`, `vercel.json`, `.gitignore`, `requirements-dev.txt`, `.github/**` | **MIT** | root [`LICENSE`](LICENSE) | the repository root |
| **the Enclosure papers — `mfg-congest` and `wardrop-repro`** — as *documents*: prose, figures, tables, layout, CSS | **CC-BY 4.0** | a visible licence paragraph in each page's footer, the page's JSON-LD `license` field, and the CC-BY licence text shipped alongside the papers | wherever each page is published |
| the verifier each paper embeds and offers for download — `verify_congest.py`, `verify_wardrop.py` | **MIT** | inside the decoded file: SPDX line, copyright notice, full permission-and-warranty text, and the attribution for the parts ported from the certification toolkit | inside the page, and in your downloads folder once you click |
| the CC-BY 4.0 licence text shipped alongside the papers | licence text; reproduce freely | itself | beside the papers |

> **The last column is a locator, not the rule.** It tells you where to find these works in
> this repository today. It is safe to be approximate precisely because every path in it
> points at the **default** licence: anything a glob fails to cover falls back to the same
> root `LICENSE` it was already under, so a stale locator cannot change anyone's obligations.
> The one licence that is *not* the default — CC-BY 4.0, on the papers — is identified by
> **which work it is**, never by where it lives. That asymmetry is deliberate.
>
> **`papers/` is a namespace, not a licence.** Four pages are published under it and they do
> not share a licence: `mfg-congest` and `wardrop-repro` are the CC-BY 4.0 Enclosure papers,
> while `mfg-cap` and `stock-constraint` are MIT under the root `LICENSE` like the rest of the
> code. This is exactly the case the rule above is built for — open the page and read what it
> says about itself; the directory it is served from decides nothing.

Copyright holder throughout: **Carlos Toledo**. *Enclosure* is a trading name; it appears in
prose bylines and in the CC-BY credit string, never as the holder of an MIT notice.

## The embedded verifier — the one case worth reading twice

Each paper page carries its verifier base64-encoded, so the proof travels with the page and
the download button needs no network. **That file is MIT even though the page around it is
CC-BY.** A licence on the page cannot follow a file that leaves the page, so the file states
its own: decode it and the first thing you read is `SPDX-License-Identifier: MIT`, a copyright
line, the full permission-and-warranty text, and the attribution for the sections ported from
the certification toolkit.

Concretely: you may run, modify, redistribute, and embed `verify_congest.py` or
`verify_wardrop.py` in a commercial product, keeping only the notice. The CC-BY attribution
requirement of the surrounding page is **not** a condition on any of that.

No file in this repository carries two licences with unmarked boundaries.

## What reuse requires

**MIT parts** (everything except the Enclosure papers): keep the copyright notice and the
permission-and-warranty text in all copies or substantial portions — including inside bundles
and binaries, where a `LICENSE`/`NOTICE` file is the customary vehicle. When redistributing a
verifier, the certification-toolkit heritage line is part of the notice you are preserving.
Nothing else is required: no credit in a paper or UI, no publishing of changes, no matching
licence, no permission. Citation via `CITATION.cff` is **requested, not required**.

**CC-BY 4.0 parts** (the Enclosure papers, as documents): credit *Carlos Toledo / Enclosure*,
link <https://creativecommons.org/licenses/by/4.0/>, link the canonical page, state any
changes you made, and do not imply endorsement. Commercial reuse is permitted.

## What no licence here grants

The **solver** that produces the certified candidates, and the research pipeline around it,
are not part of this repository and are not licensed by it. The papers ship the *verifier* and
the *certified candidate* — everything a referee needs to re-check the result independently —
not the method used to find it. Nothing here grants a trademark right in *Enclosure*, and MIT
grants no patent licence beyond what it implies for the code actually distributed.

**Third-party material** we reproduce carries its own terms and is cited, not relicensed: the
Bakaryan–Aoun–de Lima Ribeiro–Hovakimyan–Gomes network and Table 1 (arXiv:2504.16028 / *AIMS
Mathematics* 11(5):15143–15162, 2026), and the Gomes–Saúde and Gomes–Gutiérrez–Ribeiro models.

Questions: carlos@carlostoledo.co
