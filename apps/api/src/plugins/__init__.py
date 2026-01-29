from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseRiskPlugin(ABC):
    """Abstract base class for all risk plugins."""

    @abstractmethod
    async def score_address(self, address: str) -> Dict[str, Any]:
        """Score a blockchain address."""
        raise NotImplementedError


__all__ = ["BaseRiskPlugin"]
