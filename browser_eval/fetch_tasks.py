"""
Downloads WebVoyager benchmark tasks from Hugging Face and saves them to tasks.json.

WebVoyager: 643 tasks across 15 real websites with reference answers.
Paper: https://arxiv.org/abs/2401.13919

Run once before eval:
    python fetch_tasks.py
    python fetch_tasks.py --sites arxiv wikipedia github  # only those sites
    python fetch_tasks.py --limit 50                       # first N tasks
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TASKS_FILE = Path(__file__).parent / "tasks.json"

# WebVoyager site names as they appear in the dataset
ALL_SITES = [
    "allrecipes", "amazon", "apple", "arxiv", "bbc", "booking",
    "cambridge", "coursera", "espn", "github", "googleflights",
    "googlemaps", "google", "huggingface", "wolframalpha",
]

# Sites that work well without login or CAPTCHA issues
SAFE_SITES = [
    "arxiv", "wikipedia", "github", "bbc", "cambridge",
    "google", "huggingface", "wolframalpha", "allrecipes", "apple",
]


WEBVOYAGER_URL = (
    "https://raw.githubusercontent.com/MinorJerry/WebVoyager/main/data/WebVoyager_data.jsonl"
)


def fetch_from_github(sites: list[str], limit: int | None) -> list[dict]:
    import urllib.request

    print("Downloading WebVoyager tasks from GitHub...")
    with urllib.request.urlopen(WEBVOYAGER_URL, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    # Group by site first so we can sample evenly
    by_site: dict[str, list[dict]] = {}
    for line in lines:
        row: dict      = json.loads(line)
        web_name: str  = str(row.get("web_name") or "")
        key            = web_name.lower().replace(" ", "")

        if sites and not any(s in key for s in sites):
            continue

        ref = row.get("answer") or []
        if isinstance(ref, str):
            ref = [ref]
        elif not isinstance(ref, list):
            ref = [str(ref)] if ref else []

        by_site.setdefault(web_name, []).append({
            "source":      "webvoyager",
            "web_name":    web_name,
            "start_url":   str(row.get("web") or ""),
            "description": str(row.get("ques") or ""),
            "reference":   ref,
        })

    # Round-robin across sites for diversity
    site_names = sorted(by_site.keys())
    indices    = {s: 0 for s in site_names}
    tasks: list[dict] = []
    cap = limit or 10_000

    while len(tasks) < cap:
        added = False
        for site in site_names:
            if len(tasks) >= cap:
                break
            idx = indices[site]
            if idx < len(by_site[site]):
                entry = dict(by_site[site][idx])
                entry["id"] = len(tasks) + 1
                tasks.append(entry)
                indices[site] += 1
                added = True
        if not added:
            break

    return tasks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sites", nargs="+", default=None,
        help=f"Only include these sites (default: all). Options: {ALL_SITES}",
    )
    parser.add_argument(
        "--safe-only", action="store_true",
        help=f"Only include sites that work well without login: {SAFE_SITES}",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Maximum number of tasks to download",
    )
    args = parser.parse_args()

    sites = args.sites or (SAFE_SITES if args.safe_only else [])

    tasks = fetch_from_github(sites=sites, limit=args.limit)

    TASKS_FILE.write_text(json.dumps(tasks, indent=2, ensure_ascii=False))
    print(f"Saved {len(tasks)} tasks to {TASKS_FILE}")

    # Print breakdown by site
    by_site: dict[str, int] = {}
    for t in tasks:
        by_site[t["web_name"]] = by_site.get(t["web_name"], 0) + 1
    print("\nBreakdown by site:")
    for site, count in sorted(by_site.items(), key=lambda x: -x[1]):
        print(f"  {site:20s} {count}")


if __name__ == "__main__":
    main()
