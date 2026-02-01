import pytest
from datetime import datetime, timezone, timedelta

from src.common import datetime_utils
from src.common.enums import ComplianceStatus, RiskLevel, AlertStatus, CaseStatus


@pytest.mark.unit
def test_datetime_utils_helpers():
    now = datetime_utils.utc_now()
    assert now.tzinfo is not None

    naive = datetime(2024, 1, 1, 12, 0, 0)
    aware = datetime_utils.ensure_utc(naive)
    assert aware.tzinfo == timezone.utc
    assert aware.year == 2024

    offset = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    converted = datetime_utils.ensure_utc(offset)
    assert converted.tzinfo == timezone.utc

    iso = datetime_utils.format_iso(naive)
    assert iso.endswith("+00:00")


@pytest.mark.unit
def test_common_enums_values():
    assert ComplianceStatus.PENDING.value == "pending"
    assert RiskLevel.HIGH.value == "high"
    assert AlertStatus.FALSE_POSITIVE.value == "false_positive"
    assert CaseStatus.UNDER_REVIEW.value == "under_review"
