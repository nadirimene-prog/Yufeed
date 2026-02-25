import pytest

from src.api.ai_agents import BatchTriageRequest


@pytest.mark.unit
def test_batch_triage_request_accepts_selected_alert_ids():
    payload = BatchTriageRequest(alert_ids=[1, 2, 3], limit=25)
    assert payload.alert_ids == [1, 2, 3]
    assert payload.limit == 25


@pytest.mark.unit
def test_batch_triage_request_defaults_to_pending_limit_mode():
    payload = BatchTriageRequest()
    assert payload.alert_ids is None
    assert payload.limit == 50
