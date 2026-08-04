# MFG Lab — the academic repo. `make check` is the ritual; a human reads
# the output (internal green is necessary, not sufficient).
#
# TIERS
#   make check       correctness — every JS battery. Green = code is right.
#   make check-py    the Python batteries (mfglab pytest + PLD selftest; needs venv).
#   make check-all   check + headless-browser layout batteries + check-py.

NODE := node
LAB  := mfg-lab/tests
SIN  := sin-mfg/tests
VENV := .venv
PY   := $(VENV)/bin/python

.PHONY: check check-eqcert check-cap check-lab check-sin check-all check-py layout venv clean

check: check-eqcert check-cap check-lab check-sin
	@echo ""
	@echo "== make check: correctness gates green =="

# eqcert runs FIRST: everything downstream inherits its arithmetic, and its
# THE SINGLE-SOURCE GATE IS NOT IN THIS TREE, and that is a stated gap, not an
# oversight. It was removed from the export on 2026-07-30 because its register
# names private, unexported projects: publishing it would disclose them, and
# trimming the register until the token scan went quiet would have replaced a
# measured census with a flattering one. So the honest reading of this file is:
# `make check` here proves the arithmetic and the artifacts, and proves NOTHING
# about whether a second copy of the interval or rational library has appeared
# in this tree. The monorepo's gate still scans the whole tree at source. A
# public-scoped register is the follow-up; until it exists, do not read a green
# run here as a single-source guarantee.
check-eqcert:
	@echo "== eqcert (certification toolkit) =="
	@$(NODE) eqcert/tests/test-eqcert.js
	@echo "   note: no single-source gate in this tree -- see the comment above."

# mfg-cap: the computer-assisted proof. The artifact is GENERATED from the
# kernels, so test-artifact.js asserts byte-identity and freshness — the page
# cannot drift from what the battery proves.
check-cap:
	@echo "== mfg-cap batteries =="
	@$(NODE) mfg-cap/tests/test-cap.js
	@$(NODE) mfg-cap/tests/test-artifact.js

check-lab:
	@echo "== mfg-lab batteries =="
	@$(NODE) $(LAB)/smoke.js
	@$(NODE) $(LAB)/test-order-study.js
	@$(NODE) $(LAB)/test-failure-map.js
	@$(NODE) $(LAB)/test-byo.js
# M3 (2026-07-28): test-byo-artifact.js and test-lab-artifact.js removed with the pages,
# builders and templates they gated. mirrors the root Makefile, same commit.
	@$(NODE) $(LAB)/test-index.js
	@$(NODE) $(LAB)/test-wardrop.js
	@$(NODE) $(LAB)/test-wardrop-diff.js
	@$(NODE) $(LAB)/test-wardrop-interval.js
	@$(NODE) $(LAB)/test-water-value-diff.js
	@$(NODE) $(LAB)/test-transpose.js
	@$(NODE) $(LAB)/test-invariant.js

check-sin:
	@echo "== sin-mfg battery =="
	@$(NODE) $(SIN)/test-sin.js
	@$(NODE) $(SIN)/test-transpose-sin.js
	@$(NODE) $(SIN)/test-water-value.js

check-all: check layout check-py

check-py:
	@echo "== Python batteries =="
	@if [ -x "$(PY)" ] && $(PY) -c "import numpy" 2>/dev/null; then \
		$(PY) -m pytest -q python && \
		echo "-- PLD martingale selftest --" && \
		$(PY) sin-mfg/tests/pld_martingale_test.py --selftest >/dev/null && \
		echo "PLD selftest: ALL PASS" ; \
	else \
		echo "SKIPPED — venv not built. This gate did NOT run. Run 'make venv'." ; \
	fi

layout:
	@echo "== layout batteries (chromium) =="
	@if [ -x "$(PY)" ] && $(PY) -c "import playwright" 2>/dev/null; then \
		$(PY) $(LAB)/test-layout.py && $(PY) $(SIN)/test-layout-sin.py ; \
	else \
		echo "SKIPPED — playwright not installed. These gates did NOT run." ; \
		echo "         run 'make venv' first; the visual claims are UNVERIFIED until then." ; \
	fi

venv:
	@PYBIN=$$(for p in python3.13 python3.12 python3.11; do command -v $$p && break; done); \
	if [ -z "$$PYBIN" ]; then \
		echo "No python 3.11+ found — install one, then rerun 'make venv'." ; \
		exit 1 ; \
	fi ; \
	echo "building $(VENV) on $$PYBIN ($$($$PYBIN --version))" ; \
	$$PYBIN -m venv $(VENV) && \
	$(PY) -m pip install -q --upgrade pip && \
	$(PY) -m pip install -q -r requirements-dev.txt && \
	$(VENV)/bin/playwright install chromium && \
	echo "venv ready. run 'make check-all' for the full suite."

clean:
	@find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "cleaned transient files."
