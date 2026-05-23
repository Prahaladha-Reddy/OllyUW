from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd

# File types that must go through Unstructured API
UNSTRUCTURED_EXTS: frozenset[str] = frozenset({".pdf", ".docx", ".doc", ".pptx", ".ppt"})

# File types we can convert locally
DIRECT_EXTS: frozenset[str] = frozenset({
    ".csv", ".json", ".md", ".txt", ".yaml", ".yml", ".toml",
})


def classify(filename: str) -> str:
    """Returns 'unstructured', 'direct', or 'rejected'."""
    suffix = Path(filename).suffix.lower()
    if suffix in UNSTRUCTURED_EXTS:
        return "unstructured"
    if suffix in DIRECT_EXTS:
        return "direct"
    return "rejected"


def elements_to_markdown(elements: list[dict]) -> str:
    """Convert Unstructured API elements list to a markdown string."""
    parts: list[str] = []
    last_page: int | None = None

    for el in elements:
        etype: str = el.get("type") or ""
        text: str = (el.get("text") or "").strip()
        metadata: dict = el.get("metadata") or {}

        if not text:
            continue

        page = metadata.get("page_number")
        if page and page != last_page:
            parts.append(f"<!-- page {page} -->")
            last_page = page

        if etype == "Title":
            parts.append(f"# {text}")
        elif etype in ("Header", "SectionHeader"):
            parts.append(f"## {text}")
        elif etype == "ListItem":
            parts.append(f"- {text}")
        elif etype == "PageBreak":
            parts.append("---")
        else:
            parts.append(text)

    return "\n\n".join(parts)


def convert_direct(content: bytes, filename: str) -> str:
    """Convert a directly-convertible file type to markdown."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(io.BytesIO(content))
        result = df.to_markdown(index=False)
        return result or ""

    text = content.decode("utf-8", errors="replace")

    if suffix == ".json":
        try:
            data = json.loads(text)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            return f"```json\n{formatted}\n```"
        except json.JSONDecodeError:
            return f"```json\n{text}\n```"

    if suffix in (".yaml", ".yml"):
        return f"```yaml\n{text}\n```"

    if suffix == ".toml":
        return f"```toml\n{text}\n```"

    # .md or .txt — pass through as-is
    return text
