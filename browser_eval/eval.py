"""
Evaluation runner for the Gemini+BrowserOS browser agent.
Uses WebVoyager benchmark tasks (fetch with fetch_tasks.py first).

Usage:
    python eval.py                          # run all tasks
    python eval.py --sites arxiv github     # filter by website
    python eval.py --limit 20               # first N tasks
    python eval.py --ids 1 5 10             # specific task IDs
    python eval.py --dry-run                # preview without running
    python eval.py --resume                 # skip already-done tasks
    python eval.py --verbose                # show every tool call

Results → results/results.json  (updated after each task)
Summary → results/summary.csv
"""
from __future__ import annotations

import sys
sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
sys.stderr.reconfigure(line_buffering=True)  # type: ignore[union-attr]

import argparse
import csv
import json
from pathlib import Path
import sys
import time
from datetime import datetime
from pathlib import Path

from subagent import BrowserAgent, _mcp_tools_list, set_log_file, close_all_tabs

TASKS_FILE   = Path(__file__).parent / "tasks.json"
RESULTS_DIR  = Path(__file__).parent / "results"
RESULTS_JSON = RESULTS_DIR / "results.json"
SUMMARY_CSV  = RESULTS_DIR / "summary.csv"

INTER_TASK_SLEEP = 3.0   # seconds between tasks


# ── scoring ──────────────────────────────────────────────────────────────────

def score_output(output: str, reference: list[str]) -> bool:
    """
    Fuzzy check: task passes if ANY reference answer string appears
    in the agent output (case-insensitive).
    Returns True if no reference provided (manual review needed).
    """
    if not reference:
        return True   # no ground truth — assume pass, flag for manual review

    output_lower = output.lower()
    for ref in reference:
        if str(ref).lower() in output_lower:
            return True
    return False


def needs_manual_review(reference: list[str]) -> bool:
    return not reference


# ── helpers ──────────────────────────────────────────────────────────────────

def load_tasks(
    ids:   list[int] | None = None,
    sites: list[str] | None = None,
    limit: int        | None = None,
) -> list[dict]:
    if not TASKS_FILE.exists():
        raise SystemExit(
            f"tasks.json not found. Run first:\n"
            f"  python fetch_tasks.py\n"
            f"  python fetch_tasks.py --safe-only --limit 50\n"
        )

    tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))

    if ids:
        tasks = [t for t in tasks if t["id"] in ids]
    if sites:
        sites_lower = [s.lower() for s in sites]
        tasks = [t for t in tasks if any(s in t.get("web_name", "").lower() for s in sites_lower)]
    if limit:
        tasks = tasks[:limit]

    return tasks


def load_existing() -> dict[int, dict]:
    if RESULTS_JSON.exists():
        data = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
        return {r["task_id"]: r for r in data}
    return {}


def save_results(results: list[dict]) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False))


def save_summary_csv(results: list[dict]) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    fields = [
        "task_id", "web_name", "description",
        "agent_success", "score_pass", "manual_review",
        "turns", "tool_calls", "elapsed",
        "error", "output_preview", "reference",
    ]
    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({
                "task_id":       r["task_id"],
                "web_name":      r.get("web_name", ""),
                "description":   r.get("description", "")[:100],
                "agent_success": r["agent_success"],
                "score_pass":    r.get("score_pass", ""),
                "manual_review": r.get("manual_review", False),
                "turns":         r["turns"],
                "tool_calls":    r["tool_calls"],
                "elapsed":       r["elapsed"],
                "error":         r.get("error") or "",
                "output_preview": str(r.get("output", ""))[:120],
                "reference":     json.dumps(r.get("reference", [])),
            })


def _bar(n: int, total: int, width: int = 20) -> str:
    filled = int(width * n / total) if total else 0
    return "[" + "#" * filled + "-" * (width - filled) + f"] {n}/{total}"


def print_task_result(task: dict, result: dict) -> None:
    if result["agent_success"]:
        if result.get("manual_review"):
            icon, label = "?", "MANUAL"
        elif result.get("score_pass"):
            icon, label = "+", "PASS"
        else:
            icon, label = "x", "WRONG"
    else:
        icon, label = "x", "FAIL"

    print(f"  {icon} [{label:6s}] {task.get('web_name',''):15s} | turns={result['turns']:2d}  tools={result['tool_calls']:2d}  {result['elapsed']}s")
    if result.get("reference") and not result.get("manual_review"):
        print(f"    expected: {result['reference']}")
    if result.get("output"):
        print(f"    output:   {str(result['output'])[:120]}")
    if result.get("error"):
        print(f"    error:    {result['error']}")


def print_summary(results: list[dict]) -> None:
    total    = len(results)
    if not total:
        print("No results.")
        return

    agent_ok  = sum(1 for r in results if r["agent_success"])
    scored    = [r for r in results if not r.get("manual_review") and r["agent_success"]]
    passed    = sum(1 for r in scored if r.get("score_pass"))
    manual    = sum(1 for r in results if r.get("manual_review"))
    avg_turns = sum(r["turns"]      for r in results) / total
    avg_tools = sum(r["tool_calls"] for r in results) / total
    avg_time  = sum(r["elapsed"]    for r in results) / total
    total_time = sum(r["elapsed"]   for r in results)

    print(f"\n{'=' * 60}")
    print(f"  EVALUATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Tasks run        : {total}")
    print(f"  Agent completed  : {agent_ok}/{total}  ({100*agent_ok//total}%)")
    print(f"  Answer correct   : {passed}/{len(scored)}  ({100*passed//len(scored) if scored else 0}%)  [auto-scored]")
    if manual:
        print(f"  Manual review    : {manual}  (no reference answer available)")
    print(f"  Avg turns/task   : {avg_turns:.1f}")
    print(f"  Avg tools/task   : {avg_tools:.1f}")
    print(f"  Avg time/task    : {avg_time:.1f}s")
    print(f"  Total time       : {total_time:.0f}s  ({total_time/60:.1f} min)")

    # By site
    by_site: dict[str, list] = {}
    for r in results:
        site = r.get("web_name", "unknown")
        by_site.setdefault(site, []).append(r)

    if len(by_site) > 1:
        print(f"\n  By site:")
        for site, rows in sorted(by_site.items()):
            n      = len(rows)
            ok     = sum(1 for r in rows if r.get("score_pass"))
            manual = sum(1 for r in rows if r.get("manual_review"))
            pct    = 100 * ok // (n - manual) if (n - manual) else 0
            print(f"    {site:20s} {ok}/{n - manual} correct  ({pct}%)  {manual} manual")

    # Failed tasks
    failed = [r for r in results if not r["agent_success"]]
    if failed:
        print(f"\n  Agent failures ({len(failed)}):")
        for r in failed[:10]:
            err = (r.get("error") or "no output")[:70]
            print(f"    Task {r['task_id']:03d}: {err}")
        if len(failed) > 10:
            print(f"    ... and {len(failed) - 10} more")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids",       nargs="+", type=int, help="Run specific task IDs")
    parser.add_argument("--sites",     nargs="+",           help="Filter by site name (e.g. arxiv github)")
    parser.add_argument("--limit",     type=int,            help="Max tasks to run")
    parser.add_argument("--dry-run",   action="store_true", help="Print tasks without running")
    parser.add_argument("--resume",    action="store_true", help="Skip tasks already in results")
    parser.add_argument("--max-turns", type=int, default=30)
    args = parser.parse_args()

    tasks = load_tasks(ids=args.ids, sites=args.sites, limit=args.limit)
    if not tasks:
        print("No tasks matched the filters. Try running fetch_tasks.py first.")
        sys.exit(1)

    if args.dry_run:
        print(f"{len(tasks)} tasks:")
        for t in tasks:
            ref = t.get("reference", [])
            print(f"  [{t['id']:03d}] {t.get('web_name',''):15s} | {t['description'][:70]}")
            if ref:
                print(f"         expected: {ref}")
        return

    # Check BrowserOS
    print("Checking BrowserOS MCP...")
    tools = _mcp_tools_list()
    if tools is None:
        print(
            "\nERROR: BrowserOS not reachable.\n"
            "  1. Open BrowserOS\n"
            "  2. Settings → MCP → enable server\n"
            "  3. Confirm URL: http://127.0.0.1:9239/mcp\n"
        )
        sys.exit(1)
    print(f"Connected — {len(tools)} tools.\n")

    existing     = load_existing() if args.resume else {}
    set_log_file(RESULTS_DIR / "eval.log")
    agent        = BrowserAgent()
    all_results  = list(existing.values())
    run_start    = time.monotonic()

    print(f"{'=' * 60}")
    print(f"  Running {len(tasks)} tasks  |  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 60}\n")

    for i, task in enumerate(tasks, 1):
        tid = task["id"]

        if args.resume and tid in existing:
            print(f"  skip  Task {tid:03d} (already done)")
            continue

        print(f"\n[{i}/{len(tasks)}] {_bar(i, len(tasks))}  Task {tid:03d}  {task.get('web_name', '')}")
        print(f"  {task['description'][:90]}")

        close_all_tabs()   # fresh browser state for every task

        result = agent.run(
            goal      = task["description"],
            max_turns = args.max_turns,
        )

        # Score against reference answer
        reference    = task.get("reference") or []
        score_pass   = score_output(result.get("output", ""), reference) if result["success"] else False
        manual_flag  = needs_manual_review(reference) and result["success"]

        record = {
            "task_id":       tid,
            "web_name":      task.get("web_name", ""),
            "description":   task["description"],
            "start_url":     task.get("start_url", ""),
            "reference":     reference,
            "agent_success": result["success"],
            "score_pass":    score_pass,
            "manual_review": manual_flag,
            "turns":         result["turns"],
            "tool_calls":    result["tool_calls"],
            "output":        result.get("output", ""),
            "error":         result.get("error"),
            "elapsed":       result["elapsed"],
            "timestamp":     datetime.now().isoformat(),
        }

        print_task_result(task, record)

        all_results = [r for r in all_results if r["task_id"] != tid]
        all_results.append(record)
        save_results(all_results)

        if i < len(tasks):
            time.sleep(INTER_TASK_SLEEP)

    save_results(all_results)
    save_summary_csv(all_results)
    print_summary(all_results)

    elapsed = time.monotonic() - run_start
    print(f"\n  Results: {RESULTS_JSON}")
    print(f"  CSV:     {SUMMARY_CSV}")
    print(f"  Time:    {elapsed:.0f}s  ({elapsed/60:.1f} min)\n")


if __name__ == "__main__":
    main()
