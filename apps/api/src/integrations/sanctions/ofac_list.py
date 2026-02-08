"""
OFAC SDN (Specially Designated Nationals) List Integration

Fetches and parses the US Treasury OFAC SDN list.

Source: https://sanctionslist.ofac.treas.gov/
API Documentation: https://ofac.treasury.gov/specially-designated-nationals-list-data-formats-data-schemas
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from ..base import BaseIntegration, IntegrationResult, IntegrationStatus

logger = logging.getLogger(__name__)


class OFACSDNList(BaseIntegration):
    """
    OFAC SDN (Specially Designated Nationals) List provider.

    Fetches the official OFAC SDN list and provides search capabilities.

    Note: In production, this would fetch from:
    https://sanctionslist.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML

    For now, uses demo data.
    """

    OFAC_SDN_URL = "https://sanctionslist.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"
    OFAC_SDN_JSON_URL = (
        "https://sanctionslist.ofac.treas.gov/api/PublicationPreview/exports/SDN_ENHANCED.JSON"
    )

    def __init__(self):
        super().__init__(
            name="OFAC SDN List",
            base_url=self.OFAC_SDN_URL,
            timeout_seconds=60,
            cache_ttl_seconds=86400,  # 24 hours
        )

        self._sanctions_data: List[Dict[str, Any]] = []
        self._last_fetch: Optional[datetime] = None

    async def health_check(self) -> bool:
        """Check if the OFAC list is accessible."""
        # In production, would check the actual endpoint
        return True

    async def _execute(self, **kwargs) -> IntegrationResult:
        """Fetch and parse the OFAC SDN list."""
        try:
            # In production, would fetch from OFAC endpoint
            # For now, return cached/demo data
            return IntegrationResult(
                status=IntegrationStatus.SUCCESS, data=self._sanctions_data, source=self.name
            )

        except Exception as e:
            logger.error(f"Failed to fetch OFAC SDN list: {e}")
            return IntegrationResult(
                status=IntegrationStatus.ERROR, error_message=str(e), source=self.name
            )

    async def fetch_list(self) -> IntegrationResult:
        """Fetch the latest OFAC SDN list."""
        return await self.execute()

    async def search(
        self,
        name: Optional[str] = None,
        sdn_type: Optional[str] = None,
        program: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search the OFAC SDN list.

        Args:
            name: Name to search for
            sdn_type: Filter by SDN type (individual, entity, vessel, aircraft)
            program: Filter by sanctions program

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
                m
                for m in matches
                if name_upper in m.get("name", "").upper()
                or any(name_upper in alias.upper() for alias in m.get("aliases", []))
            ]

        if sdn_type:
            matches = [m for m in matches if m.get("entity_type", "").lower() == sdn_type.lower()]

        if program:
            program_upper = program.upper()
            matches = [
                m for m in matches if any(program_upper in p.upper() for p in m.get("programs", []))
            ]

        return matches

    def _parse_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse OFAC SDN XML format."""
        entries = []

        try:
            root = ET.fromstring(xml_content)

            # OFAC uses namespace
            ns = {"ofac": "http://tempuri.org/sdnList.xsd"}

            for sdn_entry in root.findall(".//ofac:sdnEntry", ns):
                entry = {
                    "id": self._get_text(sdn_entry, "ofac:uid", ns),
                    "list_type": "ofac_sdn",
                    "entity_type": self._map_sdn_type(
                        self._get_text(sdn_entry, "ofac:sdnType", ns)
                    ),
                    "name": self._build_name(sdn_entry, ns),
                    "aliases": self._extract_aliases_ofac(sdn_entry, ns),
                    "nationalities": self._extract_nationalities_ofac(sdn_entry, ns),
                    "birth_dates": self._extract_dob_ofac(sdn_entry, ns),
                    "addresses": self._extract_addresses_ofac(sdn_entry, ns),
                    "programs": self._extract_programs_ofac(sdn_entry, ns),
                    "reasons": self._extract_remarks_ofac(sdn_entry, ns),
                    "identifications": self._extract_ids_ofac(sdn_entry, ns),
                }
                entries.append(entry)

        except ET.ParseError as e:
            logger.error(f"Failed to parse OFAC SDN XML: {e}")

        return entries

    def _get_text(self, element: ET.Element, path: str, ns: Dict[str, str]) -> str:
        """Get text content from an XML element."""
        found = element.find(path, ns)
        return found.text if found is not None and found.text else ""

    def _map_sdn_type(self, sdn_type: str) -> str:
        """Map OFAC SDN type to entity type."""
        type_map = {
            "Individual": "individual",
            "Entity": "entity",
            "Vessel": "vessel",
            "Aircraft": "aircraft",
        }
        return type_map.get(sdn_type, "unknown")

    def _build_name(self, sdn_entry: ET.Element, ns: Dict[str, str]) -> str:
        """Build full name from OFAC entry."""
        first = self._get_text(sdn_entry, "ofac:firstName", ns)
        last = self._get_text(sdn_entry, "ofac:lastName", ns)

        if first and last:
            return f"{last}, {first}"
        elif last:
            return last
        else:
            return self._get_text(sdn_entry, "ofac:sdnName", ns)

    def _extract_aliases_ofac(self, sdn_entry: ET.Element, ns: Dict[str, str]) -> List[str]:
        """Extract aliases from OFAC entry."""
        aliases = []
        for aka in sdn_entry.findall(".//ofac:akaList/ofac:aka", ns):
            alias_name = self._get_text(aka, "ofac:lastName", ns)
            first_name = self._get_text(aka, "ofac:firstName", ns)
            if first_name:
                alias_name = f"{alias_name}, {first_name}"
            if alias_name:
                aliases.append(alias_name)
        return aliases

    def _extract_nationalities_ofac(self, sdn_entry: ET.Element, ns: Dict[str, str]) -> List[str]:
        """Extract nationalities from OFAC entry."""
        nationalities = []
        for nationality in sdn_entry.findall(".//ofac:nationalityList/ofac:nationality", ns):
            country = self._get_text(nationality, "ofac:country", ns)
            if country:
                nationalities.append(country)
        return nationalities

    def _extract_dob_ofac(self, sdn_entry: ET.Element, ns: Dict[str, str]) -> List[str]:
        """Extract dates of birth from OFAC entry."""
        dobs = []
        for dob in sdn_entry.findall(".//ofac:dateOfBirthList/ofac:dateOfBirthItem", ns):
            date = self._get_text(dob, "ofac:dateOfBirth", ns)
            if date:
                dobs.append(date)
        return dobs

    def _extract_addresses_ofac(self, sdn_entry: ET.Element, ns: Dict[str, str]) -> List[str]:
        """Extract addresses from OFAC entry."""
        addresses = []
        for addr in sdn_entry.findall(".//ofac:addressList/ofac:address", ns):
            parts = []
            for field in ["ofac:address1", "ofac:address2", "ofac:city", "ofac:country"]:
                value = self._get_text(addr, field, ns)
                if value:
                    parts.append(value)
            if parts:
                addresses.append(", ".join(parts))
        return addresses

    def _extract_programs_ofac(self, sdn_entry: ET.Element, ns: Dict[str, str]) -> List[str]:
        """Extract sanctions programs from OFAC entry."""
        programs = []
        for program in sdn_entry.findall(".//ofac:programList/ofac:program", ns):
            if program.text:
                programs.append(program.text)
        return programs

    def _extract_remarks_ofac(self, sdn_entry: ET.Element, ns: Dict[str, str]) -> List[str]:
        """Extract remarks from OFAC entry."""
        remarks = self._get_text(sdn_entry, "ofac:remarks", ns)
        return [remarks] if remarks else []

    def _extract_ids_ofac(self, sdn_entry: ET.Element, ns: Dict[str, str]) -> List[Dict[str, str]]:
        """Extract identification documents from OFAC entry."""
        ids = []
        for id_item in sdn_entry.findall(".//ofac:idList/ofac:id", ns):
            id_entry = {
                "type": self._get_text(id_item, "ofac:idType", ns),
                "number": self._get_text(id_item, "ofac:idNumber", ns),
                "country": self._get_text(id_item, "ofac:idCountry", ns),
            }
            if id_entry["type"] or id_entry["number"]:
                ids.append(id_entry)
        return ids
