#!/usr/bin/env python3
"""
CELEX Utilities - Validation and Normalization
Fixes: Wrong CELEX formats (e.g., D2366→L2366 for Directives)
"""

import re
import sys
from typing import Tuple, List, Optional
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class CELEXInfo:
    raw: str
    normalized: str
    sector: int  # 1, 2, or 3 (year prefix)
    year: int
    doc_type: str  # R, D, L, E, etc.
    number: str
    is_valid: bool
    suggested_fixes: List[str]
    document_category: Optional[str]  # Regulation, Directive, etc.


# Document type mappings based on official EUR-Lex documentation
DOC_TYPE_CODES = {
    "R": "Regulation",
    "L": "Legislative act (Directives, Decisions)",
    "D": "Decision (non-legislative)",
    "E": "Decision of the Council",
    "F": "Common foreign and security policy",
    "S": "Treaty",
    "C": "Communication",
    "B": "Budget",
    "K": "Corrigendum",
    "A": "Agreement",
    "X": "Other documents",
    "O": "Not published in the Official Journal",
}

# Keywords that suggest document type
TITLE_KEYWORDS = {
    "REGULATION": ["REGULATION", "AMLR", "GDPR", "MICA", "SFDR", "CSRD", "DORA"],
    "DIRECTIVE": ["DIRECTIVE", "PSD", "EMD", "AMLD", "MLD", "CRD", "CRR", "NIS"],
    "DECISION": ["DECISION", "IMPLEMENTING DECISION", "DELEGATED DECISION"],
    "GUIDELINE": ["GUIDELINE", "GUIDELINES"],
}


class CELEXUtils:
    """Utilities for working with CELEX numbers."""

    @staticmethod
    def parse(celex: str) -> CELEXInfo:
        """Parse and validate a CELEX number."""
        raw = celex
        celex = re.sub(r"[.\s]", "", celex.upper().strip())

        is_valid = True
        suggested_fixes = []
        document_category = None

        # Check basic format
        if not re.match(r"^[123]\d{3,4}[A-Z]\d+$", celex):
            is_valid = False
            suggested_fixes.append("Check format: should be like 32023R1114")

        # Initialize defaults
        sector = 0
        year = 0
        doc_type = ""
        number = ""

        # Extract components
        try:
            if len(celex) > 0:
                sector = int(celex[0])

                # Year (4 or 2 digits based on sector)
                if sector == 3:
                    year = int(celex[1:5])
                    doc_type = celex[5] if len(celex) > 5 else ""
                    number = celex[6:] if len(celex) > 6 else ""
                elif sector == 1 or sector == 2:
                    year = int(celex[1:3])  # 2-digit year
                    doc_type = celex[3] if len(celex) > 3 else ""
                    number = celex[4:] if len(celex) > 4 else ""
                else:
                    is_valid = False

            # Check document type is valid
            if doc_type and doc_type not in DOC_TYPE_CODES:
                is_valid = False
                suggested_fixes.append(f"Unknown document type: {doc_type}")

            if doc_type:
                document_category = DOC_TYPE_CODES.get(doc_type)

        except (IndexError, ValueError):
            is_valid = False

        return CELEXInfo(
            raw=raw,
            normalized=celex,
            sector=sector,
            year=year,
            doc_type=doc_type,
            number=number,
            is_valid=is_valid,
            suggested_fixes=suggested_fixes,
            document_category=document_category,
        )

    @staticmethod
    def suggest_corrections(celex: str, title: str = "") -> List[str]:
        """Suggest corrections based on title analysis."""
        info = CELEXUtils.parse(celex)
        suggestions = []
        title_upper = title.upper()

        # Detect document type from title
        detected_type = None
        for doc_type, keywords in TITLE_KEYWORDS.items():
            for kw in keywords:
                if kw in title_upper:
                    detected_type = doc_type
                    break
            if detected_type:
                break

        # Suggest corrections if mismatch
        if detected_type == "REGULATION" and info.doc_type != "R":
            if len(info.normalized) > 5:
                corrected = info.normalized[:5] + "R" + info.normalized[6:]
                suggestions.append(corrected)

        elif detected_type == "DIRECTIVE":
            # Directives use 'L' (legislative) not 'D' (decision)
            if info.doc_type == "D":
                corrected = info.normalized[:5] + "L" + info.normalized[6:]
                suggestions.append(corrected)
            elif info.doc_type != "L":
                corrected = info.normalized[:5] + "L" + info.normalized[6:]
                suggestions.append(corrected)

        elif detected_type == "DECISION" and info.doc_type not in ["D", "E"]:
            if len(info.normalized) > 5:
                corrected = info.normalized[:5] + "D" + info.normalized[6:]
                suggestions.append(corrected)

        return suggestions

    @staticmethod
    def normalize_for_search(celex: str, title: str = "") -> List[str]:
        """Get all CELEX variants to try for content extraction."""
        info = CELEXUtils.parse(celex)
        variants = [info.normalized]

        # Add corrections from title analysis
        corrections = CELEXUtils.suggest_corrections(celex, title)
        variants.extend(corrections)

        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                unique_variants.append(v)

        return unique_variants

    @staticmethod
    def validate_batch(celexes: List[Tuple[str, str]]) -> dict:
        """Validate a batch of CELEX numbers with titles."""
        results = {
            "valid": [],
            "invalid": [],
            "corrected": [],
        }

        for celex, title in celexes:
            info = CELEXUtils.parse(celex)
            suggestions = CELEXUtils.suggest_corrections(celex, title)

            if info.is_valid and not suggestions:
                results["valid"].append({"celex": celex, "title": title, "info": info})
            elif suggestions:
                results["corrected"].append(
                    {"celex": celex, "title": title, "suggested": suggestions[0], "info": info}
                )
            else:
                results["invalid"].append({"celex": celex, "title": title, "info": info})

        return results


def test_celex_utils():
    """Test CELEX utilities with known cases."""

    # Test cases: (celex, title, expected_valid, expected_corrections)
    test_cases = [
        ("32023R1114", "Markets in Crypto-Assets Regulation", True, []),
        ("32015D2366", "Payment Services Directive 2 (PSD2)", True, ["32015L2366"]),
        ("32016R0679", "General Data Protection Regulation", True, []),  # GD 0679
        ("32024R1624", "Anti-Money Laundering Regulation", True, []),
        ("INVALID", "Some Title", False, []),
        ("32015L2366", "PSD2 Directive", True, []),  # Already correct
    ]

    print("\n" + "=" * 70)
    print("CELEX UTILITIES - TEST RESULTS")
    print("=" * 70)

    utils = CELEXUtils()
    passed = 0

    for celex, title, expected_valid, expected_corrections in test_cases:
        info = utils.parse(celex)
        corrections = utils.suggest_corrections(celex, title)

        valid_ok = info.is_valid == expected_valid
        corrections_ok = corrections == expected_corrections

        status = "✅ PASS" if (valid_ok and corrections_ok) else "❌ FAIL"

        print(f"\n{status} {celex}")
        print(f"   Title: {title[:50]}...")
        print(f"   Type: {info.document_category} ({info.doc_type})")
        print(f"   Year: {info.year}")
        print(f"   Valid: {info.is_valid} (expected {expected_valid})")
        print(f"   Corrections: {corrections}")

        if valid_ok and corrections_ok:
            passed += 1

    total = len(test_cases)
    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed}/{total} tests passed ({100*passed//total}%)")
    print("=" * 70)

    return passed == total


def main():
    success = test_celex_utils()

    # Also print documentation
    print("\n" + "=" * 70)
    print("CELEX FORMAT REFERENCE")
    print("=" * 70)
    print(
        """
CELEX Format: [SECTOR][YEAR][TYPE][NUMBER]

Sector:
  1 = Treaties, international agreements (1951-1977)
  2 = Acts 1978-1985
  3 = Acts from 1986 onwards

Year: 2 or 4 digits depending on sector

Type:
  R = Regulation
  L = Legislative act (Directives, Decisions)
  D = Decision (non-legislative)
  E = Decision of the Council
  S = Treaty
  C = Communication

Examples:
  32023R1114 = MiCA Regulation (2023)
  32015L2366 = PSD2 Directive (2015)
  32024R1624 = AML Regulation (2024)
    """
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
