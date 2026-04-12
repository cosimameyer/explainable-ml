#!/usr/bin/env python3
"""
Generate the Python Libraries markdown table in README.md from docs/libraries.json.

libraries.json is the single source of truth. This script:
  1. Reads docs/libraries.json
  2. Builds the markdown table rows
  3. Replaces the table in README.md (between the header row and the next ## or EOF)

Usage:
    python scripts/generate_readme_table.py           # updates README.md in place
    python scripts/generate_readme_table.py --check   # exits 1 if README would change
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "docs" / "libraries.json"
README = ROOT / "README.md"

BOOL_EMOJI = {True: "✅", False: "❌"}


def build_link_cell(lib: dict) -> str:
    """Build the Link column markdown."""
    parts = []
    docs = lib.get("docs", "")
    pypi = lib.get("pypi", "")

    if docs:
        # Use "Documentation" as label unless the URL is a GitHub repo page
        if re.match(r"https?://github\.com/[^/]+/[^/]+/?$", docs):
            parts.append(f"[Documentation]({docs})")
        else:
            parts.append(f"[Documentation]({docs})")

    if pypi:
        parts.append(f"[PyPI]({pypi})")
    elif not pypi and not docs:
        # No links at all
        pass
    elif not pypi and docs and "github.com" in docs:
        # If docs is a GitHub URL and no PyPI, also offer GitHub link
        pass

    # If no docs but we have a GitHub repo, add GitHub link
    if not docs and lib.get("repo"):
        parts.append(f"[GitHub](https://github.com/{lib['repo']})")

    return ", ".join(parts)


def build_row(lib: dict) -> str:
    """Build a single markdown table row from a library dict."""
    repo = lib.get("repo", "")
    name = lib["name"]
    known_for = lib.get("known_for", "")
    description = lib.get("description", "")

    # Shields.io badges
    last_commit = f"![Last commit](https://img.shields.io/github/last-commit/{repo}?style=flat-square)" if repo else ""
    license_badge = f"![License](https://img.shields.io/github/license/{repo})" if repo else ""
    stars_badge = f"![GitHub Repo stars](https://img.shields.io/github/stars/{repo})" if repo else ""

    link_cell = build_link_cell(lib)

    cells = [
        f"`{name}`",
        known_for,
        description,
        link_cell,
        last_commit,
        license_badge,
        stars_badge,
        BOOL_EMOJI[lib.get("global", False)],
        BOOL_EMOJI[lib.get("local", False)],
        BOOL_EMOJI[lib.get("tabular", False)],
        BOOL_EMOJI[lib.get("text", False)],
        BOOL_EMOJI[lib.get("image", False)],
        BOOL_EMOJI[lib.get("timeseries", False)],
        BOOL_EMOJI[lib.get("blackbox", False)],
        BOOL_EMOJI[lib.get("whitebox", False)],
    ]
    return "| " + " | ".join(cells) + " |"


TABLE_HEADER = "| Python Library  | Known For | Description | Link | Latest Change | License | GitHub Repo Stars | Global | Local | Tabular | Text | Image | Time Series | Black-Box Models | White-Box Models |"
TABLE_SEP = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"


def generate_table(libs: list[dict]) -> str:
    """Generate the full markdown table string."""
    rows = [build_row(lib) for lib in libs]
    return "\n".join([TABLE_HEADER, TABLE_SEP] + rows)


def update_readme(libs: list[dict], check: bool = False) -> int:
    """Replace the table in README.md. Returns 0 on success, 1 if check fails."""
    old_content = README.read_text(encoding="utf-8")
    new_table = generate_table(libs)

    # Find the existing table: starts with the header line, ends before next ## or EOF
    # Pattern: from the table header line through all table rows (lines starting with |)
    lines = old_content.splitlines()
    table_start = None
    table_end = None

    for i, line in enumerate(lines):
        if line.strip().startswith("| Python Library"):
            table_start = i
            continue
        if table_start is not None and table_end is None:
            # Skip separator
            if line.strip().startswith("|---"):
                continue
            # Table rows start with |
            if line.strip().startswith("|") and line.strip():
                continue
            # First non-table line
            table_end = i
            break

    if table_start is None:
        print("ERROR: Could not find table header in README.md", file=sys.stderr)
        return 1

    if table_end is None:
        table_end = len(lines)

    # Rebuild the file
    new_lines = lines[:table_start] + new_table.splitlines() + lines[table_end:]
    new_content = "\n".join(new_lines) + "\n"

    if check:
        if old_content == new_content:
            print(f"README.md table is up to date ({len(libs)} libraries).")
            return 0
        else:
            print("README.md table is out of date. Run: python scripts/generate_readme_table.py",
                  file=sys.stderr)
            return 1

    README.write_text(new_content, encoding="utf-8")
    print(f"Updated README.md table ({len(libs)} libraries).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if README.md table would change.")
    args = parser.parse_args()

    if not JSON_PATH.exists():
        print(f"ERROR: {JSON_PATH} not found", file=sys.stderr)
        return 1

    libs = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return update_readme(libs, check=args.check)


if __name__ == "__main__":
    sys.exit(main())
