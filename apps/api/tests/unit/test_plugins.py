import pytest

from src.plugins.kyc_vendor import KYCVendorPlugin
from src.plugins.trm import TRMPlugin


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kyc_vendor_plugin_success_and_error():
    plugin = KYCVendorPlugin(api_key="key", base_url="https://example.com")

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "verified", "flags": ["pep"]}

    async def fake_get(*args, **kwargs):
        return DummyResponse()

    plugin.client.get = fake_get
    result = await plugin.verify_user("user1")
    assert result["status"] == "verified"
    assert result["flags"] == ["pep"]

    async def fake_get_error(*args, **kwargs):
        raise RuntimeError("boom")

    plugin.client.get = fake_get_error
    result = await plugin.verify_user("user2")
    assert result["status"] == "error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trm_plugin_success_and_error():
    plugin = TRMPlugin(api_key="key", base_url="https://example.com")

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"risk_score": 77, "risk_categories": ["scam"]}

    async def fake_get(*args, **kwargs):
        return DummyResponse()

    plugin.client.get = fake_get
    result = await plugin.score_address("0xabc")
    assert result["score"] == 77
    assert result["vendor"] == "TRM"

    async def fake_get_error(*args, **kwargs):
        raise RuntimeError("boom")

    plugin.client.get = fake_get_error
    result = await plugin.score_address("0xdef")
    assert result["score"] == 0
    assert "error" in result
