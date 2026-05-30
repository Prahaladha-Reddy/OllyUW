"""
BM25-indexed deferred tool catalog.

Tools registered here are NOT sent to the LLM by default.
The LLM discovers them via tool_search / tool_describe / tool_call.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolEntry:
    name: str
    description: str
    schema: dict[str, Any]       # OpenAI function-call schema
    handler: Callable             # sync or async callable
    tags: list[str] = field(default_factory=list)


class ToolRegistry:
    """BM25-indexed catalog of deferred tools."""

    _K1: float = 1.5
    _B: float = 0.75

    def __init__(self) -> None:
        self._entries: dict[str, ToolEntry] = {}
        self._doc_tokens: dict[str, list[str]] = {}
        self._df: dict[str, int] = {}
        self._avg_len: float = 1.0

    def register(self, entry: ToolEntry) -> None:
        self._entries[entry.name] = entry
        self._reindex()

    def register_many(self, entries: list[ToolEntry]) -> None:
        for e in entries:
            self._entries[e.name] = e
        self._reindex()

    def search(self, query: str, top_k: int = 5) -> list[dict[str, str]]:
        """Return [{name, description}, ...] for top-k BM25 matches."""
        if not self._entries:
            return []
        qtokens = _tokenize(query)
        if not qtokens:
            return [
                {"name": e.name, "description": e.description}
                for e in list(self._entries.values())[:top_k]
            ]
        n = len(self._entries)
        scored: list[tuple[float, str]] = []
        for name, tokens in self._doc_tokens.items():
            score = self._bm25(qtokens, tokens, n)
            if score > 0:
                scored.append((score, name))
        scored.sort(reverse=True)
        return [
            {"name": self._entries[name].name, "description": self._entries[name].description}
            for _, name in scored[:top_k]
        ]

    def describe(self, name: str) -> dict[str, Any] | None:
        e = self._entries.get(name)
        return e.schema if e else None

    def get_handler(self, name: str) -> Callable | None:
        e = self._entries.get(name)
        return e.handler if e else None

    def all_names(self) -> list[str]:
        return list(self._entries.keys())

    def _reindex(self) -> None:
        self._doc_tokens = {}
        self._df = {}
        for name, entry in self._entries.items():
            doc = f"{entry.name} {entry.description} {' '.join(entry.tags)}"
            tokens = _tokenize(doc)
            self._doc_tokens[name] = tokens
            for t in set(tokens):
                self._df[t] = self._df.get(t, 0) + 1
        lengths = [len(t) for t in self._doc_tokens.values()]
        self._avg_len = sum(lengths) / len(lengths) if lengths else 1.0

    def _bm25(self, qtokens: list[str], doc_tokens: list[str], n: int) -> float:
        dl = len(doc_tokens)
        tf_map: dict[str, int] = {}
        for t in doc_tokens:
            tf_map[t] = tf_map.get(t, 0) + 1
        score = 0.0
        for t in qtokens:
            if t not in tf_map:
                continue
            tf = tf_map[t]
            df = self._df.get(t, 0)
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
            numer = tf * (self._K1 + 1)
            denom = tf + self._K1 * (1 - self._B + self._B * dl / self._avg_len)
            score += idf * numer / denom
        return score


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1]


_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    return _registry
