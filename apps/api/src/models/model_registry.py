from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class ModelRegistry(Base):
    """Top-level model registry entry."""

    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True)
    model_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    model_type = Column(String(100), nullable=False)  # rule-based | ml | hybrid
    owner = Column(String(255))
    status = Column(String(50), default="active")  # active | deprecated

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")


class ModelVersion(Base):
    """Model version entry with metrics and artifacts."""

    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("model_registry.id"), nullable=False, index=True)
    version = Column(String(100), nullable=False)
    status = Column(String(50), default="staging")  # staging | production | archived
    artifact_uri = Column(String(500))
    feature_set_hash = Column(String(128))
    training_window = Column(String(255))
    metrics = Column(JSON().with_variant(JSONB(), "postgresql"))
    created_at = Column(DateTime, default=utc_now)
    promoted_at = Column(DateTime)

    model = relationship("ModelRegistry", back_populates="versions")
    drift_reports = relationship(
        "ModelDriftReport", back_populates="version", cascade="all, delete-orphan"
    )


class ModelDriftReport(Base):
    """Drift monitoring snapshots for a model version."""

    __tablename__ = "model_drift_reports"

    id = Column(Integer, primary_key=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False, index=True)
    drift_score = Column(Numeric(6, 3))
    status = Column(String(50), default="ok")  # ok | warning | critical
    window_start = Column(DateTime)
    window_end = Column(DateTime)
    metrics = Column(JSON().with_variant(JSONB(), "postgresql"))
    observed_at = Column(DateTime, default=utc_now, index=True)

    version = relationship("ModelVersion", back_populates="drift_reports")
