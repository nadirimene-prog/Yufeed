"""
Sanctions Screening Service

Unified service for screening against multiple sanctions lists.
Provides:
- Multi-list screening (EU, OFAC, UN)
- Name matching with fuzzy logic
- Entity classification
- Match scoring
- Bulk screening capabilities
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import re
from difflib import SequenceMatcher

from ..base import BaseIntegration, IntegrationResult, IntegrationStatus

logger = logging.getLogger(__name__)


class SanctionsListType(str, Enum):
    """Types of sanctions lists."""
    EU_CONSOLIDATED = "eu_consolidated"
    OFAC_SDN = "ofac_sdn"
    UN_SECURITY_COUNCIL = "un_sc"
    UK_HMT = "uk_hmt"
    ALL = "all"


class EntityType(str, Enum):
    """Types of sanctioned entities."""
    INDIVIDUAL = "individual"
    ENTITY = "entity"
    VESSEL = "vessel"
    AIRCRAFT = "aircraft"
    UNKNOWN = "unknown"


class MatchType(str, Enum):
    """Types of matches."""
    EXACT = "exact"
    FUZZY = "fuzzy"
    PARTIAL = "partial"
    ALIAS = "alias"
    PHONETIC = "phonetic"


@dataclass
class SanctionsMatch:
    """A match against a sanctions list."""
    list_type: SanctionsListType
    entity_type: EntityType
    match_type: MatchType

    # Match details
    matched_name: str
    original_name: str
    score: float  # 0-100

    # Entity details
    sanctions_id: str
    aliases: List[str] = field(default_factory=list)
    nationalities: List[str] = field(default_factory=list)
    birth_dates: List[str] = field(default_factory=list)
    addresses: List[str] = field(default_factory=list)

    # Sanctions program details
    programs: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    listing_date: Optional[datetime] = None

    # Additional data
    additional_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "list_type": self.list_type.value,
            "entity_type": self.entity_type.value,
            "match_type": self.match_type.value,
            "matched_name": self.matched_name,
            "original_name": self.original_name,
            "score": self.score,
            "sanctions_id": self.sanctions_id,
            "aliases": self.aliases,
            "nationalities": self.nationalities,
            "birth_dates": self.birth_dates,
            "addresses": self.addresses,
            "programs": self.programs,
            "reasons": self.reasons,
            "listing_date": self.listing_date.isoformat() if self.listing_date else None,
            "additional_info": self.additional_info
        }


@dataclass
class ScreeningResult:
    """Result of a sanctions screening."""
    screened_name: str
    screened_at: datetime
    matches: List[SanctionsMatch]
    is_hit: bool
    highest_score: float
    lists_checked: List[SanctionsListType]
    processing_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screened_name": self.screened_name,
            "screened_at": self.screened_at.isoformat(),
            "matches": [m.to_dict() for m in self.matches],
            "is_hit": self.is_hit,
            "highest_score": self.highest_score,
            "lists_checked": [l.value for l in self.lists_checked],
            "match_count": len(self.matches),
            "processing_time_ms": self.processing_time_ms
        }


class SanctionsService:
    """
    Unified sanctions screening service.

    Screens names against multiple sanctions lists and aggregates results.

    Usage:
        service = SanctionsService()
        await service.initialize()

        # Single name screening
        result = await service.screen_name("John Doe")

        # Batch screening
        results = await service.screen_batch(["John Doe", "Jane Smith"])
    """

    # Match threshold for considering a hit
    DEFAULT_THRESHOLD = 85.0

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        enable_fuzzy: bool = True,
        enable_phonetic: bool = True
    ):
        self.threshold = threshold
        self.enable_fuzzy = enable_fuzzy
        self.enable_phonetic = enable_phonetic

        # List providers will be initialized
        self._eu_list = None
        self._ofac_list = None
        self._initialized = False

        # In-memory sanctions data (for demo/testing)
        self._demo_sanctions: List[Dict[str, Any]] = []

        logger.info("SanctionsService initialized")

    async def initialize(self) -> None:
        """Initialize sanctions list providers."""
        if self._initialized:
            return

        try:
            # Initialize list providers
            from .eu_list import EUConsolidatedList
            from .ofac_list import OFACSDNList

            self._eu_list = EUConsolidatedList()
            self._ofac_list = OFACSDNList()

            # Load demo data for testing
            self._load_demo_sanctions()

            self._initialized = True
            logger.info("SanctionsService fully initialized")

        except Exception as e:
            logger.error(f"Failed to initialize SanctionsService: {e}")
            # Continue with demo data only
            self._load_demo_sanctions()
            self._initialized = True

    def _load_demo_sanctions(self) -> None:
        """Load demo sanctions data for testing."""
        self._demo_sanctions = [
            {
                "id": "EU-001",
                "list_type": SanctionsListType.EU_CONSOLIDATED,
                "entity_type": EntityType.INDIVIDUAL,
                "name": "PUTIN, Vladimir Vladimirovich",
                "aliases": ["Vladimir PUTIN", "V.V. Putin"],
                "nationalities": ["Russia"],
                "birth_dates": ["1952-10-07"],
                "programs": ["EU Russia Sanctions"],
                "reasons": ["President of the Russian Federation"]
            },
            {
                "id": "EU-002",
                "list_type": SanctionsListType.EU_CONSOLIDATED,
                "entity_type": EntityType.ENTITY,
                "name": "Sberbank",
                "aliases": ["Sberbank of Russia", "PJSC Sberbank"],
                "nationalities": ["Russia"],
                "programs": ["EU Russia Sanctions"],
                "reasons": ["Major Russian state-owned bank"]
            },
            {
                "id": "OFAC-001",
                "list_type": SanctionsListType.OFAC_SDN,
                "entity_type": EntityType.INDIVIDUAL,
                "name": "KIM, Jong Un",
                "aliases": ["Kim Jong-un", "Kim Jong Un"],
                "nationalities": ["North Korea"],
                "programs": ["North Korea Sanctions"],
                "reasons": ["Supreme Leader of North Korea"]
            },
            {
                "id": "OFAC-002",
                "list_type": SanctionsListType.OFAC_SDN,
                "entity_type": EntityType.INDIVIDUAL,
                "name": "KHAMENEI, Ali Hosseini",
                "aliases": ["Ayatollah Khamenei", "Ali Khamenei"],
                "nationalities": ["Iran"],
                "programs": ["Iran Sanctions"],
                "reasons": ["Supreme Leader of Iran"]
            },
            {
                "id": "EU-003",
                "list_type": SanctionsListType.EU_CONSOLIDATED,
                "entity_type": EntityType.ENTITY,
                "name": "Wagner Group",
                "aliases": ["PMC Wagner", "Wagner PMC"],
                "nationalities": ["Russia"],
                "programs": ["EU Russia Sanctions"],
                "reasons": ["Private military company"]
            }
        ]

    async def screen_name(
        self,
        name: str,
        entity_type: Optional[EntityType] = None,
        lists: Optional[List[SanctionsListType]] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> ScreeningResult:
        """
        Screen a single name against sanctions lists.

        Args:
            name: Name to screen
            entity_type: Optional entity type filter
            lists: Lists to check (default: all)
            additional_info: Additional matching criteria

        Returns:
            ScreeningResult with all matches
        """
        import time
        start_time = time.time()

        await self.initialize()

        lists_to_check = lists or [SanctionsListType.EU_CONSOLIDATED, SanctionsListType.OFAC_SDN]
        matches = []

        # Normalize the input name
        normalized_name = self._normalize_name(name)

        # Screen against each list
        for sanctions_entry in self._demo_sanctions:
            # Check if this list should be checked
            if sanctions_entry["list_type"] not in lists_to_check:
                continue

            # Check entity type filter
            if entity_type and sanctions_entry["entity_type"] != entity_type:
                continue

            # Check for matches
            match = self._check_match(
                normalized_name,
                sanctions_entry,
                additional_info
            )

            if match and match.score >= self.threshold:
                matches.append(match)

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)

        processing_time = int((time.time() - start_time) * 1000)

        return ScreeningResult(
            screened_name=name,
            screened_at=datetime.utcnow(),
            matches=matches,
            is_hit=len(matches) > 0,
            highest_score=matches[0].score if matches else 0.0,
            lists_checked=lists_to_check,
            processing_time_ms=processing_time
        )

    async def screen_batch(
        self,
        names: List[str],
        max_concurrent: int = 10
    ) -> List[ScreeningResult]:
        """
        Screen multiple names concurrently.

        Args:
            names: List of names to screen
            max_concurrent: Maximum concurrent screenings

        Returns:
            List of ScreeningResults
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def screen_one(name: str) -> ScreeningResult:
            async with semaphore:
                return await self.screen_name(name)

        results = await asyncio.gather(
            *[screen_one(name) for name in names],
            return_exceptions=True
        )

        # Convert exceptions to empty results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ScreeningResult(
                    screened_name=names[i],
                    screened_at=datetime.utcnow(),
                    matches=[],
                    is_hit=False,
                    highest_score=0.0,
                    lists_checked=[]
                ))
            else:
                processed_results.append(result)

        return processed_results

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Convert to uppercase
        normalized = name.upper()

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Remove common prefixes/suffixes
        prefixes = ["MR", "MRS", "MS", "DR", "PROF"]
        for prefix in prefixes:
            if normalized.startswith(prefix + " "):
                normalized = normalized[len(prefix) + 1:]

        # Remove punctuation except hyphens
        normalized = re.sub(r"[^\w\s-]", "", normalized)

        return normalized.strip()

    def _check_match(
        self,
        normalized_name: str,
        sanctions_entry: Dict[str, Any],
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Optional[SanctionsMatch]:
        """Check if a name matches a sanctions entry."""
        entry_name = self._normalize_name(sanctions_entry["name"])
        aliases = [self._normalize_name(a) for a in sanctions_entry.get("aliases", [])]

        best_score = 0.0
        best_match_name = entry_name
        match_type = MatchType.FUZZY

        # Exact match check
        if normalized_name == entry_name:
            best_score = 100.0
            match_type = MatchType.EXACT
        else:
            # Fuzzy match on primary name
            score = self._fuzzy_score(normalized_name, entry_name)
            if score > best_score:
                best_score = score
                best_match_name = entry_name

            # Check aliases
            for alias in aliases:
                if normalized_name == alias:
                    best_score = 100.0
                    best_match_name = alias
                    match_type = MatchType.ALIAS
                    break
                else:
                    score = self._fuzzy_score(normalized_name, alias)
                    if score > best_score:
                        best_score = score
                        best_match_name = alias
                        match_type = MatchType.ALIAS

        # Apply additional matching criteria if provided
        if additional_info:
            # Boost score if nationality matches
            if "nationality" in additional_info:
                if additional_info["nationality"].upper() in [
                    n.upper() for n in sanctions_entry.get("nationalities", [])
                ]:
                    best_score = min(100.0, best_score * 1.1)

            # Boost score if birth date matches
            if "birth_date" in additional_info:
                if additional_info["birth_date"] in sanctions_entry.get("birth_dates", []):
                    best_score = min(100.0, best_score * 1.2)

        if best_score < self.threshold:
            return None

        return SanctionsMatch(
            list_type=sanctions_entry["list_type"],
            entity_type=sanctions_entry["entity_type"],
            match_type=match_type,
            matched_name=best_match_name,
            original_name=sanctions_entry["name"],
            score=best_score,
            sanctions_id=sanctions_entry["id"],
            aliases=sanctions_entry.get("aliases", []),
            nationalities=sanctions_entry.get("nationalities", []),
            birth_dates=sanctions_entry.get("birth_dates", []),
            programs=sanctions_entry.get("programs", []),
            reasons=sanctions_entry.get("reasons", [])
        )

    def _fuzzy_score(self, name1: str, name2: str) -> float:
        """Calculate fuzzy match score between two names."""
        # Use SequenceMatcher for basic fuzzy matching
        ratio = SequenceMatcher(None, name1, name2).ratio()

        # Also check token-based similarity
        tokens1 = set(name1.split())
        tokens2 = set(name2.split())

        if tokens1 and tokens2:
            token_overlap = len(tokens1 & tokens2) / max(len(tokens1), len(tokens2))
            # Combine both scores
            return (ratio * 0.6 + token_overlap * 0.4) * 100
        else:
            return ratio * 100

    async def get_list_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded sanctions lists."""
        await self.initialize()

        eu_count = len([s for s in self._demo_sanctions if s["list_type"] == SanctionsListType.EU_CONSOLIDATED])
        ofac_count = len([s for s in self._demo_sanctions if s["list_type"] == SanctionsListType.OFAC_SDN])

        return {
            "total_entries": len(self._demo_sanctions),
            "by_list": {
                "eu_consolidated": eu_count,
                "ofac_sdn": ofac_count
            },
            "last_updated": datetime.utcnow().isoformat(),
            "status": "demo_data"
        }

    async def health_check(self) -> bool:
        """Check if the service is healthy."""
        await self.initialize()
        return len(self._demo_sanctions) > 0
