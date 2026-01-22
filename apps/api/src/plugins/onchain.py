from typing import Dict, Any

from src.plugins import BaseRiskPlugin


class MockOnchainRiskPlugin(BaseRiskPlugin):
    """Mock on-chain risk provider (placeholder for TRM/Chainalysis)."""

    async def score_address(self, address: str) -> Dict[str, Any]:
        return {
            "address": address,
            "risk_score": 0.12,
            "risk_level": "low",
            "vendor": "mock-onchain",
            "signals": {
                "sanctions": False,
                "mixer_exposure": False,
                "darknet_exposure": False,
            },
        }


def get_default_onchain_plugin() -> BaseRiskPlugin:
    return MockOnchainRiskPlugin()
