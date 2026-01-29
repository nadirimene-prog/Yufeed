"""
Event normalization for Risk OS decisioning.
Converts incoming event variants into the canonical event schema.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


@dataclass
class NormalizedEvent:
    event_type: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    source: Optional[str]
    payload: Dict[str, Any]
    metadata: Dict[str, Any]


EVENT_TYPE_MAP = {
    "transaction.fiat": "txn_fiat",
    "txn.fiat": "txn_fiat",
    "fiat.transaction": "txn_fiat",
    "transaction.crypto": "txn_crypto",
    "txn.crypto": "txn_crypto",
    "crypto.transaction": "txn_crypto",
    "user.login": "login",
    "account.login": "login",
    "kyc.update": "kyc_update",
    "withdrawal.requested": "withdrawal_request",
    "deposit.detected": "deposit_detected",
    "chargeback.created": "chargeback",
    "sanctions.hit": "sanctions_hit",
}

ENTITY_TYPE_MAP = {
    "txn_fiat": "transaction",
    "txn_crypto": "transaction",
    "withdrawal_request": "account",
    "deposit_detected": "account",
    "chargeback": "transaction",
    "login": "account",
    "kyc_update": "entity",
    "sanctions_hit": "counterparty",
}


def normalize_event(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    source: Optional[str] = None,
) -> NormalizedEvent:
    payload = payload or {}
    normalized_type = EVENT_TYPE_MAP.get(event_type, event_type)
    inferred_entity_type = entity_type or ENTITY_TYPE_MAP.get(normalized_type)
    inferred_entity_id = entity_id or _infer_entity_id(normalized_type, payload)

    metadata: Dict[str, Any] = {
        "normalized_at": utc_now().isoformat(),
    }
    if normalized_type != event_type:
        metadata["normalized_from"] = event_type
    else:
        metadata["normalized"] = True

    return NormalizedEvent(
        event_type=normalized_type,
        entity_type=inferred_entity_type,
        entity_id=inferred_entity_id,
        source=source,
        payload=payload,
        metadata=metadata,
    )


def _infer_entity_id(event_type: str, payload: Dict[str, Any]) -> Optional[str]:
    if event_type in {"txn_fiat", "txn_crypto", "chargeback"}:
        return _first_present(payload, ["transaction_id", "tx_id", "id"])
    if event_type in {"withdrawal_request", "deposit_detected"}:
        return _first_present(payload, ["account_id", "wallet_id", "iban", "id"])
    if event_type == "login":
        return _first_present(payload, ["user_id", "account_id", "id"])
    if event_type == "sanctions_hit":
        return _first_present(payload, ["counterparty_id", "name", "entity_id"])
    if event_type == "kyc_update":
        return _first_present(payload, ["user_id", "entity_id", "id"])
    return _first_present(payload, ["entity_id", "id"])


def _first_present(payload: Dict[str, Any], keys: list[str]) -> Optional[str]:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return str(value)
    return None
