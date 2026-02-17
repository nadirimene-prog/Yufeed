"""
Helpers for dealing with missing/placeholder document titles.

CELLAR ingestion feeds sometimes emit placeholder values (for example "$item.title").
When that happens, we derive a usable title from extracted full text so that:
- the UI shows meaningful document names
- AI classification/scope tagging has better input
"""

from __future__ import annotations

import re
from typing import Optional, List

_PLACEHOLDER_TITLES = {
    "no title",
    "untitled",
    "$item.title",
}


def is_placeholder_title(title: Optional[str]) -> bool:
    if not title:
        return True
    normalized = title.strip()
    if not normalized:
        return True

    lower = normalized.lower()
    if lower in _PLACEHOLDER_TITLES:
        return True
    if "$item.title" in lower:
        return True

    # Common synthetic fallbacks that indicate we couldn't fetch metadata.
    if lower.startswith("eu publication "):
        return True
    if lower.startswith("official journal "):
        return True

    # Title that is "CELEX:xxxx" or only a CELEX-like identifier isn't useful for humans.
    if lower.startswith("celex:"):
        return True
    if re.fullmatch(r"[0-9]{1,5}[a-z]{1,3}[0-9]{1,6}[a-z0-9]*", lower):
        return True

    return False


_TITLE_KEYWORDS = (
    "regulation",
    "directive",
    "decision",
    "recommendation",
    "delegated regulation",
    "implementing regulation",
)


def derive_title_from_text(full_text: Optional[str]) -> Optional[str]:
    """
    Best-effort title detection from extracted full text.

    We keep it simple and deterministic:
    - take the first non-empty lines
    - prefer a line containing common act keywords (regulation/directive/decision/…)
    - join up to a few lines to accommodate titles split across lines
    """
    if not full_text:
        return None

    raw_lines = [line.strip() for line in full_text.splitlines()]
    lines: List[str] = []
    for line in raw_lines[:80]:
        if not line:
            continue
        if len(line) <= 2:
            continue
        lower = line.lower()
        if lower in {"en", "fr", "de", "it", "es"}:
            continue
        if "$item.title" in lower:
            continue
        # Skip obvious file-like lines sometimes present in FORMEX dumps.
        if re.match(r"^[LC]_[0-9]{4}", line):
            continue
        if re.match(r"^L_[0-9]{4}[0-9A-Z_.-]*$", line):
            continue
        lines.append(line)

    if not lines:
        return None

    start_idx = 0
    for idx, line in enumerate(lines[:25]):
        lower = line.lower()
        if any(keyword in lower for keyword in _TITLE_KEYWORDS):
            start_idx = idx
            break

    parts: List[str] = []
    for line in lines[start_idx : start_idx + 4]:
        lower = line.lower()
        # Stop if we reached preamble/procedural sections.
        if lower.startswith(("having regard", "whereas", "vu ", "considering")):
            break

        candidate = (" ".join(parts + [line])).strip()
        if len(candidate) > 200:
            break
        parts.append(line)

        # If we already have a decent length, don't over-join.
        if len(" ".join(parts)) >= 120:
            break

    title = re.sub(r"\\s+", " ", " ".join(parts)).strip()
    if not title:
        return None
    if not re.search(r"[A-Za-z]", title):
        return None
    if len(title) < 12:
        return None

    return title[:240]
