# /// script
# dependencies = [
#   "pandas>=2.0.0",
# ]
# ///
"""
Quick data analysis for CSV/JSON files.

Usage:
  uv run analyse.py <file> --summary
  uv run analyse.py <file> --column <col> --stats
  uv run analyse.py <file> --filter "col == 'value'" --output out.csv
  uv run analyse.py <file> --top N --sort-by <col>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick data analysis")
    parser.add_argument("file", help="CSV or JSON file")
    parser.add_argument("--summary", action="store_true", help="Print shape, dtypes, and describe()")
    parser.add_argument("--column", default="", help="Column to analyse")
    parser.add_argument("--stats", action="store_true", help="Statistics for --column")
    parser.add_argument("--filter", default="", help="Pandas query expression e.g. \"age > 30\"")
    parser.add_argument("--output", default="", help="Save result to this file")
    parser.add_argument("--top", type=int, default=0, help="Show top N rows")
    parser.add_argument("--sort-by", default="", dest="sort_by", help="Column to sort by")
    args = parser.parse_args()

    try:
        import pandas as pd
    except ImportError:
        print("error: pandas not installed. Run: pip install pandas", file=sys.stderr)
        sys.exit(1)

    path = Path(args.file)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    # Load
    if path.suffix.lower() == ".json":
        df = pd.read_json(str(path))
    else:
        df = pd.read_csv(str(path))

    # Apply filter
    if args.filter:
        try:
            df = df.query(args.filter)
        except Exception as e:
            print(f"error in filter expression: {e}", file=sys.stderr)
            sys.exit(1)

    # Sort
    if args.sort_by and args.sort_by in df.columns:
        df = df.sort_values(args.sort_by, ascending=False)

    # Summary
    if args.summary:
        print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nNull counts:\n{df.isnull().sum().to_string()}")
        print(f"\nDescribe:\n{df.describe(include='all').to_string()}")

    # Column stats
    if args.column and args.stats:
        if args.column not in df.columns:
            print(f"error: column '{args.column}' not found. Available: {list(df.columns)}", file=sys.stderr)
            sys.exit(1)
        col = df[args.column]
        if pd.api.types.is_numeric_dtype(col):
            print(f"Column: {args.column} ({len(col)} rows, {col.isnull().sum()} nulls)")
            print(f"  min={col.min():.4g}  max={col.max():.4g}  mean={col.mean():.4g}  median={col.median():.4g}")
            print(f"  std={col.std():.4g}  p25={col.quantile(0.25):.4g}  p75={col.quantile(0.75):.4g}")
        else:
            vc = col.value_counts().head(20)
            print(f"Column: {args.column} ({len(col)} rows, {col.nunique()} unique)")
            print(vc.to_string())

    # Top N
    if args.top > 0 and not args.summary and not args.stats:
        print(df.head(args.top).to_string())

    # Output
    if args.output:
        out = Path(args.output)
        if out.suffix.lower() == ".json":
            df.to_json(str(out), orient="records", indent=2)
        else:
            df.to_csv(str(out), index=False)
        print(f"saved {len(df)} rows → {out}")

    # Default: just print shape if nothing else requested
    if not any([args.summary, args.column, args.top, args.output]):
        print(f"{path.name}: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
