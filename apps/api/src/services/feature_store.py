"""Feature store implementation.

This module intentionally contains two APIs:
- `FeatureStore` (async): legacy compute path used by existing unit tests and
  downstream async pipelines.
- `FeatureStoreService` (sync): DB-backed feature persistence service used by
  REST endpoints and Celery tasks.
"""

import json
import os
import inspect
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as redis_async
from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.cache.cache_manager import CacheManager
from src.config import settings
from src.models.transaction_models import FeatureValue, Transaction, UserRiskProfile
from src.tenancy.context import get_current_tenant


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


REDIS_URL = settings.REDIS_URL
if not REDIS_URL:
    from unittest.mock import AsyncMock

    redis = AsyncMock()
    redis.get.return_value = None
else:
    redis = redis_async.from_url(REDIS_URL, **settings.redis_connection_kwargs)

CACHE_TTL = int(os.getenv("FEATURE_CACHE_TTL", "60"))


class FeatureStore:
    """
    Compute or fetch pre‑aggregated behavioural features for a user/event.
    The public method is async and returns a plain dict that can be merged
    into any downstream risk‑scoring pipeline.

    NOTE: This is intentionally kept stable for existing tests.
    """

    @staticmethod
    async def compute_features(
        user_id: str,
        event_type: str,
        payload: Dict[str, Any],
        db,  # async Session from get_async_db()
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        import time
        from src.monitoring.metrics import (
            feature_extraction_duration_seconds,
            feature_cache_hits_total,
            feature_cache_misses_total,
        )

        start_time = time.time()

        resolved_tenant_id = (
            tenant_id
            or (payload.get("tenant_id") if isinstance(payload, dict) else None)
            or get_current_tenant()
            or "default"
        )
        cache_key = f"feat:{resolved_tenant_id}:{user_id}:{event_type}"
        cached = await redis.get(cache_key)
        if cached:
            feature_cache_hits_total.inc()
            duration = time.time() - start_time
            feature_extraction_duration_seconds.labels(feature_type="user").observe(duration)
            return json.loads(cached)

        feature_cache_misses_total.inc()

        # Default result shape (safe for downstream consumers).
        result: Dict[str, Any] = {
            "velocity_1h_count": 0,
            "velocity_1h_total": 0.0,
            "velocity_24h_count": 0,
            "velocity_24h_total": 0.0,
            "unique_countries_7d": 0,
            "unique_counterparties_30d": 0,
            "max_amount_30d": 0.0,
            "account_age_days": 0,
            "kyc_status": "unknown",
            "risk_level": "low",
        }

        if db is not None:
            now = utc_now()
            one_hour_ago = now - timedelta(hours=1)
            twenty_four_hours_ago = now - timedelta(hours=24)
            seven_days_ago = now - timedelta(days=7)
            thirty_days_ago = now - timedelta(days=30)

            async def _exec(stmt):
                executed = db.execute(stmt)
                if inspect.isawaitable(executed):
                    return await executed
                return executed

            # Velocity windows (COUNT + SUM).
            stmt_1h = select(
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.amount), 0),
            ).where(
                Transaction.tenant_id == resolved_tenant_id,
                Transaction.user_id == user_id,
                Transaction.timestamp >= one_hour_ago,
            )
            count_1h, total_1h = (await _exec(stmt_1h)).one()
            result["velocity_1h_count"] = int(count_1h or 0)
            result["velocity_1h_total"] = float(total_1h or 0)

            stmt_24h = select(
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.amount), 0),
            ).where(
                Transaction.tenant_id == resolved_tenant_id,
                Transaction.user_id == user_id,
                Transaction.timestamp >= twenty_four_hours_ago,
            )
            count_24h, total_24h = (await _exec(stmt_24h)).one()
            result["velocity_24h_count"] = int(count_24h or 0)
            result["velocity_24h_total"] = float(total_24h or 0)

            # Distinct counts.
            stmt_countries = select(func.count(func.distinct(Transaction.country_code))).where(
                Transaction.tenant_id == resolved_tenant_id,
                Transaction.user_id == user_id,
                Transaction.timestamp >= seven_days_ago,
                Transaction.country_code.is_not(None),
            )
            countries = (await _exec(stmt_countries)).scalar_one_or_none()
            result["unique_countries_7d"] = int(countries or 0)

            stmt_counterparties = select(
                func.count(func.distinct(Transaction.counterparty_id))
            ).where(
                Transaction.tenant_id == resolved_tenant_id,
                Transaction.user_id == user_id,
                Transaction.timestamp >= thirty_days_ago,
                Transaction.counterparty_id.is_not(None),
            )
            counterparties = (await _exec(stmt_counterparties)).scalar_one_or_none()
            result["unique_counterparties_30d"] = int(counterparties or 0)

            stmt_max = select(func.max(Transaction.amount)).where(
                Transaction.tenant_id == resolved_tenant_id,
                Transaction.user_id == user_id,
                Transaction.timestamp >= thirty_days_ago,
            )
            max_amount = (await _exec(stmt_max)).scalar_one_or_none()
            result["max_amount_30d"] = float(max_amount or 0)

            # Risk profile-derived features.
            stmt_profile = (
                select(
                    UserRiskProfile.kyc_status,
                    UserRiskProfile.risk_level,
                    UserRiskProfile.account_created_at,
                )
                .where(
                    UserRiskProfile.tenant_id == resolved_tenant_id,
                    UserRiskProfile.user_id == user_id,
                )
                .limit(1)
            )
            profile_row = (await _exec(stmt_profile)).first()
            if profile_row:
                kyc_status, risk_level, account_created_at = profile_row
                if kyc_status:
                    result["kyc_status"] = kyc_status
                if risk_level:
                    result["risk_level"] = risk_level
                if account_created_at:
                    now_for_math = now
                    if (
                        getattr(account_created_at, "tzinfo", None) is None
                        and now_for_math.tzinfo is not None
                    ):
                        now_for_math = now_for_math.replace(tzinfo=None)
                    try:
                        result["account_age_days"] = max(
                            0, int((now_for_math - account_created_at).days)
                        )
                    except Exception:
                        result["account_age_days"] = 0

        await redis.set(cache_key, json.dumps(result), ex=CACHE_TTL)

        # Record feature extraction duration
        duration = time.time() - start_time
        feature_extraction_duration_seconds.labels(feature_type="user").observe(duration)

        return result


class FeatureStoreService:
    """Synchronous, DB-backed feature store persistence service."""

    _CACHE_NAMESPACE = "features"
    _CACHE_TYPE = "features"

    def __init__(self, db: Session):
        self.db = db
        self.cache = CacheManager()
        self.cache_ttl_seconds = int(os.getenv("FEATURE_CACHE_TTL", "60"))

    def _resolve_tenant_id(self, tenant_id: Optional[str]) -> str:
        resolved = tenant_id or get_current_tenant()
        if not resolved:
            raise HTTPException(status_code=403, detail="Tenant context required")
        return resolved

    def _cache_key(self, tenant_id: str, entity_type: str, entity_id: str, version: int) -> str:
        return f"{tenant_id}:{entity_type}:{entity_id}:v{version}"

    def upsert_features(
        self,
        entity_type: str,
        entity_id: str,
        features: Dict[str, Dict[str, Any]],
        *,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, FeatureValue]:
        tenant_id = self._resolve_tenant_id(tenant_id)
        if not entity_type or not entity_id:
            raise HTTPException(status_code=400, detail="entity_type and entity_id are required")

        if not features:
            return {}

        normalized: Dict[str, Tuple[Any, Optional[str], datetime, int]] = {}
        versions: set[int] = set()

        for feature_name, payload in features.items():
            if not feature_name:
                continue
            if payload is None:
                continue

            value = payload.get("value")
            feature_type = payload.get("feature_type")

            calculated_at = payload.get("calculated_at") or utc_now()
            if isinstance(calculated_at, str):
                calculated_at_str = calculated_at
                if calculated_at_str.endswith("Z"):
                    calculated_at_str = calculated_at_str[:-1] + "+00:00"
                calculated_at = datetime.fromisoformat(calculated_at_str)

            version = payload.get("version", 1) or 1
            try:
                version = int(version)
            except Exception:
                version = 1

            normalized[feature_name] = (value, feature_type, calculated_at, version)
            versions.add(version)

        if not normalized:
            return {}

        existing_rows = (
            self.db.query(FeatureValue)
            .filter(
                and_(
                    FeatureValue.tenant_id == tenant_id,
                    FeatureValue.entity_type == entity_type,
                    FeatureValue.entity_id == entity_id,
                    FeatureValue.feature_name.in_(list(normalized.keys())),
                    FeatureValue.version.in_(list(versions)),
                )
            )
            .all()
        )
        existing_by_key: Dict[Tuple[str, int], FeatureValue] = {
            (row.feature_name, row.version): row for row in existing_rows
        }

        out: Dict[str, FeatureValue] = {}
        touched_versions: set[int] = set()

        for feature_name, (value, feature_type, calculated_at, version) in normalized.items():
            touched_versions.add(version)
            row = existing_by_key.get((feature_name, version))
            if row:
                row.feature_value = value
                row.feature_type = feature_type
                row.calculated_at = calculated_at
            else:
                row = FeatureValue(
                    tenant_id=tenant_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    feature_name=feature_name,
                    feature_value=value,
                    feature_type=feature_type,
                    calculated_at=calculated_at,
                    version=version,
                )
                self.db.add(row)
            out[feature_name] = row

        # Invalidate cached feature sets for touched versions (cache-aside).
        for version in touched_versions:
            self.cache.delete(
                self._CACHE_NAMESPACE, self._cache_key(tenant_id, entity_type, entity_id, version)
            )

        return out

    def get_features(
        self,
        entity_type: str,
        entity_id: str,
        names: Optional[List[str]] = None,
        *,
        tenant_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Dict[str, Dict[str, Any]]:
        tenant_id = self._resolve_tenant_id(tenant_id)
        version = int(version or 1)
        if not entity_type or not entity_id:
            raise HTTPException(status_code=400, detail="entity_type and entity_id are required")

        cache_key = self._cache_key(tenant_id, entity_type, entity_id, version)
        cached = self.cache.get(self._CACHE_NAMESPACE, cache_key, cache_type=self._CACHE_TYPE)
        if isinstance(cached, dict):
            if names:
                name_set = {n for n in names if n}
                return {k: v for k, v in cached.items() if k in name_set}
            return cached

        query = self.db.query(FeatureValue).filter(
            and_(
                FeatureValue.tenant_id == tenant_id,
                FeatureValue.entity_type == entity_type,
                FeatureValue.entity_id == entity_id,
                FeatureValue.version == version,
            )
        )
        if names:
            query = query.filter(FeatureValue.feature_name.in_([n for n in names if n]))

        rows = query.all()
        result = {
            row.feature_name: {
                "value": row.feature_value,
                "feature_type": row.feature_type,
                "calculated_at": row.calculated_at.isoformat() if row.calculated_at else None,
                "version": row.version,
            }
            for row in rows
        }

        if not names:
            self.cache.set(
                self._CACHE_NAMESPACE,
                cache_key,
                result,
                ttl=self.cache_ttl_seconds,
                cache_type=self._CACHE_TYPE,
            )

        return result

    def get_feature(
        self,
        entity_type: str,
        entity_id: str,
        feature_name: str,
        *,
        tenant_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        if not feature_name:
            return None
        features = self.get_features(
            entity_type,
            entity_id,
            names=[feature_name],
            tenant_id=tenant_id,
            version=version,
        )
        return features.get(feature_name)

    def delete_feature(
        self,
        entity_type: str,
        entity_id: str,
        feature_name: str,
        *,
        tenant_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> None:
        tenant_id = self._resolve_tenant_id(tenant_id)
        if not entity_type or not entity_id or not feature_name:
            raise HTTPException(
                status_code=400, detail="entity_type, entity_id, and feature_name are required"
            )

        query = self.db.query(FeatureValue).filter(
            and_(
                FeatureValue.tenant_id == tenant_id,
                FeatureValue.entity_type == entity_type,
                FeatureValue.entity_id == entity_id,
                FeatureValue.feature_name == feature_name,
            )
        )
        if version is not None:
            query = query.filter(FeatureValue.version == int(version))

        query.delete(synchronize_session=False)

        if version is not None:
            self.cache.delete(
                self._CACHE_NAMESPACE,
                self._cache_key(tenant_id, entity_type, entity_id, int(version)),
            )
        else:
            # Drop all versions for this entity (if supported by Redis).
            self.cache.delete_pattern(
                self._CACHE_NAMESPACE,
                f"{tenant_id}:{entity_type}:{entity_id}:v*",
            )
