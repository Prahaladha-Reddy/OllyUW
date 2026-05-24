"""
Layer 3 output validator.

The validator runs outside the model before final text is surfaced. It enforces
the underwriting-specific boundaries from the system design:

- final scoring memos need at least one citation per dimension score
- every quoted citation must match a substring of the cited file
- demographic attribution terms trigger review for scoring memos
- binder/policy issuance language is blocked
"""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field

_URL_RE = re.compile(r"https?://[^\s\)\]>\"']+")

_BINDER_PHRASES = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bhereby\s+(bind|bound|issuing)\b",
        r"\b(this\s+)(constitutes?|is)\s+(a\s+)?binder\b",
        r"\bpolicy\s+(number|no\.?)\s*[A-Z0-9-]{4,}",
        r"\bcertificate\s+of\s+insurance\b",
        r"\beffective\s+immediately.*coverage",
        r"\bcoverage\s+is\s+(bound|issued|effective)\b",
        r"\bclaim\s+(is\s+)?(approved|denied|adjudicated)\b",
    ]
]

_DEMOGRAPHIC_RE = re.compile(
    r"\b("
    r"protected\s+class|race|racial|ethnicity|ethnic|gender|national\s+origin|"
    r"nationality|religion|religious|caste|immigrant|immigrants|minority|"
    r"muslim|hindu|christian|jewish|founder\s+age|"
    r"indian[-\s]?subcontinent|east[-\s]?asian|west[-\s]?african|"
    r"bangalore|lagos|nigeria|nigerian"
    r")\b",
    re.IGNORECASE,
)

_DIMENSION_LINE_RE = re.compile(r"^\s*(D(?:[1-9]|1[0-2]))\b", re.IGNORECASE)
_MEMO_HINT_RE = re.compile(r"\b(RISK\s+SCORES?|OVERALL\s+SCORE|RISK\s+BAND|COVERAGE\s+RECOMMENDATION)\b", re.IGNORECASE)

_CITATION_PATTERNS = [
    re.compile(r'\[citation:\s*([^\],"]+?)\s*,\s*"([^"]+)"\s*\]', re.IGNORECASE),
    re.compile(r'\[source:\s*([^\],"]+?)(?:\s*,[^\]]*?)?\s*,\s*"([^"]+)"\s*\]', re.IGNORECASE),
    re.compile(
        r'\[([^\],"]+\.(?:md|txt|json|csv|yaml|yml|toml|pdf|docx|pptx))\s*,[^\]]*?"([^"]+)"\s*\]',
        re.IGNORECASE,
    ),
]


@dataclass(frozen=True)
class Citation:
    filename: str
    quote: str


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)

    def __iter__(self):
        """Backward-compatible unpacking as (is_valid, warnings)."""
        yield self.is_valid
        yield self.errors + self.warnings

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "citations": [asdict(citation) for citation in self.citations],
        }


def validate(
    output: str,
    tool_results: list[str] | None = None,
    source_texts: dict[str, str] | None = None,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    source_texts = source_texts or {}
    tool_results = tool_results or []

    citations = extract_citations(output)
    memo_like = _looks_like_scoring_memo(output)

    for pattern in _BINDER_PHRASES:
        match = pattern.search(output)
        if match:
            errors.append(
                "possible binder/policy/claim-adjudication language detected: "
                f"{_snippet(output, match.start(), match.end())!r}"
            )

    output_urls = set(_URL_RE.findall(output))
    if output_urls and tool_results:
        all_tool_text = "\n".join(tool_results)
        for url in output_urls:
            if url not in all_tool_text:
                warnings.append(f"unverified URL in output: {url}")

    if memo_like:
        _validate_dimension_citations(output, citations, errors)
        if _DEMOGRAPHIC_RE.search(output):
            match = _DEMOGRAPHIC_RE.search(output)
            errors.append(
                "demographic term appeared in memo body; review for demographic attribution: "
                f"{_snippet(output, match.start(), match.end())!r}"
            )

    if source_texts:
        _validate_quote_grounding(citations, source_texts, errors)
    elif citations and memo_like:
        errors.append("cannot verify citation quotes because no source documents were available")

    return ValidationResult(is_valid=not errors, errors=errors, warnings=warnings, citations=citations)


def extract_citations(text: str) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(text):
            filename = match.group(1).strip()
            quote = match.group(2).strip()
            if filename.lower().startswith(("citation:", "source:")):
                continue
            key = (filename, quote)
            if key in seen:
                continue
            seen.add(key)
            citations.append(Citation(filename=filename, quote=quote))
    return citations


def _validate_dimension_citations(output: str, citations: list[Citation], errors: list[str]) -> None:
    dimension_blocks = _dimension_blocks(output)
    if not dimension_blocks:
        return

    if not citations:
        errors.append("scoring memo contains dimension scores but no citations")

    for dimension, block in dimension_blocks:
        if not extract_citations(block):
            errors.append(f"{dimension} score is missing a citation")


def _validate_quote_grounding(
    citations: list[Citation],
    source_texts: dict[str, str],
    errors: list[str],
) -> None:
    for citation in citations:
        source_text = _find_source_text(citation.filename, source_texts)
        if source_text is None:
            errors.append(f"citation source not found: {citation.filename}")
            continue
        if citation.quote not in source_text:
            errors.append(
                f"citation quote not found verbatim in {citation.filename}: {citation.quote!r}"
            )


def _dimension_blocks(output: str) -> list[tuple[str, str]]:
    lines = output.splitlines()
    blocks: list[tuple[str, str]] = []
    for idx, line in enumerate(lines):
        match = _DIMENSION_LINE_RE.match(line)
        if not match:
            continue
        block_lines = [line]
        for next_line in lines[idx + 1 : idx + 5]:
            if _DIMENSION_LINE_RE.match(next_line) or next_line.strip().upper().startswith("OVERALL SCORE"):
                break
            block_lines.append(next_line)
        blocks.append((match.group(1).upper(), "\n".join(block_lines)))
    return blocks


def _looks_like_scoring_memo(output: str) -> bool:
    if _MEMO_HINT_RE.search(output):
        return True
    return len(_dimension_blocks(output)) >= 3


def _find_source_text(filename: str, source_texts: dict[str, str]) -> str | None:
    wanted = _normalise_filename(filename)
    for source_name, source_text in source_texts.items():
        if _normalise_filename(source_name) == wanted:
            return source_text
    return None


def _normalise_filename(filename: str) -> str:
    filename = filename.strip().strip("\"'")
    match = re.search(r"[^,\]\s]+\.(?:md|txt|json|csv|yaml|yml|toml|pdf|docx|pptx)", filename, re.IGNORECASE)
    if match:
        filename = match.group(0)
    return os.path.basename(filename).lower()


def _snippet(text: str, start: int, end: int) -> str:
    left = max(0, start - 40)
    right = min(len(text), end + 40)
    return text[left:right].replace("\n", " ").strip()
