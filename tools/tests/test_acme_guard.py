"""Specification for tools/acme_guard.py — the Acme convention guard.

Each test builds a tiny stand-in repository in a temp directory and runs the guard against it.
The guard must:
  * exit clean on a correct deprecation that carries all touch-points;
  * name the exact missing touch-point when one is absent;
  * flag a module-level call to a deprecated name anywhere in the tree;
  * flag a module-level import of numpy/scipy/pandas/matplotlib in library code,
    but not in tests/ or conftest.py;
  * ignore deprecations older than the Acme threshold (3.8).

Run:  pytest tools/tests -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[1] / "acme_guard.py"
spec = importlib.util.spec_from_file_location("acme_guard", GUARD)
guard = importlib.util.module_from_spec(spec)
sys.modules["acme_guard"] = guard
spec.loader.exec_module(guard)

OLD, NEW = "old_tree", "old_tree_graph"
MSG = f"{OLD} is deprecated, use `{NEW}` instead."


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def make_repo(
    tmp: Path,
    *,
    version="3.8",
    message=MSG,
    export_both=True,
    conftest_filter=True,
    reminder=True,
    reference=True,
    test=True,
    module_level_caller=False,
    bad_import_in_lib=False,
    bad_import_in_tests=False,
) -> Path:
    root = tmp / "repo"
    exports = f'__all__ = ["{NEW}"' + (f', "{OLD}"' if export_both else "") + "]"
    lib = f'''"""Stand-in module."""
import itertools
{"import numpy" if bad_import_in_lib else ""}
{exports}


def {NEW}(n):
    """Build a thing.

    >>> {NEW}(1)
    """
    return n


def {OLD}(n):
    """
    .. deprecated:: {version}
       `{OLD}` is a deprecated alias for `{NEW}`.
    """
    import warnings

    warnings.warn(
        "{message}",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return {NEW}(n)
'''
    write(root, "networkx/__init__.py", "")
    write(root, "networkx/generators/__init__.py", "")
    write(root, "networkx/generators/classic.py", lib)
    filt = (
        '    warnings.filterwarnings(\n        "ignore", category=DeprecationWarning, message="old_tree is deprecated"\n    )\n'
        if conftest_filter
        else ""
    )
    write(root, "networkx/conftest.py", f"import warnings\nimport pytest\n\n{'import numpy' if bad_import_in_tests else ''}\n\n@pytest.fixture(autouse=True)\ndef set_warnings():\n{filt}    yield\n")
    write(root, "networkx/generators/tests/__init__.py", "")
    write(
        root,
        "networkx/generators/tests/test_classic.py",
        ("import pytest\nimport networkx as nx\n\n" + ("import numpy\n" if bad_import_in_tests else "") +
         (f"\ndef test_{OLD}_deprecated():\n    with pytest.deprecated_call():\n        nx.{OLD}(1)\n" if test else "")),
    )
    write(
        root,
        "networkx/algorithms/tests/test_swap.py",
        "import networkx as nx\n\n" + (f"thing = nx.{OLD}(3)\n" if module_level_caller else f"thing = nx.{NEW}(3)\n") +
        "\n\ndef test_inside_function():\n    nx.old_tree(2)\n",
    )
    write(root, "doc/developer/deprecations.rst", "Deprecations\n============\n\nVersion 3.10\n~~~~~~~~~~~~\n" + (f"* Remove ``{OLD}`` from ``networkx.generators.classic``.\n" if reminder else ""))
    write(root, "doc/reference/generators.rst", "Classic\n-------\n.. autosummary::\n\n   " + OLD + "\n" + (f"   {NEW}\n" if reference else ""))
    return root


def rules(vs):
    return sorted({v.rule for v in vs})


# ---------------------------------------------------------------- clean paths

def test_clean_repo_passes(tmp_path):
    root = make_repo(tmp_path)
    violations, ndeps = guard.run(root)
    assert violations == []
    assert ndeps == 1


def test_pre_acme_deprecation_is_grandfathered(tmp_path):
    # A 3.6 deprecation with NO touch-points must not be checked.
    root = make_repo(tmp_path, version="3.6", conftest_filter=False, reminder=False, reference=False, test=False)
    violations, ndeps = guard.run(root)
    assert violations == []
    assert ndeps == 0


def test_cli_exit_codes(tmp_path, capsys):
    root = make_repo(tmp_path)
    assert guard.main(["--root", str(root)]) == 0
    assert "0 violations" in capsys.readouterr().out
    root2 = make_repo(tmp_path / "b", reference=False)
    assert guard.main(["--root", str(root2)]) == 1
    assert "binomial" not in capsys.readouterr().out  # no leakage of unrelated names
    assert guard.main(["--root", str(tmp_path / "nowhere")]) == 2


# ---------------------------------------------------------------- R1 touch-points

@pytest.mark.parametrize(
    "kwargs, needle",
    [
        ({"export_both": False}, "missing from __all__"),
        ({"conftest_filter": False}, "filterwarnings"),
        ({"reminder": False}, "removal reminder"),
        ({"reference": False}, "API reference"),
        ({"test": False}, "deprecated_call"),
    ],
)
def test_each_missing_touchpoint_is_named(tmp_path, kwargs, needle):
    root = make_repo(tmp_path, **kwargs)
    violations, _ = guard.run(root)
    assert rules(violations) == ["deprecation-touchpoints"]
    assert len(violations) == 1
    assert needle in violations[0].message


def test_off_format_warning_message_is_a_violation(tmp_path):
    root = make_repo(tmp_path, message="old_tree will go away; prefer old_tree_graph")
    violations, ndeps = guard.run(root)
    assert ndeps == 0  # unparseable → not registered as a deprecation
    assert rules(violations) == ["deprecation-touchpoints"]
    assert "house format" in violations[0].message


def test_conftest_filter_must_match_message_prefix(tmp_path):
    root = make_repo(tmp_path)
    conf = root / "networkx" / "conftest.py"
    conf.write_text(conf.read_text().replace('message="old_tree is deprecated"', 'message="something else"'))
    violations, _ = guard.run(root)
    assert any("filterwarnings" in v.message for v in violations)


# ---------------------------------------------------------------- R2 module-level caller

def test_module_level_caller_is_flagged_with_location(tmp_path):
    root = make_repo(tmp_path, module_level_caller=True)
    violations, _ = guard.run(root)
    assert rules(violations) == ["module-level-caller"]
    v = violations[0]
    assert v.path.endswith("networkx/algorithms/tests/test_swap.py")
    assert v.line == 3


def test_call_inside_a_function_is_not_flagged(tmp_path):
    # the reference repo already calls old_tree inside test_inside_function()
    root = make_repo(tmp_path)
    violations, _ = guard.run(root)
    assert violations == []


# ---------------------------------------------------------------- R3 import boundary

def test_module_level_optional_import_in_library_is_flagged(tmp_path):
    root = make_repo(tmp_path, bad_import_in_lib=True)
    violations, _ = guard.run(root)
    assert rules(violations) == ["import-boundary"]
    assert violations[0].path.endswith("networkx/generators/classic.py")
    assert "numpy" in violations[0].message


def test_optional_imports_in_tests_and_conftest_are_exempt(tmp_path):
    root = make_repo(tmp_path, bad_import_in_tests=True)
    violations, _ = guard.run(root)
    assert violations == []
