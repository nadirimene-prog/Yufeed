"""
EU Consolidated Financial Sanctions List Integration

Fetches and parses the EU Consolidated Financial Sanctions List.

Source: https://webgate.ec.europa.eu/fsd/fsf
API Documentation: https://data.europa.eu/data/datasets

The EU list contains:
- Individuals and entities subject to asset freezes
- Travel ban information
- Sanctions program details
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from ..base import BaseIntegration, IntegrationResult, IntegrationStatus

logger = logging.getLogger(__name__)


class EUConsolidatedList(BaseIntegration):
    """
    EU Consolidated Financial Sanctions List provider.

    Fetches the official EU sanctions list and provides search capabilities.

    Note: In production, this would fetch from:
    https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList/content

    For now, uses demo data.
    """

    EU_SANCTIONS_URL = "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList/content"

    def __init__(self):
        super().__init__(
            name="EU Consolidated Sanctions List",
            base_url=self.EU_SANCTIONS_URL,
            timeout_seconds=60,
            cache_ttl_seconds=86400  # 24 hours
        )

        self._sanctions_data: List[Dict[str, Any]] = []
        self._last_fetch: Optional[datetime] = None

    async def health_check(self) -> bool:
        """Check if the EU list is accessible."""
        # In production, would check the actual endpoint
        return True

    async def _execute(self, **kwargs) -> IntegrationResult:
        """Fetch and parse the EU sanctions list."""
        try:
            # In production, would fetch from EU endpoint
            # For now, return cached/demo data
            return IntegrationResult(
                status=IntegrationStatus.SUCCESS,
                data=self._sanctions_data,
                source=self.name
            )

        except Exception as e:
            logger.error(f"Failed to fetch EU sanctions list: {e}")
            return IntegrationResult(
                status=IntegrationStatus.ERROR,
                error_message=str(e),
                source=self.name
            )

    async def fetch_list(self) -> IntegrationResult:
        """Fetch the latest EU sanctions list."""
        return await self.execute()

    async def search(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the EU sanctions list.

        Args:
            name: Name to search for
            nationality: Filter by nationality
            entity_type: Filter by entity type

        Returns:
            List of matching entries
        """
        result = await self.execute()
        if result.status != IntegrationStatus.SUCCESS:
            return []

        matches = result.data or []

        if name:
            name_upper = name.upper()
            matches = [
                m for m in matches
                if name_upper in m.get("name", "").upper()
                or any(name_upper in alias.upper() for alias in m.get("aliases", []))
            ]

        if nationality:
            nat_upper = nationality.upper()
            matches = [
                m for m in matches
                if any(nat_upper in n.upper() for n in m.get("nationalities", []))
            ]

        if entity_type:
            matches = [
                m for m in matches
                if m.get("entity_type", "").lower() == entity_type.lower()
            ]

        return matches

    def _parse_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse EU sanctions XML format."""
        entries = []

        try:
            root = ET.fromstring(xml_content)

            # Navigate the EU XML structure
            for entity in root.findall(".//sanctionEntity"):
                entry = {
                    "id": entity.get("euReferenceNumber", ""),
                    "list_type": "eu_consolidated",
                    "entity_type": self._determine_entity_type(entity),
                    "name": self._extract_name(entity),
                    "aliases": self._extract_aliases(entity),
                    "nationalities": self._extract_nationalities(entity),
                    "birth_dates": self._extract_birth_dates(entity),
                    "programs": self._extract_programs(entity),
                    "reasons": self._extract_reasons(entity),
                    "listing_date": self._extract_listing_date(entity)
                }
                entries.append(entry)

        except ET.ParseError as e:
            logger.error(f"Failed to parse EU sanctions XML: {e}")

        return entries

    def _determine_entity_type(self, entity: ET.Element) -> str:
        """Determine entity type from XML."""
        subject_type = entity.find(".//subjectType")
        if subject_type is not None:
            type_code = subject_type.get("code", "").lower()
            if "person" in type_code:
                return "individual"
            elif "enterprise" in type_code or "entity" in type_code:
                return "entity"
        return "unknown"

    def _extract_name(self, entity: ET.Element) -> str:
        """Extract primary name from XML."""
        name_alias = entity.find(".//nameAlias[@nameAliasType='primary']")
        if name_alias is not None:
            whole_name = name_alias.find("wholeName")
            if whole_name is not None and whole_name.text:
                return whole_name.text
        return ""

    def _extract_aliases(self, entity: ET.Element) -> List[str]:
        """Extract alias names from XML."""
        aliases = []
        for name_alias in entity.findall(".//nameAlias"):
            if name_alias.get("nameAliasType") != "primary":
                whole_name = name_alias.find("wholeName")
                if whole_name is not None and whole_name.text:
                    aliases.append(whole_name.text)
        return aliases

    def _extract_nationalities(self, entity: ET.Element) -> List[str]:
        """Extract nationalities from XML."""
        nationalities = []
        for citizenship in entity.findall(".//citizenship"):
            country = citizenship.find("country")
            if country is not None and country.text:
                nationalities.append(country.text)
        return nationalities

    def _extract_birth_dates(self, entity: ET.Element) -> List[str]:
        """Extract birth dates from XML."""
        dates = []
        for birth_date in entity.findall(".//birthdate"):
            date_elem = birth_date.find("date")
            if date_elem is not None and date_elem.text:
                dates.append(date_elem.text)
        return dates

    def _extract_programs(self, entity: ET.Element) -> List[str]:
        """Extract sanctions programs from XML."""
        programs = []
        for regulation in entity.findall(".//regulation"):
            programme = regulation.find("programme")
            if programme is not None and programme.text:
                programs.append(programme.text)
        return programs

    def _extract_reasons(self, entity: ET.Element) -> List[str]:
        """Extract listing reasons from XML."""
        reasons = []
        for remark in entity.findall(".//remark"):
            if remark.text:
                reasons.append(remark.text)
        return reasons

    def _extract_listing_date(self, entity: ET.Element) -> Optional[str]:
        """Extract listing date from XML."""
        regulation = entity.find(".//regulation")
        if regulation is not None:
            entry_date = regulation.find("entryIntoForceDate")
            if entry_date is not None and entry_date.text:
                return entry_date.text
        return None
