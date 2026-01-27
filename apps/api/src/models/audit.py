# apps/api/src/models/audit.py
from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(String(255), unique=True, nullable=False)
    actor_id = Column(String(255), nullable=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(50), nullable=True)
    actor_type = Column(String(50), nullable=True)
    actor_ip = Column(String(45), nullable=True)
    user_agent = Column(String, nullable=True)

    action = Column(String(50), nullable=False)
    method = Column(String(10), nullable=False)
    path = Column(String(512), nullable=False)

    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(255), nullable=True)
    status_code = Column(Integer, nullable=True)
    request_id = Column(String(255), nullable=True)

    changes = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
