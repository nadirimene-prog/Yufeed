"""Helpers for mapping Official Journal references to act-by-act identifiers."""

from __future__ import annotations

import re
from typing import Optional


_SERIES_MAP = {
    "JOL": "L",
    "JOC": "C",
}


def build_act_identifier(series: str, year: int, issue: int) -> str:
    """Build act-by-act identifier like L_202302386 from series/year/issue."""
    return f"{series}_{year}{issue:05d}"


def extract_oj_act_identifier(oj_ref: Optional[str]) -> Optional[str]:
    """Extract act-by-act identifier from an OJ reference string."""
    if not oj_ref:
        return None

    ref = oj_ref.strip().upper()

    direct_match = re.search(r"\b([A-Z]{1,3}_[0-9]{9})\b", ref)
    if direct_match:
        return direct_match.group(1)

    jol_match = re.search(r"\b(JOL|JOC)_([0-9]{4})_([0-9]{1,5})\b", ref)
    if jol_match:
        series_key, year_str, issue_str = jol_match.groups()
        series = _SERIES_MAP.get(series_key)
        if not series:
            return None
        return build_act_identifier(series, int(year_str), int(issue_str))

    return None


def extract_oj_series(oj_ref: Optional[str]) -> Optional[str]:
    if not oj_ref:
        return None

    act_identifier = extract_oj_act_identifier(oj_ref)
    if act_identifier:
        match = re.match(r"^([A-Z]{1,3})_", act_identifier)
        if match:
            return match.group(1)

    ref = oj_ref.strip().upper()
    if "JOL" in ref:
        return "L"
    if "JOC" in ref:
        return "C"

    series_match = re.search(r"\bOJ\s*([A-Z]{1,3})\b", ref)
    if series_match:
        return series_match.group(1)

    return None
