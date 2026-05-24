from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


@dataclass
class CitationCheck:
    filename: str
    quote: str
    ok: bool
    reason: str = ""


@dataclass
class CitationGroundingResult:
    checks: list[CitationCheck] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def accurate(self) -> int:
        return sum(1 for check in self.checks if check.ok)

    @property
    def precision(self) -> float:
        return self.accurate / self.total if self.total else 0.0


_CITATION_PATTERNS = [
    re.compile(r'\[citation:\s*([^\],"]+?)\s*,\s*"([^"]+)"\s*\]', re.IGNORECASE),
    re.compile(r'\[source:\s*([^\],"]+?)(?:\s*,[^\]]*?)?\s*,\s*"([^"]+)"\s*\]', re.IGNORECASE),
    re.compile(
        r'\[([^\],"]+\.(?:md|txt|json|csv|yaml|yml|toml|pdf|docx|pptx))\s*,[^\]]*?"([^"]+)"\s*\]',
        re.IGNORECASE,
    ),
]


def extract_citations(response: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(response):
            pair = (match.group(1).strip(), match.group(2).strip())
            if pair[0].lower().startswith(("citation:", "source:")):
                continue
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs


def check_quote_substrings(response: str, documents: dict[str, str]) -> CitationGroundingResult:
    checks: list[CitationCheck] = []
    for filename, quote in extract_citations(response):
        source = _find_document(filename, documents)
        if source is None:
            checks.append(CitationCheck(filename, quote, False, "source file not found"))
        elif quote not in source:
            checks.append(CitationCheck(filename, quote, False, "quote not found verbatim"))
        else:
            checks.append(CitationCheck(filename, quote, True))
    return CitationGroundingResult(checks=checks)


def citation_recall(response: str, required_quotes: list[str]) -> float:
    if not required_quotes:
        return 0.0
    found = sum(1 for quote in required_quotes if quote in response)
    return found / len(required_quotes)


def _find_document(filename: str, documents: dict[str, str]) -> str | None:
    wanted = os.path.basename(filename).lower()
    for doc_name, doc_text in documents.items():
        if os.path.basename(doc_name).lower() == wanted:
            return doc_text
    return None
