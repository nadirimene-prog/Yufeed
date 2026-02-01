import pytest

from src.services.event_normalizer import normalize_event, _first_present


@pytest.mark.unit
def test_normalize_event_mapping_and_metadata():
    event = normalize_event("transaction.fiat", payload={"transaction_id": "tx1"})
    assert event.event_type == "txn_fiat"
    assert event.entity_type == "transaction"
    assert event.entity_id == "tx1"
    assert event.metadata.get("normalized_from") == "transaction.fiat"

    event = normalize_event("custom.event", payload={"id": "abc"})
    assert event.event_type == "custom.event"
    assert event.metadata.get("normalized") is True


@pytest.mark.unit
def test_first_present():
    assert _first_present({"a": 1, "b": 2}, ["b", "a"]) == "2"
    assert _first_present({}, ["a"]) is None
