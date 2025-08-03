import ast
import os

IGNORE_DIRS = [
    "migrations",
    "__pycache__",
    "venv",
    ".env",
    "mediafiles",
    "adhoc",
    ".git",
]


def scan_dirs(dirs):
    for base in dirs:
        for root, subdirs, files in os.walk(base):
            # Skip ignored directories
            subdirs[:] = [d for d in subdirs if d not in IGNORE_DIRS]
            for fn in files:
                if fn.endswith(".py"):
                    yield os.path.join(root, fn)


def find_empty_fstrings(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)

    # First we unite every JoinedStr that are format_spec of some FormattedValue
    format_specs = {
        fv.format_spec
        for fv in ast.walk(tree)
        if (isinstance(fv, ast.FormattedValue) and fv.format_spec is not None)
    }

    empties = []
    # Now we loop through the normal JoinedStr
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue

        # If it's a format_spec, skip it
        if node in format_specs:
            continue

        # Now we finally check if the f-string is empty
        has_placeholder = any(
            isinstance(part, ast.FormattedValue) for part in node.values
        )

        if not has_placeholder:
            empties.append((node.lineno, node.col_offset))

    return empties


if __name__ == "__main__":
    import sys

    paths = sys.argv[1:] or ["."]
    for pyfile in scan_dirs(paths):
        empties = find_empty_fstrings(pyfile)
        for line_number, col in empties:
            print(f"{pyfile}:{line_number}:{col}: f-string without placeholder found")
