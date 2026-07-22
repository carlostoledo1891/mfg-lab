"""mfglab.lab — the Live Lab's instruments.

Not solvers. These take a kernel you already have and answer questions about
it that its own test suite does not:

* :func:`~mfglab.lab.order_study.study` — the convergence study, which refuses
  to report an order it cannot support;
* :func:`~mfglab.lab.failure_map.map_box` — where in a parameter box the solver
  stops working.

Both speak one small :mod:`~mfglab.lab.contract`, and both return a
:class:`~mfglab.certificate.Certificate` that cannot exist without a falsifier.

These are Python twins of the JavaScript instruments under ``mfg-lab/lab/``,
held to the same DECISIONS (not the same English) by
``tests/test_crosslang_lab.py``, which compares refusal codes and numbers
across the two runtimes.
"""
from .contract import Kernel, ContractError, validate, error_of, norm_of, DEFAULT_LEVELS
from .order_study import study, StudyResult, RESOLUTION, TIGHTEN_BY
from .failure_map import map_box, MapResult, OK, STALLED, DIVERGED, THREW
from . import fixtures

__all__ = [
    "Kernel", "ContractError", "validate", "error_of", "norm_of", "DEFAULT_LEVELS",
    "study", "StudyResult", "RESOLUTION", "TIGHTEN_BY",
    "map_box", "MapResult", "OK", "STALLED", "DIVERGED", "THREW", "fixtures",
]
