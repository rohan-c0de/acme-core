# ACME-142 — Align `binomial_tree` with the core naming standard

**Requested by:** Pat (PM, Platform) · **Component:** acme-core / generators · **Priority:** normal

## Original request (Pat, as filed)

> Can we rename `binomial_tree` so it matches the other generators? New folks keep asking why it's the odd one out when everything else ends in `_graph`. The old name should keep working for a while so nothing breaks.

## Triage notes (tech lead)

Naming convention: public graph constructors end in `_graph`. `binomial_tree` is the odd one out; rename via `acme-deprecate-function`, not a hard cut.

**Repo search** (`binomial_tree`): **11** occurrences in **6** files (excluding this ticket).

| File | Occurrences | Notes |
|------|-------------|--------|
| `networkx/generators/classic.py` | 3 | `__all__`, definition, docstring example |
| `networkx/generators/tests/test_classic.py` | 2 | test method name; call inside `test_binomial_tree` |
| `networkx/algorithms/tests/test_broadcasting.py` | 2 | test function name; call inside the test |
| `networkx/algorithms/tests/test_swap.py` | 1 | **module top-level** call (`binomial = nx.binomial_tree(...)`) |
| `doc/reference/generators.rst` | 1 | autosummary entry |
| `doc/release/release_2.6.rst` | 2 | historical release notes only |

Live call sites: three in tests, one docstring/doctest example. **Only** `test_swap.py` is at module top level — that one must move to the new name before collection, or DeprecationWarning aborts the suite. In-function calls may stay (ask implementer).

**Versions** (`networkx/__init__.py`: `__version__ = "3.7.1rc0.dev0"`): deprecate in **3.8** (next minor); schedule removal under **Version 3.10** (two minor versions after the deprecating release). Keep `@nx._dispatchable(graphs=None, returns_graph=True)` on the real implementation only.

## Ask

Add `binomial_tree_graph` as the canonical generator; keep `binomial_tree` as a deprecated alias per `acme-deprecate-function` (house-format warning, deprecate 3.8, remove 3.10). Fix the module-top-level call in `test_swap.py`.

## Acceptance criteria (set at triage)

- [ ] `binomial_tree_graph` is the real implementation (`@nx._dispatchable`); `binomial_tree` is a thin alias with `.. deprecated:: 3.8` and warning text exactly `binomial_tree is deprecated, use \`binomial_tree_graph\` instead.`
- [ ] Both names in `__all__`; NEW in `doc/reference` autosummary; OLD kept; removal reminder under Version 3.10 in `doc/developer/deprecations.rst`
- [ ] `networkx/conftest.py` ignores `DeprecationWarning` with message prefix `binomial_tree is deprecated`
- [ ] `test_binomial_tree_deprecated` uses `pytest.deprecated_call()` and asserts OLD equals NEW
- [ ] No module-top-level calls to `binomial_tree` remain (including tests)
- [ ] No new optional-dependency imports at module top under `networkx/`
- [ ] PR carries the `type: API` label
- [ ] `python tools/acme_guard.py` exits 0
- [ ] `pytest -n auto --doctest-modules networkx` green (same checks CI runs)

*(Synthesized ticket for the Acme scenario. Pat's request is the non-technical ask; triage notes and acceptance criteria were drafted by the agent from the repository and Acme's conventions, and reviewed by the tech lead.)*
