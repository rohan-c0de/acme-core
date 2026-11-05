# Baseline — what the agent knew before Acme conventions (Nov 5, 2026)

Captured in Cursor Ask mode, repository as inherited (upstream AGENTS.md and CONTRIBUTING.rst still in place). Prompt:

> How does this repository deprecate a public function? List every file a contributor must change, with paths, and anything else the contributor must do. Then say whether anything in the repository's own instructions would stop you from doing this task.

Answer (as given; opening lines of the answer were not captured):

`doc/developer/deprecations.rst` (linked from `CONTRIBUTING.rst`).

Files a contributor must change

1. The module that defines the public function (path depends on the API; e.g. `networkx/generators/expanders.py`)
   * Emit `warnings.warn(..., DeprecationWarning)` naming the version of removal and the replacement.
   * In practice also add a Sphinx `.. deprecated:: X.Y` note in the docstring (used on current examples; not listed as a separate bullet in the Procedure section).
2. `networkx/conftest.py`
   * Add a `warnings.filterwarnings("ignore", category=DeprecationWarning, message=...)` so the suite stays quiet while the API still exists.
3. `doc/developer/deprecations.rst`
   * Under the target removal version's Todo list, add a reminder (e.g. remove the function and related tests).

Anything else

* Cycle: usually two minor releases (warn in N, remove in N+2); for a major, at least one prior release with the warning.
* PR: apply the `type: API` label (`CONTRIBUTING.rst`).
* Tests (customary, not in the Procedure bullets): wrap remaining calls in `pytest.deprecated_call()` in the function's test module.
* Reviewer note: merge message should briefly describe the change; use `Closes #...` if it closes an issue.

Would repo instructions stop this task?
Answering / documenting the process: no.
Actually submitting an automated deprecation PR as an agent: yes — `AGENTS.md` requires following the automated contributions policy in `CONTRIBUTING.rst`, which rejects fully automated issues/PRs and requires human review, understanding, and disclosure of AI use. `AGENTS.md` also blocks opening a PR on issues labeled Discussion/Question, issues younger than two weeks, or when another open PR already covers it.

Observation during the run: the agent attempted to fetch https://networkx.org/documentation/latest/developer/contribute.html (the policy page linked from the inherited AGENTS.md); Cursor's Run Mode prompted for approval; declined (Skip) to keep the baseline limited to repository contents.
