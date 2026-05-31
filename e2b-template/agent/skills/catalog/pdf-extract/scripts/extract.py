# /// script
# dependencies = [
#   "pdfplumber>=0.10.0",
# ]
# ///
"""
Extract text, tables, or metadata from a PDF file.

Usage:
  uv run extract.py <pdf_file> [--output text|tables|meta] [--pages N-M] [--search PATTERN] [--format csv|json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract content from a PDF file.")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--output", choices=["text", "tables", "meta"], default="text",
                        help="What to extract (default: text)")
    parser.add_argument("--pages", default="",
                        help="Page range, e.g. '1-10' or '3' (default: all)")
    parser.add_argument("--search", default="",
                        help="Filter text output to lines matching this regex")
    parser.add_argument("--format", choices=["csv", "json", "plain"], default="plain",
                        help="Output format for tables (default: plain)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    try:
        import pdfplumber
    except ImportError:
        print("error: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
        sys.exit(1)

    with pdfplumber.open(str(pdf_path)) as pdf:
        total_pages = len(pdf.pages)
        page_indices = _parse_pages(args.pages, total_pages)

        if args.output == "meta":
            meta = {
                "file": str(pdf_path),
                "total_pages": total_pages,
                "metadata": pdf.metadata or {},
            }
            print(json.dumps(meta, indent=2, default=str))
            return

        if args.output == "text":
            pattern = re.compile(args.search, re.IGNORECASE) if args.search else None
            for i in page_indices:
                page = pdf.pages[i]
                text = page.extract_text() or ""
                if pattern:
                    lines = [ln for ln in text.splitlines() if pattern.search(ln)]
                    if lines:
                        print(f"--- Page {i + 1} ---")
                        print("\n".join(lines))
                else:
                    print(f"--- Page {i + 1} ---")
                    print(text or "(no text on this page)")
            return

        if args.output == "tables":
            for i in page_indices:
                page = pdf.pages[i]
                tables = page.extract_tables()
                if not tables:
                    continue
                for t_idx, table in enumerate(tables):
                    if args.format == "json":
                        print(json.dumps({"page": i + 1, "table": t_idx + 1, "data": table}))
                    elif args.format == "csv":
                        writer = csv.writer(sys.stdout)
                        print(f"# Page {i + 1}, Table {t_idx + 1}")
                        for row in table:
                            writer.writerow([c or "" for c in row])
                    else:
                        print(f"--- Page {i + 1}, Table {t_idx + 1} ---")
                        for row in table:
                            print(" | ".join(str(c or "") for c in row))
            return


def _parse_pages(spec: str, total: int) -> list[int]:
    if not spec:
        return list(range(total))
    spec = spec.strip()
    if "-" in spec:
        parts = spec.split("-", 1)
        start = max(0, int(parts[0]) - 1)
        end = min(total, int(parts[1]))
        return list(range(start, end))
    return [max(0, min(int(spec) - 1, total - 1))]


if __name__ == "__main__":
    main()
