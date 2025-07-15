#!/usr/bin/env python3
"""
Script to audit view documentation coverage.
Compares actual view files with existing documentation.
"""

import glob
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def find_view_files():
    """Find all views.py and view-related Python files."""
    view_files = []

    # Find all Python files in views directories
    view_patterns = ["apps/*/views.py", "apps/*/views/*.py", "apps/*/views/*/*.py"]

    for pattern in view_patterns:
        files = glob.glob(pattern)
        view_files.extend(files)

    return sorted(view_files)


def find_documented_views():
    """Find all existing view documentation."""
    doc_dirs = []
    docs_views_path = "docs/views"

    if os.path.exists(docs_views_path):
        for item in os.listdir(docs_views_path):
            item_path = os.path.join(docs_views_path, item)
            if os.path.isdir(item_path):
                readme_path = os.path.join(item_path, "README.md")
                if os.path.exists(readme_path):
                    doc_dirs.append(item)

    return sorted(doc_dirs)


def extract_view_names_from_file(filepath):
    """Extract view/class names from a Python file."""
    view_names = []
    try:
        with open(filepath, "r") as f:
            content = f.read()

        # Find class-based views (ending with View)
        import re

        class_views = re.findall(r"class\s+(\w+View\w*)", content)
        view_names.extend(class_views)

        # Find function-based views (def functions that take request)
        func_views = re.findall(r"def\s+(\w+)\s*\([^)]*request[^)]*\)", content)
        view_names.extend(func_views)

    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")

    return view_names


def main():
    logger.info("=== View Documentation Audit ===\n")

    # Find all view files
    view_files = find_view_files()
    logger.info(f"Found {len(view_files)} view files:")
    for vf in view_files:
        logger.info(f"  - {vf}")

    logger.info("")

    # Find documented views
    documented_views = find_documented_views()
    logger.info(f"Found {len(documented_views)} documented view directories:")
    for dv in documented_views:
        logger.info(f"  - {dv}")

    logger.info("")

    # Extract view names from files
    logger.info("=== View Analysis ===")
    all_view_names = set()
    file_to_views = {}

    for view_file in view_files:
        views_in_file = extract_view_names_from_file(view_file)
        if views_in_file:
            file_to_views[view_file] = views_in_file
            all_view_names.update(views_in_file)
            logger.info(f"{view_file}:")
            for view in views_in_file:
                logger.info(f"  - {view}")

    logger.info(f"Total unique view names found: {len(all_view_names)}")

    # Check coverage
    logger.info("=== Documentation Coverage ===")
    documented_set = set(documented_views)

    logger.info("Undocumented view files (high priority for Phase 2):")
    undocumented_files = []
    for view_file, views in file_to_views.items():
        os.path.basename(view_file).replace(".py", "")
        # app_name = view_file.split("/")[1]  # Extract app name
        # Commented out as we don't need app name currently

        # Check if any view from this file is documented
        documented = False
        for view_name in views:
            if view_name in documented_set:
                documented = True
                break

        if not documented:
            undocumented_files.append(view_file)
            logger.info(f"  - {view_file} ({len(views)} views)")

    logger.info("Summary:")
    logger.info(f"  - View files: {len(view_files)}")
    logger.info(f"  - Documented view directories: {len(documented_views)}")
    logger.info(f"  - Undocumented view files: {len(undocumented_files)}")
    logger.info(
        f"  - Coverage: {(len(documented_views)/(len(view_files) or 1)*100):.1f}%"
    )


if __name__ == "__main__":
    main()
