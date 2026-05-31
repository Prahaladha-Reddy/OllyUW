---
name: pdf-extract
description: Extract text, tables, and metadata from PDF files. Use when asked to read, parse, summarise, or search inside PDFs.
---

# PDF Extraction

## Workflow

1. Run `scripts/extract.py --help` to see options.
2. For text extraction: `uv run scripts/extract.py <file.pdf> --output text`
3. For tables: `uv run scripts/extract.py <file.pdf> --output tables --format csv`
4. For metadata: `uv run scripts/extract.py <file.pdf> --output meta`

The script outputs to stdout. Pipe to a file with `> output.txt` if the content is large.

## For large PDFs

- Extract page by page: `--pages 1-10`
- Search for keywords: `--search "revenue"`
- The script never loads the whole PDF into your context — it streams output.

## When the script is not available

Use `run_shell` with pdfplumber directly:

```python
python3 -c "
import pdfplumber
with pdfplumber.open('file.pdf') as pdf:
    for i, page in enumerate(pdf.pages[:5], 1):
        print(f'--- Page {i} ---')
        print(page.extract_text() or '(no text)')
"
```

For tables:
```python
python3 -c "
import pdfplumber, json
with pdfplumber.open('file.pdf') as pdf:
    for i, page in enumerate(pdf.pages):
        for table in page.extract_tables():
            print(json.dumps(table))
"
```
