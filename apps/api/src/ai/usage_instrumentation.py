"""
Shared AI usage instrumentation helpers.

These helpers centralize provider usage extraction and persist telemetry using an
isolated DB session so business transactions are not committed/rolled back by
usage logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, Iterable, Mapping, Optional

from src.ai.cost_tracker import log_usage
from src.database import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class UsageLogContext:
    tenant_id: Optional[str]
    operation: Optional[str] = None
    user_id: Optional[str] = None
    document_id: Optional[int] = None
    obligation_id: Optional[int] = None
    request_metadata: Dict[str, Any] = field(default_factory=dict)
    response_metadata: Dict[str, Any] = field(default_factory=dict)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _persist_usage(
    *,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    context: UsageLogContext,
) -> bool:
    tenant_id = (context.tenant_id or "").strip()
    if not tenant_id:
        return False

    if prompt_tokens <= 0 and completion_tokens <= 0:
        return False

    db = SessionLocal()
    try:
        log_usage(
            db=db,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tenant_id=tenant_id,
            operation=context.operation,
            document_id=context.document_id,
            obligation_id=context.obligation_id,
            user_id=context.user_id,
            request_metadata=context.request_metadata or None,
            response_metadata=context.response_metadata or None,
        )
        return True
    except Exception as exc:
        logger.warning("AI usage persistence failed: %s", exc)
        return False
    finally:
        try:
            db.close()
        except Exception:
            pass


def log_anthropic_response_usage(response: Any, *, context: UsageLogContext) -> bool:
    """Extract Anthropic SDK token usage and persist a usage row."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return False

    prompt_tokens = _safe_int(getattr(usage, "input_tokens", 0))
    completion_tokens = _safe_int(getattr(usage, "output_tokens", 0))
    # Anthropic may surface cache token buckets separately.
    prompt_tokens += _safe_int(getattr(usage, "cache_creation_input_tokens", 0))
    prompt_tokens += _safe_int(getattr(usage, "cache_read_input_tokens", 0))

    response_meta = dict(context.response_metadata or {})
    response_meta.setdefault("response_id", str(getattr(response, "id", "") or ""))
    response_meta.setdefault("stop_reason", str(getattr(response, "stop_reason", "") or ""))

    return _persist_usage(
        provider="anthropic",
        model=str(getattr(response, "model", None) or "unknown"),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        context=UsageLogContext(
            tenant_id=context.tenant_id,
            operation=context.operation,
            user_id=context.user_id,
            document_id=context.document_id,
            obligation_id=context.obligation_id,
            request_metadata=dict(context.request_metadata or {}),
            response_metadata=response_meta,
        ),
    )


def log_openai_response_usage(
    response_json: Mapping[str, Any], *, context: UsageLogContext, model: Optional[str] = None
) -> bool:
    """Extract OpenAI-compatible usage payload and persist a usage row."""
    usage = response_json.get("usage")
    if not isinstance(usage, Mapping):
        return False

    prompt_tokens = _safe_int(usage.get("prompt_tokens"))
    completion_tokens = _safe_int(usage.get("completion_tokens"))

    response_meta = dict(context.response_metadata or {})
    if "id" in response_json:
        response_meta.setdefault("response_id", str(response_json.get("id") or ""))
    if "object" in response_json:
        response_meta.setdefault("object", str(response_json.get("object") or ""))
    if "system_fingerprint" in response_json:
        response_meta.setdefault(
            "system_fingerprint", str(response_json.get("system_fingerprint") or "")
        )

    resolved_model = str(model or response_json.get("model") or "unknown")
    return _persist_usage(
        provider="openai",
        model=resolved_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        context=UsageLogContext(
            tenant_id=context.tenant_id,
            operation=context.operation,
            user_id=context.user_id,
            document_id=context.document_id,
            obligation_id=context.obligation_id,
            request_metadata=dict(context.request_metadata or {}),
            response_metadata=response_meta,
        ),
    )


def log_usage_event(event: Mapping[str, Any], *, default_context: UsageLogContext) -> bool:
    """Persist a normalized usage event dict (used by analyzer aggregation)."""
    provider = str(event.get("provider") or "").strip().lower()
    model = str(event.get("model") or "unknown")
    if provider not in {"anthropic", "openai", "azure"}:
        return False

    ctx = UsageLogContext(
        tenant_id=str(event.get("tenant_id") or default_context.tenant_id or "").strip() or None,
        operation=str(event.get("operation") or default_context.operation or "") or None,
        user_id=str(event.get("user_id") or default_context.user_id or "") or None,
        document_id=(
            _safe_int(event.get("document_id"))
            if event.get("document_id") is not None
            else default_context.document_id
        ),
        obligation_id=(
            _safe_int(event.get("obligation_id"))
            if event.get("obligation_id") is not None
            else default_context.obligation_id
        ),
        request_metadata={
            **dict(default_context.request_metadata or {}),
            **(
                dict(event.get("request_metadata") or {})
                if isinstance(event.get("request_metadata"), Mapping)
                else {}
            ),
        },
        response_metadata={
            **dict(default_context.response_metadata or {}),
            **(
                dict(event.get("response_metadata") or {})
                if isinstance(event.get("response_metadata"), Mapping)
                else {}
            ),
        },
    )

    return _persist_usage(
        provider=provider,
        model=model,
        prompt_tokens=_safe_int(event.get("prompt_tokens")),
        completion_tokens=_safe_int(event.get("completion_tokens")),
        context=ctx,
    )


def log_usage_events(
    events: Iterable[Mapping[str, Any]], *, default_context: UsageLogContext
) -> int:
    """Persist a collection of normalized usage events and return count persisted."""
    persisted = 0
    for event in events:
        try:
            if log_usage_event(event, default_context=default_context):
                persisted += 1
        except Exception as exc:
            logger.warning("Skipping malformed usage event: %s", exc)
    return persisted
