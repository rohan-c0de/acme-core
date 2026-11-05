# AGENTS.md — acme-core

This is **acme-core**, Acme's graph library: a private copy of NetworkX, kept under the BSD-3 license.

## Before a change is done

Both must be green:

- Full test suite: `pytest -n auto --doctest-modules networkx`
- Convention guard: `python tools/acme_guard.py`

Never weaken the guard, the tests, or CI config to get green.

## Conventions

- Optional dependencies (`numpy`, `scipy`, `pandas`, `matplotlib`) are imported inside functions, never at module top under `networkx/`. Tests and `conftest.py` are exempt.
- Every generator carries `@nx._dispatchable(graphs=None, returns_graph=True)`.
- Any rename or removal of a public name follows the `acme-deprecate-function` skill.

## Ask before

- Changes under `.github/`, `tools/`, `.cursor/`, or `networkx/conftest.py`
- Adding new dependencies

## Never

- Push to any remote but `origin`
- Read or print secrets
- Open PRs against the original NetworkX project
