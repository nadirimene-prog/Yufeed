"""Association tables shared across domains.

We keep association tables in a dedicated module to avoid circular imports
between domain model files.
"""

from sqlalchemy import Table, Column, Integer, ForeignKey, UniqueConstraint, Index

from src.database import Base


case_findings = Table(
    "case_findings",
    Base.metadata,
    Column("case_id", Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
    Column(
        "finding_id",
        Integer,
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("case_id", "finding_id", name="uq_case_findings_case_finding"),
    Index("ix_case_findings_case_id", "case_id"),
    Index("ix_case_findings_finding_id", "finding_id"),
)
