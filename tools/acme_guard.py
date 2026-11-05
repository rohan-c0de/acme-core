#!/usr/bin/env python3
"""Acme convention guard — stdlib-only checks for deprecations and imports."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

OPTIONAL_PACKAGES = frozenset({"numpy", "scipy", "pandas", "matplotlib"})
HOUSE_FORMAT = re.compile(r"^(\w+) is deprecated, use `(\w+)` instead\.$")
DEPRECATED_DIRECTIVE = re.compile(r"\.\. deprecated::\s*(\d+\.\d+)")


@dataclass
class Violation:
    rule: str
    path: str
    line: int
    message: str


@dataclass
class Deprecation:
    old: str
    new: str
    path: str
    line: int
    module_path: Path


def _parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _read_ast(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def _const_str(node: ast.AST) -> str | None:
    """Return a string constant, joining implicit concatenations."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _const_str(node.left)
        right = _const_str(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _call_name_attr(node: ast.Call) -> str | None:
    """Return the final attribute/name of a call target, e.g. nx.old_tree → old_tree."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _warn_message_from_function(fn: ast.AST) -> tuple[str | None, int]:
    """Find warnings.warn(...) string message inside *fn*; return (msg, lineno)."""
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        is_warn = False
        if isinstance(node.func, ast.Attribute) and node.func.attr == "warn":
            is_warn = True
        elif isinstance(node.func, ast.Name) and node.func.id == "warn":
            is_warn = True
        if not is_warn or not node.args:
            continue
        msg = _const_str(node.args[0])
        if msg is not None:
            return msg, node.lineno
    return None, getattr(fn, "lineno", 1)


def _module_all_names(tree: ast.AST) -> set[str] | None:
    """Return names listed in __all__, or None if __all__ is absent."""
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    names: set[str] = set()
                    for elt in node.value.elts:
                        s = _const_str(elt)
                        if s is not None:
                            names.add(s)
                    return names
                return set()
    return None


def _iter_py_files(root: Path):
    nx = root / "networkx"
    if not nx.is_dir():
        return
    yield from sorted(nx.rglob("*.py"))


def _is_test_or_conftest(path: Path) -> bool:
    if path.name == "conftest.py":
        return True
    return "tests" in path.parts


def _discover_deprecations(
    root: Path, min_version: str
) -> tuple[list[Deprecation], list[Violation]]:
    deps: list[Deprecation] = []
    violations: list[Violation] = []
    min_v = _parse_version(min_version)

    for path in _iter_py_files(root):
        tree = _read_ast(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            doc = ast.get_docstring(node) or ""
            m = DEPRECATED_DIRECTIVE.search(doc)
            if not m:
                continue
            version = m.group(1)
            if _parse_version(version) < min_v:
                continue
            msg, warn_line = _warn_message_from_function(node)
            rel = _rel(root, path)
            if msg is None:
                violations.append(
                    Violation(
                        rule="deprecation-touchpoints",
                        path=rel,
                        line=warn_line,
                        message=(
                            "warning message missing or not a string constant; "
                            "expected house format"
                        ),
                    )
                )
                continue
            hm = HOUSE_FORMAT.match(msg)
            if not hm:
                violations.append(
                    Violation(
                        rule="deprecation-touchpoints",
                        path=rel,
                        line=warn_line,
                        message=(
                            f"warning message {msg!r} is not in house format "
                            f"(expected '{{OLD}} is deprecated, use `{{NEW}}` instead.')"
                        ),
                    )
                )
                continue
            old, new = hm.group(1), hm.group(2)
            deps.append(
                Deprecation(
                    old=old,
                    new=new,
                    path=rel,
                    line=node.lineno,
                    module_path=path,
                )
            )
    return deps, violations


def _conftest_filter_prefixes(root: Path) -> list[str]:
    conf = root / "networkx" / "conftest.py"
    if not conf.is_file():
        return []
    tree = _read_ast(conf)
    if tree is None:
        return []
    prefixes: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_fw = (
            isinstance(func, ast.Attribute) and func.attr == "filterwarnings"
        ) or (isinstance(func, ast.Name) and func.id == "filterwarnings")
        if not is_fw:
            continue
        cat_ok = False
        message = None
        for kw in node.keywords:
            if kw.arg == "category":
                if isinstance(kw.value, ast.Name) and kw.value.id == "DeprecationWarning":
                    cat_ok = True
                elif (
                    isinstance(kw.value, ast.Attribute)
                    and kw.value.attr == "DeprecationWarning"
                ):
                    cat_ok = True
            if kw.arg == "message":
                message = _const_str(kw.value)
        if cat_ok and message is not None:
            prefixes.append(message)
    return prefixes


def _has_removal_reminder(root: Path, old: str) -> bool:
    rst = root / "doc" / "developer" / "deprecations.rst"
    if not rst.is_file():
        return False
    return f"``{old}``" in rst.read_text(encoding="utf-8")


def _has_api_reference(root: Path, name: str) -> bool:
    """True if *name* appears as an autosummary / reference entry."""
    ref = root / "doc" / "reference"
    if not ref.is_dir():
        return False
    for path in ref.rglob("*.rst"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if name in line.split() or line.strip() == name:
                return True
    return False


def _has_deprecated_call_test(root: Path, old: str) -> bool:
    for path in _iter_py_files(root):
        tree = _read_ast(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.With):
                continue
            for item in node.items:
                ctx = item.context_expr
                if not isinstance(ctx, ast.Call):
                    continue
                is_dc = (
                    isinstance(ctx.func, ast.Attribute)
                    and ctx.func.attr == "deprecated_call"
                ) or (
                    isinstance(ctx.func, ast.Name)
                    and ctx.func.id == "deprecated_call"
                )
                if not is_dc:
                    continue
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and _call_name_attr(child) == old:
                        return True
    return False


def _has_conftest_filter(prefixes: list[str], old: str, new: str) -> bool:
    """True if a DeprecationWarning filter message prefixes the house warning.

    Acme requires the filter's ``message`` to start with ``{OLD} is deprecated``
    and to be a prefix of the house-format warning (as ``warnings.filterwarnings``
    does via ``re.match``).
    """
    house = f"{old} is deprecated, use `{new}` instead."
    expected = f"{old} is deprecated"
    for p in prefixes:
        if p.startswith(expected) and house.startswith(p):
            return True
    return False


def _check_touchpoints(root: Path, deps: list[Deprecation]) -> list[Violation]:
    violations: list[Violation] = []
    filter_prefixes = _conftest_filter_prefixes(root)
    conf_path = root / "networkx" / "conftest.py"

    for dep in deps:
        tree = _read_ast(dep.module_path)
        all_names = _module_all_names(tree) if tree else None
        if all_names is None or dep.old not in all_names:
            violations.append(
                Violation(
                    rule="deprecation-touchpoints",
                    path=dep.path,
                    line=dep.line,
                    message=f"{dep.old!r} missing from __all__",
                )
            )

        if not _has_conftest_filter(filter_prefixes, dep.old, dep.new):
            violations.append(
                Violation(
                    rule="deprecation-touchpoints",
                    path=_rel(root, conf_path) if conf_path.is_file() else dep.path,
                    line=dep.line,
                    message=(
                        f"missing filterwarnings for {dep.old!r} "
                        f"(expected message prefix '{dep.old} is deprecated')"
                    ),
                )
            )

        if not _has_removal_reminder(root, dep.old):
            violations.append(
                Violation(
                    rule="deprecation-touchpoints",
                    path="doc/developer/deprecations.rst",
                    line=1,
                    message=f"missing removal reminder for {dep.old!r}",
                )
            )

        # Skill: add NEW to the autosummary list; keep OLD. Guard flags missing NEW.
        if not _has_api_reference(root, dep.new):
            violations.append(
                Violation(
                    rule="deprecation-touchpoints",
                    path=dep.path,
                    line=dep.line,
                    message=f"{dep.new!r} missing from API reference",
                )
            )

        if not _has_deprecated_call_test(root, dep.old):
            violations.append(
                Violation(
                    rule="deprecation-touchpoints",
                    path=dep.path,
                    line=dep.line,
                    message=f"missing deprecated_call test for {dep.old!r}",
                )
            )

    return violations


def _check_module_level_callers(
    root: Path, deps: list[Deprecation]
) -> list[Violation]:
    if not deps:
        return []
    old_names = {d.old for d in deps}
    violations: list[Violation] = []

    for path in _iter_py_files(root):
        tree = _read_ast(path)
        if tree is None or not isinstance(tree, ast.Module):
            continue
        rel = _rel(root, path)

        class ModuleCallVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):  # noqa: N802
                return

            def visit_AsyncFunctionDef(self, node):  # noqa: N802
                return

            def visit_ClassDef(self, node):  # noqa: N802
                return

            def visit_Lambda(self, node):  # noqa: N802
                return

            def visit_Call(self, node):  # noqa: N802
                name = _call_name_attr(node)
                if name in old_names:
                    violations.append(
                        Violation(
                            rule="module-level-caller",
                            path=rel,
                            line=node.lineno,
                            message=f"module-level call to deprecated name {name!r}",
                        )
                    )
                self.generic_visit(node)

        visitor = ModuleCallVisitor()
        for stmt in tree.body:
            visitor.visit(stmt)

    return violations


def _check_import_boundary(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in _iter_py_files(root):
        if _is_test_or_conftest(path):
            continue
        tree = _read_ast(path)
        if tree is None or not isinstance(tree, ast.Module):
            continue
        rel = _rel(root, path)

        for stmt in tree.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    top = alias.name.split(".")[0]
                    if top in OPTIONAL_PACKAGES:
                        violations.append(
                            Violation(
                                rule="import-boundary",
                                path=rel,
                                line=stmt.lineno,
                                message=(
                                    f"module-level import of optional dependency {top!r}"
                                ),
                            )
                        )
            elif isinstance(stmt, ast.ImportFrom):
                if stmt.module:
                    top = stmt.module.split(".")[0]
                    if top in OPTIONAL_PACKAGES:
                        violations.append(
                            Violation(
                                rule="import-boundary",
                                path=rel,
                                line=stmt.lineno,
                                message=(
                                    f"module-level import of optional dependency {top!r}"
                                ),
                            )
                        )
    return violations


def run(root, min_version="3.8"):
    """Run all guard rules. Returns (violations, number_of_deprecations_checked)."""
    root = Path(root)
    deps, format_violations = _discover_deprecations(root, min_version)
    violations: list[Violation] = list(format_violations)
    violations.extend(_check_touchpoints(root, deps))
    violations.extend(_check_module_level_callers(root, deps))
    violations.extend(_check_import_boundary(root))
    return violations, len(deps)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Acme convention guard")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument(
        "--min-version",
        default="3.8",
        help="ignore deprecations older than this version (default: 3.8)",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not (root / "networkx").is_dir():
        print(f"acme-guard: no networkx/ package under {root}", file=sys.stderr)
        return 2

    violations, ndeps = run(root, min_version=args.min_version)
    n = len(violations)
    print(
        f"acme-guard: 3 rules checked, {ndeps} Acme-era deprecation(s), {n} violations"
    )
    for v in violations:
        print(f"[{v.rule}] {v.path}:{v.line} {v.message}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
