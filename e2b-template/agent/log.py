
from __future__ import annotations

import json
import logging
import sys
from typing import Any

from agent.config import LOG_LEVEL

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

log = logging.getLogger("ollyuw.worker")


def preview(s: Any, n: int = 200) -> str:
    """Short, single-line preview of arbitrary content for log lines."""
    text = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False, default=str)
    text = text.replace("\n", "\\n")
    return text if len(text) <= n else text[:n] + f"...<+{len(text)-n}b>"
