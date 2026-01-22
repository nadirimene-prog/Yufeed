import os
import httpx
from typing import Dict, Any

class KYCVendorPlugin:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("KYC_API_KEY", "")
        self.base_url = base_url or os.getenv("KYC_API_URL", "https://api.kycprovider.com/v1")
        self.client = httpx.AsyncClient()

    async def verify_user(self, user_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/users/{user_id}/verify"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = await self.client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return {"status": data.get("status", "unknown"), "flags": data.get("flags", []), "raw": data}
        except Exception as exc:
            return {"status": "error", "flags": [], "error": str(exc)}
