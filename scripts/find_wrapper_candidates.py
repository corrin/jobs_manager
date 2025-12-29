#!/usr/bin/env python
"""
Find wrapper function candidates - short functions with few callers.

Usage: python scripts/find_wrapper_candidates.py [--max-lines N] [--max-callers N] [--output FILE]
"""

import ast
import json
import sys
from collections import defaultdict
from pathlib import Path


def count_function_lines(node: ast.FunctionDef) -> int:
    """Count non-empty, non-docstring lines in a function."""
    if not node.body:
        return 0

    # Skip docstring if present
    start_idx = 0
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        start_idx = 1

    return len(node.body) - start_idx


def extract_functions_and_calls(filepath: Path) -> tuple[dict, set]:
    """Extract function definitions and function calls from a file."""
    functions = {}  # name -> (filepath, lineno, num_lines)
    calls = set()  # set of function names called

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return functions, calls

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.current_class = None

        def visit_ClassDef(self, node):
            old_class = self.current_class
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = old_class

        def visit_FunctionDef(self, node):
            # Create qualified name
            if self.current_class:
                name = f"{self.current_class}.{node.name}"
            else:
                name = node.name

            num_lines = count_function_lines(node)
            functions[name] = (str(filepath), node.lineno, num_lines)
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node):
            # Extract function name from call
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            self.generic_visit(node)

    Visitor().visit(tree)
    return functions, calls


def main():
    max_lines = 3
    max_callers = 3
    output_file = None

    # Parse args
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--max-lines" and i + 1 < len(args):
            max_lines = int(args[i + 1])
            i += 2
        elif args[i] == "--max-callers" and i + 1 < len(args):
            max_callers = int(args[i + 1])
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        else:
            i += 1

    # Collect all functions and calls
    all_functions = {}  # name -> (filepath, lineno, num_lines)
    call_counts = defaultdict(int)  # name -> count

    apps_dir = Path("apps")
    for py_file in apps_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        functions, calls = extract_functions_and_calls(py_file)
        all_functions.update(functions)

        for call in calls:
            call_counts[call] += 1

    # Find candidates: short functions with few callers
    candidates = []
    for name, (filepath, lineno, num_lines) in all_functions.items():
        # Skip dunder methods and properties
        base_name = name.split(".")[-1]
        if base_name.startswith("__") and base_name.endswith("__"):
            continue

        callers = call_counts.get(base_name, 0)

        if num_lines <= max_lines and callers <= max_callers and callers > 0:
            candidates.append(
                {
                    "name": name,
                    "filepath": filepath,
                    "lineno": lineno,
                    "num_lines": num_lines,
                    "callers": callers,
                    "status": "pending",  # pending, fixed, keep
                    "notes": "",
                }
            )

    # Sort by lines then callers
    candidates.sort(key=lambda x: (x["num_lines"], x["callers"]))

    if output_file:
        with open(output_file, "w") as f:
            json.dump(candidates, f, indent=2)
        print(f"Wrote {len(candidates)} candidates to {output_file}")
    else:
        print(f"Wrapper candidates (≤{max_lines} lines, ≤{max_callers} callers):\n")
        print(f"{'Function':<50} {'Location':<45} {'Lines':>5} {'Callers':>7}")
        print("-" * 110)

        for c in candidates[:50]:
            loc = f"{c['filepath']}:{c['lineno']}"
            print(f"{c['name']:<50} {loc:<45} {c['num_lines']:>5} {c['callers']:>7}")

        print(f"\nTotal candidates: {len(candidates)}")


if __name__ == "__main__":
    main()
