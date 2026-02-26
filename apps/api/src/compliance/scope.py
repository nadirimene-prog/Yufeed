from __future__ import annotations

from typing import Any, Iterable, List, NamedTuple, Optional

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
    "psan": "vasp",
    "psp": "psp",
    "vasp": "vasp",
    "casp": "vasp",
}

SCOPE_ALL_TOKENS = {"all", "*", "any"}


class ScopeParseResult(NamedTuple):
    scopes: List[str]
    invalid_tokens: List[str]
    explicit_all: bool
    tokens: List[str]


def _tokenize_scope_input(scope: Optional[Any]) -> List[str]:
    if scope is None:
        return []
    if isinstance(scope, str):
        raw_tokens = scope.split(",")
    elif isinstance(scope, (list, tuple, set)):
        raw_tokens = []
        for item in scope:
            if item is None:
                continue
            raw_tokens.extend(str(item).split(","))
    else:
        raw_tokens = str(scope).split(",")
    return [item.strip().lower() for item in raw_tokens if str(item).strip()]


def parse_scopes(scope: Optional[Any]) -> ScopeParseResult:
    tokens = _tokenize_scope_input(scope)
    if not tokens:
        return ScopeParseResult(scopes=[], invalid_tokens=[], explicit_all=False, tokens=[])

    explicit_all = any(token in SCOPE_ALL_TOKENS for token in tokens)
    normalized: List[str] = []
    invalid_tokens: List[str] = []

    for token in tokens:
        if token in SCOPE_ALL_TOKENS:
            continue
        canonical = SCOPE_ALIASES.get(token, token)
        if canonical in SCOPE_KEYWORDS:
            if canonical not in normalized:
                normalized.append(canonical)
            continue
        if token not in invalid_tokens:
            invalid_tokens.append(token)

    return ScopeParseResult(
        scopes=normalized,
        invalid_tokens=invalid_tokens,
        explicit_all=explicit_all,
        tokens=tokens,
    )


def normalize_scopes(scope: Optional[str]) -> List[str]:
    parsed = parse_scopes(scope)
    if parsed.explicit_all:
        return []
    return parsed.scopes


def normalize_scope_tags(values: Optional[Any]) -> List[str]:
    parsed = parse_scopes(values)
    return parsed.scopes


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


def match_scope_filter(
    scope_filter: Optional[Any],
    *values: Any,
    fail_closed_on_invalid: bool = False,
) -> tuple[bool, ScopeParseResult]:
    parsed = parse_scopes(scope_filter)
    if parsed.invalid_tokens:
        return (False if fail_closed_on_invalid else True), parsed
    if parsed.explicit_all or not parsed.scopes:
        return True, parsed
    keywords = scope_keywords(parsed.scopes)
    if not keywords:
        return True, parsed
    haystack = _build_scope_haystack(values)
    if not haystack:
        return True, parsed
    return any(keyword in haystack for keyword in keywords), parsed


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
