"""
Document Content Extraction

Extracts full text from PDF documents for indexing and search.
"""

import requests
from typing import Optional, Dict, Any
import re
from bs4 import BeautifulSoup


class ContentExtractor:
    """
    Extracts full text content from EU legal documents.

    Uses multiple strategies:
    1. EUR-Lex HTML text extraction (primary)
    2. PDF text extraction (fallback)
    3. FORMEX XML parsing (if available)
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; EULegalMonitor/1.0)'
        })

    def extract_content(self, celex: str) -> Optional[Dict[str, Any]]:
        """
        Extract full text content for a document.

        Args:
            celex: CELEX number

        Returns:
            Dict with:
                - full_text: Complete text content
                - language: Document language
                - extraction_method: How content was extracted
                - article_breakdown: List of articles with text
        """
        # Try HTML extraction first (fastest and most reliable)
        result = self._extract_from_html(celex)
        if result:
            return result

        # Fallback to noting that content is available via PDF
        return {
            "full_text": None,
            "language": "en",
            "extraction_method": "pdf_available",
            "article_breakdown": [],
            "note": "Full text available in PDF format"
        }

    def _extract_from_html(self, celex: str) -> Optional[Dict[str, Any]]:
        """
        Extract content from EUR-Lex HTML version.

        EUR-Lex provides clean HTML versions of most documents.
        """
        try:
            # EUR-Lex HTML endpoint
            url = f"https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:{celex}"

            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract main content
            content_div = soup.find('div', {'id': 'text'}) or soup.find('div', {'class': 'eli-main-title'})
            if not content_div:
                # Try alternative selectors
                content_div = soup.find('div', {'class': 'content'})

            if not content_div:
                return None

            # Extract text
            full_text = content_div.get_text(separator='\n', strip=True)

            # Clean up text
            full_text = self._clean_text(full_text)

            # Try to extract articles
            articles = self._extract_articles(content_div)

            return {
                "full_text": full_text,
                "language": "en",
                "extraction_method": "html",
                "article_breakdown": articles,
                "word_count": len(full_text.split())
            }

        except Exception as e:
            print(f"HTML extraction failed for {celex}: {e}")
            return None

    def _extract_articles(self, content_div) -> list:
        """
        Extract individual articles from HTML content.

        Most EU legal documents are structured with numbered articles.
        """
        articles = []

        # Look for article headings
        article_pattern = re.compile(r'Article\s+(\d+[a-z]?)', re.IGNORECASE)

        # Find all headings that match article pattern
        for heading in content_div.find_all(['h1', 'h2', 'h3', 'h4', 'p']):
            text = heading.get_text(strip=True)
            match = article_pattern.match(text)

            if match:
                article_num = match.group(1)

                # Get the article content (next siblings until next article)
                content_parts = []
                for sibling in heading.find_next_siblings():
                    sibling_text = sibling.get_text(strip=True)

                    # Stop at next article
                    if article_pattern.match(sibling_text):
                        break

                    if sibling_text:
                        content_parts.append(sibling_text)

                if content_parts:
                    articles.append({
                        "number": article_num,
                        "title": text,
                        "content": "\n".join(content_parts)
                    })

        return articles

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        Removes excessive whitespace, fixes common issues.
        """
        # Remove multiple consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove multiple spaces
        text = re.sub(r' {2,}', ' ', text)

        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()

    def extract_key_sections(self, full_text: str) -> Dict[str, str]:
        """
        Extract key sections from full text.

        Identifies:
        - Preamble/Recitals
        - Definitions
        - Main provisions
        - Final provisions
        """
        sections = {}

        # Simple pattern matching for common sections
        if "Whereas:" in full_text or "Having regard to" in full_text:
            # Find recitals
            recitals_match = re.search(
                r'(Whereas:.*?)(?=Article|CHAPTER|SECTION)',
                full_text,
                re.DOTALL | re.IGNORECASE
            )
            if recitals_match:
                sections['recitals'] = recitals_match.group(1).strip()

        # Extract definitions if present
        definitions_match = re.search(
            r'(Article\s+\d+.*?Definitions?.*?)(?=Article\s+\d+)',
            full_text,
            re.DOTALL | re.IGNORECASE
        )
        if definitions_match:
            sections['definitions'] = definitions_match.group(1).strip()

        return sections

    def get_pdf_url(self, celex: str, language: str = "EN") -> str:
        """
        Get direct PDF download URL for a document.

        Args:
            celex: CELEX number
            language: Language code (EN, FR, DE, etc.)

        Returns:
            Direct PDF URL
        """
        return f"https://eur-lex.europa.eu/legal-content/{language}/TXT/PDF/?uri=CELEX:{celex}"

    def get_html_url(self, celex: str, language: str = "EN") -> str:
        """
        Get HTML view URL for a document.

        Args:
            celex: CELEX number
            language: Language code

        Returns:
            HTML view URL
        """
        return f"https://eur-lex.europa.eu/legal-content/{language}/TXT/HTML/?uri=CELEX:{celex}"
