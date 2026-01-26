"""
CELEX Normalization Utilities

Provides flexible CELEX format handling to accept various user input formats
and normalize them to the standard CELEX format (e.g., 32016R0679).

Supports input formats like:
- 32016R0679 (standard)
- 2016/679 (year/number)
- GDPR, AI Act (common names)
- Regulation 2016/679, Directive 2016/680
- 32016R679 (missing leading zeros)
"""

import re
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Common abbreviations for well-known EU legislation
CELEX_ALIASES = {
    # GDPR
    "GDPR": "32016R0679",
    "GENERAL DATA PROTECTION REGULATION": "32016R0679",
    "DATA PROTECTION REGULATION": "32016R0679",

    # AI Act
    "AI ACT": "32024R1689",
    "ARTIFICIAL INTELLIGENCE ACT": "32024R1689",

    # DMA
    "DMA": "32022R1925",
    "DIGITAL MARKETS ACT": "32022R1925",

    # DSA
    "DSA": "32022R2065",
    "DIGITAL SERVICES ACT": "32022R2065",

    # ePrivacy Directive
    "EPRIVACY": "32002L0058",
    "EPRIVACY DIRECTIVE": "32002L0058",

    # PSD2
    "PSD2": "32015L2366",
    "PAYMENT SERVICES DIRECTIVE": "32015L2366",

    # NIS2
    "NIS2": "32022L2555",
    "NIS DIRECTIVE": "32022L2555",
}

# Document type mappings
DOCUMENT_TYPE_CODES = {
    "REGULATION": "R",
    "REG": "R",
    "DIRECTIVE": "L",
    "DIR": "L",
    "DECISION": "D",
    "DEC": "D",
    "RECOMMENDATION": "H",
    "REC": "H",
    "OPINION": "V",
    "OPN": "V",
}

# Sector codes (first digit of CELEX)
SECTOR_CODES = {
    "0": "TREATY",
    "1": "SECONDARY_LEGISLATION",
    "2": "EFTA",
    "3": "EU_LEGISLATION",
    "4": "COMPLEMENTARY",
    "5": "EXTERNAL",
    "6": "CJEU",
    "7": "NATIONAL_IMPLEMENTATION",
    "8": "EEA",
    "9": "COMMON_FOREIGN",
}


def normalize_celex(input_str: str, log: bool = True) -> Optional[str]:
    """
    Normalize various CELEX input formats to standard format.

    Args:
        input_str: User input (e.g., "GDPR", "2016/679", "32016R0679")

    Returns:
        Normalized CELEX string or None if cannot be parsed

    Examples:
        >>> normalize_celex("GDPR")
        "32016R0679"
        >>> normalize_celex("2016/679")
        "32016R0679"
        >>> normalize_celex("Regulation 2016/679")
        "32016R0679"
        >>> normalize_celex("32016R679")
        "32016R0679"
    """
    if not input_str:
        return None

    # Clean input
    clean = input_str.strip().upper()

    # Check aliases first (GDPR, AI Act, etc.)
    if clean in CELEX_ALIASES:
        logger.info(f"Normalized alias '{input_str}' to {CELEX_ALIASES[clean]}")
        return CELEX_ALIASES[clean]

    # Already in standard CELEX format
    if re.match(r'^[0-9]{1,5}[A-Z]{1,3}[0-9]{1,6}[A-Z0-9]*$', clean):
        # Ensure 4-digit padding on year (e.g., 32016R679 -> 32016R0679)
        return _pad_celex_number(clean)

    # Format: "2016/679" or "2016-679"
    match = re.match(r'^(\d{4})[/-](\d+)$', clean)
    if match:
        year, number = match.groups()
        # Assume regulation (most common)
        celex = f"3{year}R{number.zfill(4)}"
        logger.info(f"Normalized '{input_str}' to {celex}")
        return celex

    # Format: "Regulation 2016/679", "Directive (EU) 2016/680"
    match = re.match(r'(REGULATION|DIRECTIVE|DECISION)\s*(?:\(EU\))?\s*(\d{4})[/-](\d+)', clean)
    if match:
        doc_type, year, number = match.groups()
        type_code = DOCUMENT_TYPE_CODES.get(doc_type, "R")
        celex = f"3{year}{type_code}{number.zfill(4)}"
        logger.info(f"Normalized '{input_str}' to {celex}")
        return celex

    # Format: "Regulation (EU) No 679/2016"
    match = re.match(r'(REGULATION|DIRECTIVE|DECISION)\s*(?:\(EU\))?\s*(?:NO\.?\s*)?(\d+)[/-](\d{4})', clean)
    if match:
        doc_type, number, year = match.groups()
        type_code = DOCUMENT_TYPE_CODES.get(doc_type, "R")
        celex = f"3{year}{type_code}{number.zfill(4)}"
        logger.info(f"Normalized '{input_str}' to {celex}")
        return celex

    # Format: "32016R679" (missing leading zeros in number)
    match = re.match(r'^(\d{1,5})([A-Z]{1,3})(\d{1,6})([A-Z0-9]*)$', clean)
    if match:
        sector_year, doc_type, number, suffix = match.groups()
        celex = f"{sector_year}{doc_type}{number.zfill(4)}{suffix}"
        logger.info(f"Normalized '{input_str}' to {celex}")
        return celex

        if log:
            logger.warning(f"Could not normalize CELEX input: '{input_str}'")
    return None


def _pad_celex_number(celex: str) -> str:
    """
    Ensure CELEX document number has proper padding (usually 4 digits).

    Example: 32016R679 -> 32016R0679
    """
    match = re.match(r'^(\d{1,5})([A-Z]{1,3})(\d{1,6})([A-Z0-9]*)$', celex)
    if not match:
        return celex

    sector_year, doc_type, number, suffix = match.groups()

    # Pad number to 4 digits (standard for most EU documents)
    if len(number) < 4:
        number = number.zfill(4)

    return f"{sector_year}{doc_type}{number}{suffix}"


def parse_celex(celex: str) -> Optional[Dict[str, str]]:
    """
    Parse CELEX into its components.

    Args:
        celex: Valid CELEX string (e.g., "32016R0679")

    Returns:
        Dictionary with parsed components or None if invalid

    Example:
        >>> parse_celex("32016R0679")
        {
            "sector": "3",
            "year": "2016",
            "document_type": "R",
            "number": "0679",
            "suffix": "",
            "sector_name": "EU_LEGISLATION",
            "type_name": "REGULATION"
        }
    """
    if not celex:
        return None

    # Standard CELEX pattern
    match = re.match(r'^(\d)(\d{4})([A-Z]{1,3})(\d{4,6})([A-Z0-9]*)$', celex)
    if not match:
        return None

    sector, year, doc_type, number, suffix = match.groups()

    # Reverse lookup for type name
    type_name = None
    for key, value in DOCUMENT_TYPE_CODES.items():
        if value == doc_type:
            type_name = key
            break

    return {
        "sector": sector,
        "year": year,
        "document_type": doc_type,
        "number": number,
        "suffix": suffix,
        "sector_name": SECTOR_CODES.get(sector, "UNKNOWN"),
        "type_name": type_name or "UNKNOWN"
    }


def generate_celex_variations(celex: str) -> list[str]:
    """
    Generate possible CELEX variations for fuzzy matching.

    Args:
        celex: Standard CELEX string

    Returns:
        List of possible variations

    Example:
        >>> generate_celex_variations("32016R0679")
        ["32016R0679", "32016R679", "2016/679", "2016-679"]
    """
    parsed = parse_celex(celex)
    if not parsed:
        return [celex]

    variations = [celex]

    # Add version without leading zeros
    if parsed["number"].startswith("0"):
        no_zeros = f"{parsed['sector']}{parsed['year']}{parsed['document_type']}{parsed['number'].lstrip('0')}{parsed['suffix']}"
        variations.append(no_zeros)

    # Add year/number format
    variations.append(f"{parsed['year']}/{parsed['number'].lstrip('0')}")
    variations.append(f"{parsed['year']}-{parsed['number'].lstrip('0')}")

    # Add type + year/number format
    type_name = parsed.get("type_name", "").capitalize()
    if type_name and type_name != "UNKNOWN":
        variations.append(f"{type_name} {parsed['year']}/{parsed['number'].lstrip('0')}")
        variations.append(f"{type_name} (EU) {parsed['year']}/{parsed['number'].lstrip('0')}")

    return list(set(variations))


def suggest_celex(partial_input: str, limit: int = 10) -> list[str]:
    """
    Suggest CELEX numbers based on partial input.

    Args:
        partial_input: Partial CELEX or search term
        limit: Maximum number of suggestions

    Returns:
        List of suggested CELEX strings
    """
    clean = partial_input.strip().upper()
    suggestions = []

    # Check for alias matches
    for alias, celex in CELEX_ALIASES.items():
        if clean in alias:
            suggestions.append(celex)

    # Limit results
    return suggestions[:limit]


def is_valid_celex(celex: str) -> bool:
    """
    Validate if string is a valid CELEX format.

    Args:
        celex: String to validate

    Returns:
        True if valid CELEX format
    """
    if not celex:
        return False
    pattern = r'^[0-9]{1,5}[A-Z]{1,3}[0-9]{1,6}[A-Z0-9]*$'
    return re.match(pattern, celex) is not None
