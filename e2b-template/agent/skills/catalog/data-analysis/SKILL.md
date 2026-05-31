---
name: data-analysis
description: Analyse CSV, JSON, or tabular data files. Summarise statistics, find patterns, filter rows, produce charts. Use when asked to analyse, explore, or summarise datasets.
---

# Data Analysis

## Workflow

1. **Peek at the file first** — `read_file(path, end_line=20)` to see structure and headers.
2. **Run quick stats** — use the script or inline Python via `run_shell`.
3. **Answer the specific question** — don't dump everything; focus on what was asked.
4. **Show your reasoning** — quote the numbers you found.

## Quick analysis with the script

```bash
uv run scripts/analyse.py data.csv --summary
uv run scripts/analyse.py data.csv --column revenue --stats
uv run scripts/analyse.py data.csv --filter "status == 'active'" --output filtered.csv
```

## Inline Python (when script not needed)

```python
python3 -c "
import csv, statistics
with open('data.csv') as f:
    rows = list(csv.DictReader(f))
vals = [float(r['revenue']) for r in rows if r['revenue']]
print(f'count={len(vals)} mean={statistics.mean(vals):.2f} median={statistics.median(vals):.2f}')
"
```

## For JSON data

```bash
python3 -c "import json, sys; data=json.load(open('data.json')); print(f'records: {len(data)}')"
```

Or use `jq` for filtering:
```bash
jq '.[] | select(.status == "active") | .name' data.json
```

## Reporting

Always include:
- Row/record count
- Key statistics relevant to the question (mean, median, min, max, counts)
- Any anomalies found (nulls, duplicates, outliers)
- A direct answer to the question asked

Use markdown tables for comparison data.
