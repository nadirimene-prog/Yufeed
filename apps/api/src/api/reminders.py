"""
Deadline Reminder API

Endpoints for managing deadline reminders and subscriptions.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.services.reminder_service import ReminderService, ReminderConfig
from src.tasks.reminders import check_upcoming_deadlines, send_reminder

router = APIRouter(
    prefix="/api/reminders",
    tags=["reminders"],
    dependencies=[Depends(require_any_role(["admin", "compliance", "aml_officer", "user"]))],
)


@router.get("/upcoming")
def get_upcoming_deadlines(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to look ahead"),
    scope: Optional[List[str]] = Query(default=None, description="Filter by scope tags"),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Get all upcoming compliance deadlines with reminders.

    Returns obligations with approaching effective dates,
    including reminder status and linked policies.
    """
    service = ReminderService(db)
    deadlines = service.get_upcoming_deadlines(days_window=days, scope_filter=scope)

    return {
        "deadlines": [
            {
                "obligation_id": d.obligation_id,
                "obligation_text": d.obligation_text,
                "celex": d.celex,
                "document_title": d.doc_title,
                "deadline": d.deadline.isoformat() if d.deadline else None,
                "days_remaining": d.days_remaining,
                "reminder_type": d.reminder_type.value,
                "linked_policy": (
                    {"id": d.linked_policy_id, "title": d.linked_policy_title}
                    if d.linked_policy_id
                    else None
                ),
            }
            for d in deadlines
        ],
        "total": len(deadlines),
        "filters": {"days": days, "scope": scope},
    }


@router.post("/send-now/{obligation_id}")
def send_reminder_now(
    obligation_id: int,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Manually trigger a reminder for a specific obligation.

    Only admins and compliance officers can send manual reminders.
    """
    from src.models.compliance_workflow import RegulatoryObligation

    obligation = db.query(RegulatoryObligation).get(obligation_id)
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    # Queue reminder task
    task = send_reminder.delay(
        obligation_id=obligation_id, reminder_type="manual", days_remaining=0
    )

    return {
        "status": "queued",
        "message": f"Reminder queued for obligation {obligation_id}",
        "task_id": task.id,
    }


@router.post("/snooze/{obligation_id}")
def snooze_reminder(
    obligation_id: int,
    days: int = Query(default=3, ge=1, le=30, description="Number of days to snooze"),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Snooze reminders for an obligation.

    Delays all future reminders for the specified number of days.
    """
    service = ReminderService(db)

    from src.models.compliance_workflow import RegulatoryObligation

    obligation = db.query(RegulatoryObligation).get(obligation_id)
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    service.snooze_reminder(obligation_id, snooze_days=days)

    return {
        "status": "success",
        "message": f"Reminders snoozed for {days} days",
        "obligation_id": obligation_id,
        "snoozed_until": (
            datetime.now(timezone.utc) + __import__("datetime").timedelta(days=days)
        ).isoformat(),
    }


@router.get("/statistics")
def get_reminder_statistics(
    days: int = Query(default=30, ge=1, le=365, description="Statistics period in days"),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Get reminder system statistics.

    Returns metrics about reminders sent, opened, and failed.
    """
    service = ReminderService(db)
    stats = service.get_reminder_statistics(days=days)

    return {"period_days": days, "statistics": stats}


@router.get("/history/{obligation_id}")
def get_reminder_history(
    obligation_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Get reminder history for a specific obligation.
    """
    from sqlalchemy import text

    results = db.execute(
        text(
            """
            SELECT
                r.id,
                r.reminder_type,
                r.sent_at,
                r.channel,
                r.status,
                r.opened_at,
                u.email as user_email,
                u.full_name as user_name
            FROM reminder_logs r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.obligation_id = :obl_id
            ORDER BY r.sent_at DESC
            LIMIT :limit
        """
        ),
        {"obl_id": obligation_id, "limit": limit},
    ).fetchall()

    return {
        "obligation_id": obligation_id,
        "history": [
            {
                "id": row[0],
                "reminder_type": row[1],
                "sent_at": row[2].isoformat() if row[2] else None,
                "channel": row[3],
                "status": row[4],
                "opened_at": row[5].isoformat() if row[5] else None,
                "recipient": {"email": row[6], "name": row[7]},
            }
            for row in results
        ],
    }


# ============================================================================
# User Subscription Management
# ============================================================================


@router.get("/subscriptions")
def get_user_subscriptions(
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Get current user's deadline reminder subscriptions.
    """
    from sqlalchemy import text

    results = db.execute(
        text(
            """
            SELECT
                s.id,
                s.obligation_id,
                s.doc_id,
                s.reminder_days,
                s.email_enabled,
                s.slack_enabled,
                s.created_at,
                ro.obligation_text,
                ld.title as doc_title
            FROM user_deadline_subscriptions s
            LEFT JOIN regulatory_obligations ro ON s.obligation_id = ro.id
            LEFT JOIN legal_documents ld ON s.doc_id = ld.id
            WHERE s.user_id = :user_id
        """
        ),
        {"user_id": current_user.user_id},
    ).fetchall()

    return {
        "subscriptions": [
            {
                "id": row[0],
                "obligation_id": row[1],
                "document_id": row[2],
                "reminder_days": row[3],
                "email_enabled": bool(row[4]),
                "slack_enabled": bool(row[5]),
                "created_at": row[6].isoformat() if row[6] else None,
                "obligation_text": row[7][:100] + "..." if row[7] and len(row[7]) > 100 else row[7],
                "document_title": row[8],
            }
            for row in results
        ]
    }


@router.post("/subscriptions")
def create_subscription(
    obligation_id: Optional[int] = None,
    doc_id: Optional[int] = None,
    reminder_days: List[int] = Query(default=[30, 14, 7]),
    email_enabled: bool = True,
    slack_enabled: bool = False,
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Subscribe to deadline reminders for an obligation or document.
    """
    if not obligation_id and not doc_id:
        raise HTTPException(status_code=400, detail="Must provide obligation_id or doc_id")

    from sqlalchemy import text

    try:
        db.execute(
            text(
                """
                INSERT INTO user_deadline_subscriptions
                (user_id, obligation_id, doc_id, reminder_days, email_enabled, slack_enabled)
                VALUES (:user_id, :obl_id, :doc_id, :days, :email, :slack)
                ON CONFLICT DO NOTHING
            """
            ),
            {
                "user_id": current_user.user_id,
                "obl_id": obligation_id,
                "doc_id": doc_id,
                "days": reminder_days,
                "email": email_enabled,
                "slack": slack_enabled,
            },
        )
        db.commit()

        return {
            "status": "success",
            "message": "Subscription created",
            "subscription": {
                "user_id": current_user.user_id,
                "obligation_id": obligation_id,
                "document_id": doc_id,
                "reminder_days": reminder_days,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create subscription: {str(e)}")


@router.delete("/subscriptions/{subscription_id}")
def delete_subscription(
    subscription_id: int,
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Unsubscribe from deadline reminders.
    """
    from sqlalchemy import text

    result = db.execute(
        text(
            """
            DELETE FROM user_deadline_subscriptions
            WHERE id = :sub_id AND user_id = :user_id
        """
        ),
        {"sub_id": subscription_id, "user_id": current_user.user_id},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {"status": "success", "message": "Subscription deleted"}


# ============================================================================
# Admin Operations
# ============================================================================


@router.post("/admin/trigger-check", include_in_schema=False)
def admin_trigger_deadline_check(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_any_role(["admin"])),
    db: Session = Depends(get_db),
):
    """
    Admin endpoint to manually trigger deadline check.
    """
    task = check_upcoming_deadlines.delay()

    return {"status": "triggered", "message": "Deadline check task queued", "task_id": task.id}


@router.get("/admin/logs")
def admin_get_reminder_logs(
    limit: int = Query(default=100, ge=1, le=500),
    status: Optional[str] = Query(
        default=None, description="Filter by status: sent, failed, opened"
    ),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance"])),
    db: Session = Depends(get_db),
):
    """
    Admin endpoint to view all reminder logs.
    """
    from sqlalchemy import text

    query = """
        SELECT
            r.id,
            r.obligation_id,
            r.reminder_type,
            r.sent_at,
            r.channel,
            r.status,
            r.opened_at,
            u.email as user_email,
            ro.celex
        FROM reminder_logs r
        LEFT JOIN users u ON r.user_id = u.id
        LEFT JOIN regulatory_obligations ro ON r.obligation_id = ro.id
    """

    if status:
        query += " WHERE r.status = :status"

    query += " ORDER BY r.sent_at DESC LIMIT :limit"

    results = db.execute(
        text(query), {"status": status, "limit": limit} if status else {"limit": limit}
    ).fetchall()

    return {
        "logs": [
            {
                "id": row[0],
                "obligation_id": row[1],
                "reminder_type": row[2],
                "sent_at": row[3].isoformat() if row[3] else None,
                "channel": row[4],
                "status": row[5],
                "opened_at": row[6].isoformat() if row[6] else None,
                "recipient": row[7],
                "celex": row[8],
            }
            for row in results
        ],
        "total": len(results),
        "filters": {"status": status},
    }
