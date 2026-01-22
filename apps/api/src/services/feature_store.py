"""
Feature Store Service
Provides online feature storage via Redis with Postgres fallback.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import redis
from sqlalchemy.orm import Session

from src.models.transaction_models import FeatureValue

logger = logging.getLogger(__name__)


class FeatureStoreService:
    def __init__(
        self,
        db: Session,
        redis_url: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        self.db = db
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl_seconds = ttl_seconds or int(os.getenv("FEATURE_STORE_TTL_SECONDS", "86400"))
        self.redis_client = self._init_redis()

    def _init_redis(self):
        try:
            client = redis.from_url(self.redis_url, decode_responses=True)
            client.ping()
            return client
        except redis.RedisError as e:
            logger.warning(f"Feature store Redis unavailable: {e}")
            return None

    def _feature_key(self, entity_type: str, entity_id: str, feature_name: str) -> str:
        return f"feature:{entity_type}:{entity_id}:{feature_name}"

    def _index_key(self, entity_type: str, entity_id: str) -> str:
        return f"feature_index:{entity_type}:{entity_id}"

    def upsert_feature(
        self,
        entity_type: str,
        entity_id: str,
        feature_name: str,
        feature_value: Any,
        feature_type: Optional[str] = None,
        calculated_at: Optional[datetime] = None,
        version: int = 1,
    ) -> FeatureValue:
        calculated_at = calculated_at or datetime.utcnow()

        record = (
            self.db.query(FeatureValue)
            .filter(
                FeatureValue.entity_type == entity_type,
                FeatureValue.entity_id == entity_id,
                FeatureValue.feature_name == feature_name,
            )
            .order_by(FeatureValue.calculated_at.desc(), FeatureValue.id.desc())
            .first()
        )
        if record:
            record.feature_value = feature_value
            record.feature_type = feature_type
            record.calculated_at = calculated_at
            record.version = version
        else:
            record = FeatureValue(
                entity_type=entity_type,
                entity_id=entity_id,
                feature_name=feature_name,
                feature_value=feature_value,
                feature_type=feature_type,
                calculated_at=calculated_at,
                version=version,
            )
            self.db.add(record)

        self._write_redis(
            entity_type,
            entity_id,
            feature_name,
            {
                "value": feature_value,
                "feature_type": feature_type,
                "calculated_at": calculated_at.isoformat(),
                "version": version,
            },
        )
        return record

    def upsert_features(
        self,
        entity_type: str,
        entity_id: str,
        features: Dict[str, Dict[str, Any]],
    ) -> Dict[str, FeatureValue]:
        records: Dict[str, FeatureValue] = {}
        for name, payload in features.items():
            records[name] = self.upsert_feature(
                entity_type=entity_type,
                entity_id=entity_id,
                feature_name=name,
                feature_value=payload.get("value"),
                feature_type=payload.get("feature_type"),
                calculated_at=payload.get("calculated_at"),
                version=payload.get("version", 1),
            )
        return records

    def get_feature(
        self,
        entity_type: str,
        entity_id: str,
        feature_name: str,
    ) -> Optional[Dict[str, Any]]:
        cached = self._read_redis(entity_type, entity_id, feature_name)
        if cached is not None:
            return cached

        record = (
            self.db.query(FeatureValue)
            .filter(
                FeatureValue.entity_type == entity_type,
                FeatureValue.entity_id == entity_id,
                FeatureValue.feature_name == feature_name,
            )
            .order_by(FeatureValue.calculated_at.desc(), FeatureValue.id.desc())
            .first()
        )
        if not record:
            return None

        payload = {
            "value": record.feature_value,
            "feature_type": record.feature_type,
            "calculated_at": record.calculated_at.isoformat(),
            "version": record.version,
        }
        self._write_redis(entity_type, entity_id, feature_name, payload)
        return payload

    def get_features(
        self,
        entity_type: str,
        entity_id: str,
        names: Optional[list[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        if names:
            results: Dict[str, Dict[str, Any]] = {}
            for name in names:
                feature = self.get_feature(entity_type, entity_id, name)
                if feature is not None:
                    results[name] = feature
            return results

        if self.redis_client:
            try:
                feature_names = list(
                    self.redis_client.smembers(self._index_key(entity_type, entity_id))
                )
                if feature_names:
                    return {
                        name: self._read_redis(entity_type, entity_id, name)
                        for name in feature_names
                        if self._read_redis(entity_type, entity_id, name) is not None
                    }
            except redis.RedisError as e:
                logger.warning(f"Feature index read failed: {e}")

        records = (
            self.db.query(FeatureValue)
            .filter(
                FeatureValue.entity_type == entity_type,
                FeatureValue.entity_id == entity_id,
            )
            .order_by(FeatureValue.calculated_at.desc(), FeatureValue.id.desc())
            .all()
        )
        results: Dict[str, Dict[str, Any]] = {}
        for record in records:
            if record.feature_name in results:
                continue
            results[record.feature_name] = {
                "value": record.feature_value,
                "feature_type": record.feature_type,
                "calculated_at": record.calculated_at.isoformat(),
                "version": record.version,
            }
        return results

    def delete_feature(self, entity_type: str, entity_id: str, feature_name: str) -> None:
        if self.redis_client:
            try:
                self.redis_client.delete(self._feature_key(entity_type, entity_id, feature_name))
                self.redis_client.srem(self._index_key(entity_type, entity_id), feature_name)
            except redis.RedisError as e:
                logger.warning(f"Feature delete failed: {e}")

    def _write_redis(self, entity_type: str, entity_id: str, feature_name: str, payload: Dict[str, Any]) -> None:
        if not self.redis_client:
            return
        try:
            key = self._feature_key(entity_type, entity_id, feature_name)
            self.redis_client.setex(key, self.ttl_seconds, json.dumps(payload))
            self.redis_client.sadd(self._index_key(entity_type, entity_id), feature_name)
        except redis.RedisError as e:
            logger.warning(f"Feature store write failed: {e}")

    def _read_redis(self, entity_type: str, entity_id: str, feature_name: str) -> Optional[Dict[str, Any]]:
        if not self.redis_client:
            return None
        try:
            raw = self.redis_client.get(self._feature_key(entity_type, entity_id, feature_name))
            if not raw:
                return None
            return json.loads(raw)
        except (json.JSONDecodeError, redis.RedisError) as e:
            logger.warning(f"Feature store read failed: {e}")
            return None
