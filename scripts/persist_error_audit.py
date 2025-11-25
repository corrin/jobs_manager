#!/usr/bin/env python
"""
Temporary helper script to track persist_app_error usage.

Reports how many times each file calls persist_app_error and whether the
file references AlreadyLoggedException, which helps us spot modules that
still need to adopt the new exception propagation pattern.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class PersistUsage:
    path: str
    app: str
    persist_calls: int
    has_already_logged_reference: bool
    has_already_logged_except: bool
    has_already_logged_raise: bool

    @property
    def needs_attention(self) -> bool:
        """Heuristic flag for files that call persist_app_error without the new pattern."""
        return not self.has_already_logged_reference


def gather_usage(project_root: Path) -> list[PersistUsage]:
    apps_dir = project_root / "apps"
    results: list[PersistUsage] = []

    for path in apps_dir.rglob("*.py"):
        if not path.is_file():
            continue

        text = path.read_text(encoding="utf-8")
        persist_calls = text.count("persist_app_error")
        if persist_calls == 0:
            continue

        relative = path.relative_to(project_root)
        parts = relative.parts
        app = parts[1] if len(parts) > 1 else parts[0]

        has_reference = "AlreadyLoggedException" in text
        has_except = "except AlreadyLoggedException" in text
        has_raise = "raise AlreadyLoggedException" in text

        results.append(
            PersistUsage(
                path=str(relative),
                app=app,
                persist_calls=persist_calls,
                has_already_logged_reference=has_reference,
                has_already_logged_except=has_except,
                has_already_logged_raise=has_raise,
            )
        )
    return sorted(results, key=lambda entry: entry.path)


def summarize_by_app(usages: list[PersistUsage]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = defaultdict(
        lambda: {"files": 0, "persist_calls": 0, "needs_attention": 0}
    )
    for usage in usages:
        data = summary[usage.app]
        data["files"] += 1
        data["persist_calls"] += usage.persist_calls
        if usage.needs_attention:
            data["needs_attention"] += 1
    return dict(sorted(summary.items()))


def format_report(usages: list[PersistUsage]) -> str:
    summary = summarize_by_app(usages)
    lines: list[str] = []
    lines.append("persist_app_error usage report")
    lines.append("")
    lines.append("Per-app summary:")
    for app, data in summary.items():
        lines.append(
            f"  - {app}: files={data['files']}, "
            f"persist_calls={data['persist_calls']}, "
            f"needs_attention={data['needs_attention']}"
        )
    lines.append("")
    lines.append("Detailed files:")
    for usage in usages:
        lines.append(
            f"  * {usage.path}: persist_calls={usage.persist_calls}, "
            f"has_ref={usage.has_already_logged_reference}, "
            f"has_except={usage.has_already_logged_except}, "
            f"has_raise={usage.has_already_logged_raise}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report on persist_app_error usage across the apps/ directory."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of the human-readable report.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    usages = gather_usage(project_root)

    if args.json:
        payload = {
            "usages": [asdict(usage) for usage in usages],
            "summary": summarize_by_app(usages),
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_report(usages))


if __name__ == "__main__":
    main()
