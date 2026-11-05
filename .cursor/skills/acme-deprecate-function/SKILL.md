---
name: acme-deprecate-function
description: Renames or retires a public function in acme-core with the full Acme deprecation cycle.
---

# Acme deprecate function

Read the current version from `networkx/__init__.py`. The deprecation version `X.Y` is the next minor release.

## Procedure

1. **Module** — NEW becomes the real implementation: keep `@nx._dispatchable` and update the docstring example. OLD becomes a thin alias whose docstring has `.. deprecated:: X.Y` and whose body does `import warnings` then `warnings.warn("OLD is deprecated, use `NEW` instead.", category=DeprecationWarning, stacklevel=2)` then returns `NEW(...)`. Warning text must be exactly that format because the guard parses it. Put both names in `__all__`.

2. **`networkx/conftest.py`** — Inside `set_warnings()`, add:
   `warnings.filterwarnings("ignore", category=DeprecationWarning, message="OLD is deprecated")`

3. **`doc/developer/deprecations.rst`** — Under the heading for two minor versions later, add a removal reminder for OLD.

4. **`doc/reference/<package>.rst`** — Add NEW to the autosummary list; keep OLD.

5. **Test** — Add `test_OLD_deprecated` using `pytest.deprecated_call()` that also asserts the result equals NEW's.

6. **Call sites** — Search the entire repository for calls to OLD at module top level, including in test files, and change them to NEW. The autouse warnings filter does not cover collection time, so one such call aborts the whole suite. Calls inside functions may stay — ask the user.

7. **PR** — The PR needs the `type: API` label.

## Finish

Run `python tools/acme_guard.py` and `pytest -n auto --doctest-modules networkx`. Both must be green. Never weaken the guard, the tests, or CI to get there.

Summarize the seven touch-points: (1) module alias + warning, (2) conftest filter, (3) deprecations.rst reminder, (4) reference autosummary, (5) `test_OLD_deprecated`, (6) top-level call sites → NEW, (7) `type: API` label.
