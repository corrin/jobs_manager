import os
import sys


def update_init_py(target_dir):
    init_file = os.path.join(target_dir, "__init__.py")

    # Check if the directory exists
    if not os.path.exists(target_dir):
        print(f"Skipping non-existent folder: {target_dir}")
        return

    # Get all Python files in the directory (excluding __init__.py)
    py_files = [
        f for f in os.listdir(target_dir) if f.endswith(".py") and f != "__init__.py"
    ]

    # Sanity check: Skip if no Python files are present
    if not py_files:
        print(
            f"No Python files found in {target_dir}. Skipping __init__.py generation."
        )
        return

    # Prepare import statements
    import_lines = [
        "# This file is autogenerated by update_init.py script",
        "# flake8: noqa",  # Suppress flake8 warnings globally for this file
        "",  # Add a blank line before the imports
    ]

    for py_file in py_files:
        module_name = py_file.replace(".py", "")
        import_lines.append(f"from .{module_name} import *  # noqa: F401, F403")

    # Write to __init__.py
    with open(init_file, "w") as init_f:
        init_f.write("\n".join(import_lines) + "\n")

    print(f"Successfully updated {init_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_init.py <folder_path>")
        sys.exit(1)

    folder = sys.argv[1]
    update_init_py(folder)
