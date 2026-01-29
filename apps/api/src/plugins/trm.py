import os
import httpx
from typing import Dict, Any
from . import BaseRiskPlugin

class TRMPlugin(BaseRiskPlugin):
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.getenv("TRM_API_KEY", "")
        self.base_url = base_url or os.getenv("TRM_API_URL", "https://api.trmlabs.com/v1")
        self.client = httpx.AsyncClient()

    async def score_address(self, address: str) -> Dict[str, Any]:
        url = f"{self.base_url}/address/{address}/score"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = await self.client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            risk_score = data.get("risk_score", 0)
            categories = data.get("risk_categories", [])
            return {"score": risk_score, "categories": categories, "vendor": "TRM", "address": address, "raw": data}
        except Exception as exc:
            return {"score": 0, "categories": [], "vendor": "TRM", "address": address, "error": str(exc)}
