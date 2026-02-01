import pytest

from src.api import travel_rule as travel_api
from src.auth.dependencies import CurrentUser


@pytest.mark.unit
def test_travel_rule_requests(db_session):
    user = CurrentUser("user-1", "user@example.com", "admin")

    request = travel_api.TravelRuleRequest(
        transaction_id="txn_travel_1",
        amount=1000.5,
        currency="USD",
        originator=travel_api.Party(name="Alice", account_id="acc-1"),
        beneficiary=travel_api.Party(name="Bob", wallet_address="0xabc"),
        message="Test",
    )

    created = travel_api.create_travel_rule_request(request, db_session, user)
    assert created.request_id.startswith("TR-")

    listed = travel_api.list_travel_rule_requests(status=None, db=db_session, _=user)
    assert listed

    fetched = travel_api.get_travel_rule_request(created.request_id, db_session, user)
    assert fetched.request_id == created.request_id

    submitted = travel_api.submit_travel_rule_request(created.request_id, db_session, user)
    assert submitted.status == "submitted"
