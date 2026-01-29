from __future__ import annotations

from typing import Any, Iterable, List, Optional

SCOPE_KEYWORDS = {
    "psp": [
        "payment service",
        "payment services",
        "payment institution",
        "payment provider",
        "psd2",
        "psd3",
        "sepa",
        "instant payment",
        "instant payments",
        "iban",
        "card",
        "acquirer",
        "merchant",
        "open banking",
        "strong customer authentication",
        "sca",
    ],
    "eme": [
        "electronic money",
        "e-money",
        "e money",
        "emoney",
        "electronic money institution",
        "emi",
    ],
    "vasp": [
        "crypto",
        "crypto-asset",
        "cryptoasset",
        "virtual asset",
        "vasp",
        "dlt",
        "blockchain",
        "mica",
        "casp",
        "wallet",
        "custody",
        "token",
        "stablecoin",
        "asset-referenced token",
        "e-money token",
    ],
}

SCOPE_ALIASES = {
    "emi": "eme",
    "e-money": "eme",
    "emoney": "eme",
    "e_money": "eme",
    "psp": "psp",
    "vasp": "vasp",
    "casp": "vasp",
}


def normalize_scopes(scope: Optional[str]) -> List[str]:
    if not scope:
        return []
    tokens = [item.strip().lower() for item in scope.split(",") if item.strip()]
    if not tokens:
        return []
    if any(token in {"all", "*", "any"} for token in tokens):
        return []
    normalized: List[str] = []
    for token in tokens:
        canonical = SCOPE_ALIASES.get(token, token)
        if canonical in SCOPE_KEYWORDS and canonical not in normalized:
            normalized.append(canonical)
    return normalized


def scope_keywords(scopes: Iterable[str]) -> List[str]:
    keywords: List[str] = []
    for scope in scopes:
        keywords.extend(SCOPE_KEYWORDS.get(scope, []))
    deduped: List[str] = []
    seen = set()
    for keyword in keywords:
        if keyword in seen:
            continue
        seen.add(keyword)
        deduped.append(keyword)
    return deduped


def infer_scope_tags(*values: Any) -> List[str]:
    haystack = _build_scope_haystack(values)
    if not haystack:
        return []
    tags: List[str] = []
    for scope, keywords in SCOPE_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            tags.append(scope)
    return tags


def _build_scope_haystack(values: Iterable[Any]) -> str:
    parts: List[str] = []
    for value in values:
        _append_scope_text(parts, value)
    return " ".join(part for part in parts if part).lower()


def _append_scope_text(parts: List[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str):
        if value.strip():
            parts.append(value)
        return
    if isinstance(value, dict):
        for item in value.values():
            _append_scope_text(parts, item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _append_scope_text(parts, item)
