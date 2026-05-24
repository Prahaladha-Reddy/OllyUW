---
name: pdf-extraction
description: Use when processing PDF files — extracting text, handling scanned documents, converting to markdown for analysis
---

# PDF Extraction Guide

Use this skill when you need to read a PDF file from the workspace. PDFs arrive in two variants: **text-extractable** (digital) and **scanned** (image-only). The strategy differs.

---

## Step 1 — Determine PDF type

```bash
# Check if pdfplumber can find any text
run_shell("python3 -c \"import pdfplumber; f=pdfplumber.open('/home/user/workspace/FILENAME.pdf'); p=f.pages[0]; print(len(p.extract_text() or ''), 'chars on page 1')\"")
```

- If > 100 chars → **text-extractable**, use pdfplumber
- If 0 or very few chars → **scanned**, use OCR fallback

---

## Step 2a — Text-extractable PDF (pdfplumber)

Extract all text to a markdown file:

```bash
run_shell("""python3 - <<'EOF'
import pdfplumber, pathlib, sys

src = pathlib.Path('/home/user/workspace/FILENAME.pdf')
out = src.with_suffix('.md')

lines = []
with pdfplumber.open(src) as pdf:
    for i, page in enumerate(pdf.pages, 1):
        text = page.extract_text() or ''
        if text.strip():
            lines.append(f'\\n## Page {i}\\n')
            lines.append(text)

out.write_text('\\n'.join(lines), encoding='utf-8')
print(f'wrote {len(lines)} chunks → {out.name}')
EOF
""")
```

### Extract tables from a PDF

pdfplumber has first-class table extraction:

```bash
run_shell("""python3 - <<'EOF'
import pdfplumber, pathlib, json

src = pathlib.Path('/home/user/workspace/FILENAME.pdf')
tables = []
with pdfplumber.open(src) as pdf:
    for i, page in enumerate(pdf.pages, 1):
        for j, table in enumerate(page.extract_tables(), 1):
            tables.append({'page': i, 'table': j, 'data': table})

# Print as simple markdown tables
for t in tables[:5]:  # first 5 tables
    rows = t['data']
    if not rows:
        continue
    header = '| ' + ' | '.join(str(c or '') for c in rows[0]) + ' |'
    sep = '| ' + ' | '.join('---' for _ in rows[0]) + ' |'
    body = '\n'.join('| ' + ' | '.join(str(c or '') for c in row) + ' |' for row in rows[1:])
    print(f"Page {t['page']} Table {t['table']}:")
    print(header); print(sep); print(body); print()
EOF
""")
```

---

## Step 2b — Scanned PDF (OCR via pytesseract + PyMuPDF)

Convert each page to image, then OCR:

```bash
run_shell("""python3 - <<'EOF'
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io, pathlib

src = pathlib.Path('/home/user/workspace/FILENAME.pdf')
out = src.with_suffix('.md')

lines = []
doc = fitz.open(src)
for i, page in enumerate(doc, 1):
    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR accuracy
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes('png')))
    text = pytesseract.image_to_string(img, lang='eng')
    if text.strip():
        lines.append(f'\\n## Page {i} (OCR)\\n')
        lines.append(text)

out.write_text('\\n'.join(lines), encoding='utf-8')
print(f'wrote {len(lines)} sections → {out.name}')
EOF
""")
```

---

## Step 3 — Handle large PDFs (100+ pages)

For very large documents, extract specific page ranges rather than the whole file:

```bash
# Extract pages 1-30 of a large SOC 2
run_shell("""python3 - <<'EOF'
import pdfplumber, pathlib

src = pathlib.Path('/home/user/workspace/soc2_report.pdf')
out = pathlib.Path('/home/user/workspace/soc2_report_p1-30.md')

lines = []
with pdfplumber.open(src) as pdf:
    total = len(pdf.pages)
    print(f'Total pages: {total}')
    for i in range(min(30, total)):
        text = pdf.pages[i].extract_text() or ''
        if text.strip():
            lines.append(f'\\n## Page {i+1}\\n{text}')

out.write_text('\\n'.join(lines), encoding='utf-8')
print(f'wrote pages 1-30 → {out.name}')
EOF
""")
```

---

## Step 4 — Search without reading everything

For large PDFs, grep for specific keywords before reading full pages:

```bash
# Find all pages mentioning "HITL" or "human-in-the-loop"
run_shell("""python3 - <<'EOF'
import pdfplumber, pathlib, re

src = pathlib.Path('/home/user/workspace/system_prompt.pdf')
pattern = re.compile(r'(HITL|human.in.the.loop|human approval|human review)', re.IGNORECASE)

with pdfplumber.open(src) as pdf:
    for i, page in enumerate(pdf.pages, 1):
        text = page.extract_text() or ''
        for m in pattern.finditer(text):
            start = max(0, m.start()-80)
            end = min(len(text), m.end()+80)
            print(f'Page {i}: ...{text[start:end].strip()}...')
EOF
""")
```

---

## Installing missing libraries

If pdfplumber / pytesseract / fitz are not installed:

```bash
run_shell("pip install -q pdfplumber pymupdf pytesseract pillow 2>&1 | tail -3")
```

tesseract-ocr (the binary) should already be in the sandbox image. If not:
```bash
run_shell("apt-get install -y -q tesseract-ocr 2>&1 | tail -3")
```

---

## Output convention

Always write extracted text to `ORIGINAL_NAME.md` in the same directory as the source PDF. This makes the file available to `grep_files` and `read_file` for subsequent analysis.

After extraction, report: filename, page count, extraction method (text/OCR), and any errors encountered.
