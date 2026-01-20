#!/usr/bin/env python
"""Scan Python files for duplicate definitions that might result from bad merges."""

import ast
import sys
from collections import defaultdict
from pathlib import Path


class DuplicateFinder(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.issues = []
        self.current_class = None

    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name

        # Check for duplicate class-level attributes
        attrs = defaultdict(list)
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attrs[target.id].append(item.lineno)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attrs[item.target.id].append(item.lineno)

        for name, lines in attrs.items():
            if len(lines) > 1:
                self.issues.append(
                    f"{self.filename}:{lines[0]}: Duplicate attribute '{name}' in class '{node.name}' "
                    f"(also at lines {lines[1:]})"
                )

        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        # Check for duplicate dict keys in return statements and assignments
        for child in ast.walk(node):
            if isinstance(child, ast.Dict):
                self._check_dict_keys(child)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def _check_dict_keys(self, node):
        keys = defaultdict(list)
        for i, key in enumerate(node.keys):
            if key is None:
                continue
            if isinstance(key, ast.Constant):
                keys[key.value].append(key.lineno)
            elif isinstance(key, ast.Str):  # Python < 3.8
                keys[key.s].append(key.lineno)

        for name, lines in keys.items():
            if len(lines) > 1:
                ctx = f" in class '{self.current_class}'" if self.current_class else ""
                self.issues.append(
                    f"{self.filename}:{lines[0]}: Duplicate dict key '{name}'{ctx} "
                    f"(also at lines {lines[1:]})"
                )


def scan_file(filepath):
    try:
        with open(filepath, "r") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
        finder = DuplicateFinder(str(filepath))
        finder.visit(tree)
        return finder.issues
    except SyntaxError as e:
        return [f"{filepath}: Syntax error - {e}"]
    except Exception as e:
        return [f"{filepath}: Error - {e}"]


def main():
    apps_dir = Path(__file__).parent.parent / "apps"
    all_issues = []

    for py_file in apps_dir.rglob("*.py"):
        if "migrations" in str(py_file):
            continue
        issues = scan_file(py_file)
        all_issues.extend(issues)

    if all_issues:
        print("Found potential duplicates:\n")
        for issue in sorted(all_issues):
            print(issue)
        sys.exit(1)
    else:
        print("No duplicate definitions found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
