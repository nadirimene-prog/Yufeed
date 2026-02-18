"""Compliance calendar scheduled tasks."""

from __future__ import annotations

import logging
from typing import Dict, List

from sqlalchemy import distinct

from src.database import SessionLocal
from src.models.compliance_calendar import ComplianceCalendarEvent
from src.models.tenant_models import Tenant
from src.services.compliance_calendar import ComplianceCalendarService
from src.worker import celery_app

logger = logging.getLogger(__name__)


def _active_tenant_ids(db) -> List[str]:
    tenant_ids = [
        tenant_id
        for (tenant_id,) in db.query(Tenant.tenant_id)
        .filter(Tenant.is_active.is_(True), Tenant.tenant_id.is_not(None))
        .all()
        if tenant_id
    ]
    if tenant_ids:
        return tenant_ids

    return [
        tenant_id
        for (tenant_id,) in db.query(distinct(ComplianceCalendarEvent.tenant_id))
        .filter(ComplianceCalendarEvent.tenant_id.is_not(None))
        .all()
        if tenant_id
    ]


@celery_app.task(name="tasks.task_check_overdue_events")
def task_check_overdue_events() -> Dict[str, int]:
    db = SessionLocal()
    try:
        service = ComplianceCalendarService(db)
        tenant_ids = _active_tenant_ids(db)
        updated = 0
        for tenant_id in tenant_ids:
            updated += service.check_overdue_events(tenant_id=tenant_id)
        db.commit()
        return {"tenants_scanned": len(tenant_ids), "events_marked_overdue": updated}
    except Exception:
        db.rollback()
        logger.exception("task_check_overdue_events failed")
        raise
    finally:
        db.close()


@celery_app.task(name="tasks.task_send_calendar_reminders")
def task_send_calendar_reminders() -> Dict[str, int]:
    db = SessionLocal()
    try:
        service = ComplianceCalendarService(db)
        tenant_ids = _active_tenant_ids(db)
        reminders_sent = 0
        events_considered = 0

        for tenant_id in tenant_ids:
            events = service.get_events_requiring_reminders(tenant_id=tenant_id)
            events_considered += len(events)
            for event in events:
                service.mark_event_reminded(event)
                reminders_sent += 1

        db.commit()
        return {
            "tenants_scanned": len(tenant_ids),
            "events_considered": events_considered,
            "reminders_marked": reminders_sent,
        }
    except Exception:
        db.rollback()
        logger.exception("task_send_calendar_reminders failed")
        raise
    finally:
        db.close()
