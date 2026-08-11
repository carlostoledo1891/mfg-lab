#!/usr/bin/env python3
"""mutate.py — SEMANTIC mutation operators over a Python function body.

WHAT THIS IS FOR. Path A of the evidence-first benchmark asks one question per benchmark
item: *if the reference solution were wrong, would this item's own test suite notice?* To ask
it you need mutants that are genuinely wrong-but-runnable. This file makes them.

WHY AST AND NOT TEXT. A regex that rewrites `<` to `<=` will happily corrupt a string literal
or a comment, and the resulting mutant dies at parse time. A mutant that fails because it does
not compile tells you nothing about the test suite — it tells you the mutation was bad. Every
operator here rewrites a typed AST node, and every mutant is re-compiled before it is emitted;
one that will not compile is DISCARDED, not counted.

THE FAILURE THIS FILE IS BUILT AGAINST. If the generator is broken in the direction of making
mutants that are secretly still correct, every item looks INSENSITIVE and the whole benchmark
audit reports a scandal that is really a bug in this file. `equivalent_guard()` and the
kill-controls in tests/ exist for exactly that; see README §Controls.

Stdlib only. No network. Python 3.9+."""

import ast
import copy

__all__ = ['mutants', 'MUTATION_OPERATORS']


# ---------------------------------------------------------------- operators
# Each operator is (name, node-type, transform). A transform returns a NEW node or None to
# decline. Declining is normal: most operators do not apply to most nodes.

_CMP_SWAP = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt,
    ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
    ast.Is: ast.IsNot, ast.IsNot: ast.Is,
    ast.In: ast.NotIn, ast.NotIn: ast.In,
}

_BIN_SWAP = {
    ast.Add: ast.Sub, ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv, ast.FloorDiv: ast.Mult,
    ast.Mod: ast.FloorDiv,
}

_BOOL_SWAP = {ast.And: ast.Or, ast.Or: ast.And}


def _op_comparison(node):
    """`a < b` -> `a <= b`. The classic off-by-one at a boundary. This is the operator most
    likely to survive a weak test suite, because it only differs on the boundary case — which
    is precisely the case a thin suite forgets to test."""
    if not isinstance(node, ast.Compare):
        return None
    for i, op in enumerate(node.ops):
        repl = _CMP_SWAP.get(type(op))
        if repl:
            new = copy.deepcopy(node)
            new.ops[i] = repl()
            return new
    return None


def _op_arithmetic(node):
    """`a + b` -> `a - b`. Coarse, and usually caught — which is the point: it is the control
    that shows a suite has ANY teeth at all. An item whose suite cannot kill this is not merely
    thin, it is close to vacuous."""
    if not isinstance(node, ast.BinOp):
        return None
    repl = _BIN_SWAP.get(type(node.op))
    if not repl:
        return None
    new = copy.deepcopy(node)
    new.op = repl()
    return new


def _op_boolean(node):
    """`a and b` -> `a or b`."""
    if not isinstance(node, ast.BoolOp):
        return None
    repl = _BOOL_SWAP.get(type(node.op))
    if not repl:
        return None
    new = copy.deepcopy(node)
    new.op = repl()
    return new


def _op_constant_offset(node):
    """An integer literal `k` -> `k + 1`. The off-by-one that lives in slice bounds, range
    limits and index arithmetic. Booleans are excluded because in Python `True` IS an int and
    `True + 1` is 2, which is a type-shaped break rather than a semantic one."""
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, bool) or not isinstance(node.value, int):
        return None
    new = copy.deepcopy(node)
    new.value = node.value + 1
    return new


def _op_negate_bool_constant(node):
    """`True` -> `False`."""
    if not isinstance(node, ast.Constant) or not isinstance(node.value, bool):
        return None
    new = copy.deepcopy(node)
    new.value = not node.value
    return new


def _op_drop_not(node):
    """`not x` -> `x`. Inverts a guard without touching its shape."""
    if not isinstance(node, ast.UnaryOp) or not isinstance(node.op, ast.Not):
        return None
    return copy.deepcopy(node.operand)


MUTATION_OPERATORS = [
    ('comparison', _op_comparison),
    ('arithmetic', _op_arithmetic),
    ('boolean', _op_boolean),
    ('const_offset', _op_constant_offset),
    ('bool_flip', _op_negate_bool_constant),
    ('drop_not', _op_drop_not),
]


# ---------------------------------------------------------------- machinery

class _NthReplacer(ast.NodeTransformer):
    """Applies one operator at ONE site — the nth applicable node in walk order.

    ONE SITE, NOT ALL SITES, and this is deliberate. A mutant that changes every comparison at
    once is trivially killed by any test and measures nothing; the interesting question is
    whether a suite notices a SINGLE wrong decision. First-order mutation is also what the
    mutation-testing literature means by the term, so the kill rates here are comparable to
    published ones rather than to a private variant."""

    def __init__(self, transform, target_index):
        self.transform = transform
        self.target_index = target_index
        self.seen = 0
        self.applied = False

    def visit(self, node):
        node = self.generic_visit(node)
        if self.applied:
            return node
        out = self.transform(node)
        if out is not None:
            if self.seen == self.target_index:
                self.applied = True
                return ast.copy_location(out, node)
            self.seen += 1
        return node


def _site_count(tree, transform):
    n = 0
    for node in ast.walk(tree):
        if transform(node) is not None:
            n += 1
    return n


def equivalent_guard(original_src, mutant_src):
    """Cheap guard against an EQUIVALENT MUTANT — a mutant that is textually different and
    semantically identical. A test suite cannot kill one, so counting it as a survivor
    slanders the suite.

    This catches only the trivial case (the unparse round-trips to the same code). Genuine
    equivalent-mutant detection is undecidable, so the honest position is: this reduces the
    error, it does not eliminate it, and the README says so where a reader will see it."""
    try:
        a = ast.dump(ast.parse(original_src))
        b = ast.dump(ast.parse(mutant_src))
    except SyntaxError:
        return False
    return a == b


def mutants(source, limit_per_operator=3):
    """Yield (operator_name, site_index, mutant_source).

    Every emitted mutant is COMPILE-CHECKED here, so a consumer never has to distinguish "the
    suite killed it" from "it never ran". A mutant that will not compile is dropped silently
    and is not counted in any denominator."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    for name, transform in MUTATION_OPERATORS:
        sites = _site_count(tree, transform)
        for idx in range(min(sites, limit_per_operator)):
            rep = _NthReplacer(transform, idx)
            new_tree = rep.visit(copy.deepcopy(tree))
            if not rep.applied:
                continue
            ast.fix_missing_locations(new_tree)
            try:
                mutant_src = ast.unparse(new_tree)
                compile(mutant_src, '<mutant>', 'exec')
            except (SyntaxError, ValueError, TypeError):
                continue
            if equivalent_guard(source, mutant_src):
                continue
            yield (name, idx, mutant_src)


if __name__ == '__main__':
    demo = "def f(x):\n    if x < 10 and x > 0:\n        return x + 1\n    return not True\n"
    print(demo)
    for op, i, m in mutants(demo):
        print(f'--- {op}[{i}] ---')
        print(m)
