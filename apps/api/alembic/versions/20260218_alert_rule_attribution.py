"""persist alert rule attribution and backfill historical alerts

Revision ID: 20260218_alert_rule_attribution
Revises: 20260218_compliance_calendar
Create Date: 2026-02-18 22:10:00.000000
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260218_alert_rule_attribution"
down_revision = "20260218_compliance_calendar"
branch_labels = None
depends_on = None


def _safe_parse_json(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "alerts" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("alerts")}

    if "rule_id" not in columns:
        op.add_column("alerts", sa.Column("rule_id", sa.String(length=255), nullable=True))

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("alerts")}
    desired_index = op.f("ix_alerts_rule_id")
    if desired_index not in indexes:
        op.create_index(desired_index, "alerts", ["rule_id"], unique=False)

    rows = bind.execute(
        sa.text(
            "SELECT id, rule_id, matched_rules_data FROM alerts "
            "WHERE rule_id IS NULL AND matched_rules_data IS NOT NULL"
        )
    ).mappings()

    for row in rows:
        matched = _safe_parse_json(row.get("matched_rules_data"))
        if not matched:
            continue

        rule_id = next(iter(matched.keys()), None)
        if not isinstance(rule_id, str) or not rule_id:
            continue

        bind.execute(
            sa.text("UPDATE alerts SET rule_id = :rule_id WHERE id = :id"),
            {"rule_id": rule_id, "id": row["id"]},
        )


def downgrade():
    # Intentionally no-op: this migration backfills persisted attribution and may
    # operate on databases where rule_id already existed from earlier revisions.
    pass
