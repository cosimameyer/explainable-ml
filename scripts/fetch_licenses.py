#!/usr/bin/env python3
"""
Fetch GitHub metadata (stars, last commit, license) for each library and
write it into docs/libraries.json.

Usage:
    python scripts/fetch_licenses.py            # update libraries.json in place
    python scripts/fetch_licenses.py --dry-run  # print without writing

Unauthenticated rate limit is 60 req/hr.
Set GITHUB_TOKEN env var for 5 000 req/hr:
    export GITHUB_TOKEN=ghp_...
    python scripts/fetch_licenses.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "docs" / "libraries.json"


def gh_get(path: str, token: str | None) -> dict | None:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  404 Not Found for {url} — repo may have been deleted or renamed", file=sys.stderr)
        elif e.code == 403:
            print(f"  403 Forbidden for {url} — repo may be private, or rate limit hit", file=sys.stderr)
        else:
            print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return None


def fetch_repo_data(repo: str, token: str | None) -> dict | None:
    """Return a dict with stars, pushed_at, and license for the repo, or None."""
    data = gh_get(f"/repos/{repo}", token)
    if data is None:
        return None
    lic = data.get("license") or {}
    return {
        "stars": data.get("stargazers_count"),
        "pushed_at": data.get("pushed_at"),
        "license": lic.get("spdx_id") or lic.get("name") or None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print results without writing to JSON.")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("No GITHUB_TOKEN set — using unauthenticated requests (60 req/hr limit).")

    libs = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    changed = 0

    for lib in libs:
        repo = lib.get("repo", "")
        if not repo:
            for key in ("_stars", "_updated", "_license"):
                if key not in lib:
                    lib[key] = None
            continue

        print(f"  {repo} ...", end=" ", flush=True)
        result = fetch_repo_data(repo, token)
        if result is None:
            print("(failed)")
            continue

        for old_key, new_val in [
            ("_stars",   result["stars"]),
            ("_updated", result["pushed_at"]),
            ("_license", result["license"]),
        ]:
            if lib.get(old_key) != new_val:
                changed += 1
            lib[old_key] = new_val

        print(f"★ {result['stars']}  {result['pushed_at'] or '—'}  {result['license'] or '—'}")

        # Be polite to the API
        time.sleep(0.1)

    if args.dry_run:
        print(f"\nDry-run: {changed} change(s) detected, nothing written.")
        return 0

    JSON_PATH.write_text(json.dumps(libs, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    print(f"\nUpdated {JSON_PATH} ({changed} change(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
