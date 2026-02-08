import httpx
import logging
import os
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, date

# Import utilities using proper relative imports
from src.utils.celex_utils import normalize_celex, is_valid_celex, generate_celex_variations
from src.cache.celex_cache import CelexCache

logger = logging.getLogger(__name__)


class CellarClient:
    """
    Client for querying the EU Cellar (Publications Office) SPARQL endpoint.
    Cellar is the content repository of the EU Publications Office containing
    metadata and full-text content of EU legal documents.
    """

    SPARQL_ENDPOINT = "http://publications.europa.eu/webapi/rdf/sparql"
    BASE_URL = "http://publications.europa.eu/resource/cellar"

    def __init__(self, redis_url: str = None, enable_cache: bool = True):
        """
        Initialize Cellar client with optional Redis caching.

        Args:
            redis_url: Redis connection URL for caching (defaults to REDIS_URL env var or localhost)
            enable_cache: Whether to enable Redis caching (default: True)
        """
        self.client = httpx.Client(timeout=60.0)

        # Use environment variable if redis_url not provided
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        self.cache = CelexCache(redis_url=redis_url) if enable_cache else None

        if self.cache and self.cache.is_connected():
            logger.info("CellarClient initialized with Redis caching enabled")
        else:
            logger.info("CellarClient initialized without caching")

    @staticmethod
    def _validate_celex(celex: str) -> bool:
        """
        Validate CELEX format to prevent SPARQL injection.
        CELEX format: [year][type][number] e.g., 32016R0679
        """
        if not celex:
            return False
        # CELEX must match: 1-5 digits + letter(s) + digits
        # Examples: 32016R0679, 32024R1624
        pattern = r"^[0-9]{1,5}[A-Z]{1,3}[0-9]{1,6}[A-Z0-9]*$"
        return re.match(pattern, celex) is not None

    @staticmethod
    def _sanitize_celex(celex: str) -> str:
        """
        Sanitize CELEX input by escaping special characters.
        """
        # Only allow alphanumeric characters
        return re.sub(r"[^A-Z0-9]", "", celex.upper())

    @staticmethod
    def _sanitize_query_term(term: str) -> str:
        if not term:
            return ""
        cleaned = term.strip().lower()
        cleaned = re.sub(r"[^\w\s'/-]", " ", cleaned, flags=re.UNICODE)
        cleaned = re.sub(r"\\s+", " ", cleaned)
        return cleaned.strip()

    @staticmethod
    def _extract_oj_identifier(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        identifier = value
        if "oj:" in identifier:
            identifier = identifier.split("oj:")[-1]
        if "/oj/" in identifier:
            identifier = identifier.split("/oj/")[-1]
        if "/" in identifier:
            identifier = identifier.rsplit("/", 1)[-1]
        return identifier.strip() or None

    @staticmethod
    def _extract_oj_series(identifier: Optional[str]) -> Optional[str]:
        if not identifier:
            return None
        match = re.match(r"^([A-Z]{1,3})_", identifier)
        if not match:
            return None
        return match.group(1)

    def search_oj_act_by_date(self, publication_date: date) -> List[Dict[str, Any]]:
        if not publication_date:
            return []

        date_literal = publication_date.isoformat()
        sparql_query = f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?act ?sig
        WHERE {{
          ?c_act owl:sameAs ?act .
          ?c_act cdm:official-journal-act_date_publication "{date_literal}"^^xsd:date .
          FILTER (regex(str(?act), "/oj/")) .
          ?c_exp cdm:expression_belongs_to_work ?c_act .
          ?c_manif cdm:manifestation_manifests_expression ?c_exp .
          OPTIONAL {{
            ?c_sig cdm:signature_digital_signs_manifestation ?c_manif .
            ?c_sig owl:sameAs ?sig .
          }}
        }}
        """

        try:
            response = self.client.post(
                self.SPARQL_ENDPOINT,
                data={"query": sparql_query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()
            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            acts = []
            for row in bindings:
                act_uri = row.get("act", {}).get("value")
                sig_uri = row.get("sig", {}).get("value")
                act_identifier = self._extract_oj_identifier(act_uri)
                signature_identifier = self._extract_oj_identifier(sig_uri)
                series = self._extract_oj_series(act_identifier)
                acts.append(
                    {
                        "act_uri": act_uri,
                        "signature_uri": sig_uri,
                        "act_identifier": act_identifier,
                        "signature_identifier": signature_identifier,
                        "series": series,
                        "publication_date": publication_date,
                    }
                )
            return acts
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error querying OJ act-by-act for {date_literal}: {exc}")
            return []
        except Exception as exc:
            logger.error(f"Error querying OJ act-by-act for {date_literal}: {exc}")
            return []

    def query_by_celex(self, celex: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Query Cellar using CELEX to get enriched metadata.
        Returns structured metadata or None if not found.

        Now supports:
        - CELEX normalization (accepts "GDPR", "2016/679", "Regulation 2016/679", etc.)
        - Redis caching for 100x faster queries
        - Flexible input formats

        Args:
            celex: CELEX number or variation (e.g., "GDPR", "2016/679", "32016R0679")
            use_cache: Whether to use Redis cache (default: True)

        Returns:
            Document metadata dict or None

        Security: Validates and sanitizes CELEX to prevent SPARQL injection.
        """
        if not celex:
            return None

        # Normalize CELEX input (handles GDPR, 2016/679, etc.)
        normalized_celex = normalize_celex(celex)
        if not normalized_celex:
            logger.warning(f"Could not normalize CELEX input: {celex}")
            return None

        # Validate normalized CELEX
        if not self._validate_celex(normalized_celex):
            logger.warning(f"Invalid CELEX format after normalization: {normalized_celex}")
            return None

        # Check cache first
        if use_cache and self.cache:
            cached = self.cache.get(normalized_celex)
            if cached:
                logger.info(f"Cache HIT for {celex} -> {normalized_celex}")
                return cached

        # Sanitize input as additional security layer
        safe_celex = self._sanitize_celex(normalized_celex)

        # SPARQL query to fetch document metadata by CELEX
        sparql_query = f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?work ?title ?workType ?dateDocument ?dateEntryIntoForce
               ?eli ?cellarId ?subject ?directoryCode
        WHERE {{
          ?work cdm:resource_legal_id_celex "{safe_celex}" .
          OPTIONAL {{ ?work cdm:work_has_resource-type ?workType . }}
          OPTIONAL {{ ?work cdm:work_date_document ?dateDocument . }}
          OPTIONAL {{ ?work cdm:work_date_entry-into-force ?dateEntryIntoForce . }}
          OPTIONAL {{ ?work cdm:resource_legal_id_eli ?eli . }}
          OPTIONAL {{ ?work cdm:work_is_about_subject-matter ?subject . }}
          OPTIONAL {{ ?work cdm:work_is_about_concept_directory-code ?directoryCode . }}
          OPTIONAL {{
            ?work cdm:work_has_expression ?expression .
            ?expression cdm:expression_title ?title .
            FILTER(LANG(?title) = "en")
          }}
          BIND(STRAFTER(STR(?work), "cellar/") AS ?cellarId)
        }}
        LIMIT 1
        """

        try:
            logger.info(f"Querying Cellar SPARQL for CELEX: {celex}")

            response = self.client.post(
                self.SPARQL_ENDPOINT,
                data={"query": sparql_query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", {}).get("bindings", [])

            if not results:
                logger.warning(f"No Cellar data found for CELEX: {celex}")
                return None

            metadata = self._parse_sparql_result(results[0], normalized_celex)

            # Cache the result for future queries
            if use_cache and self.cache and metadata:
                self.cache.set(normalized_celex, metadata)
                logger.info(f"Cached metadata for {normalized_celex}")

            return metadata

        except httpx.HTTPError as e:
            logger.error(f"HTTP error querying Cellar for {celex}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error querying Cellar for {celex}: {e}")
            return None

    def search_by_title_terms(
        self,
        terms: List[str],
        language: str,
        limit: int = 100,
        offset: int = 0,
        require_language: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search Cellar by title terms for a given language.
        Returns list of metadata dictionaries.
        """
        cleaned_terms = [self._sanitize_query_term(term) for term in terms]
        cleaned_terms = [term for term in cleaned_terms if term]
        if not cleaned_terms:
            return []

        language = (language or "en").lower()
        lang_codes = ["en", "eng"] if language == "en" else ["fr", "fra"]
        lang_filter = " || ".join([f'LANGMATCHES(LANG(?title), "{code}")' for code in lang_codes])
        lang_filter = f"({lang_filter})" if require_language else "true"
        filters = " || ".join([f'CONTAINS(LCASE(STR(?title)), "{term}")' for term in cleaned_terms])

        sparql_query = f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?work ?celex ?title ?workType ?dateDocument ?dateEntryIntoForce
               ?eli ?cellarId ?titleLang
        WHERE {{
          ?work cdm:resource_legal_id_celex ?celex .
          OPTIONAL {{ ?work cdm:work_has_resource-type ?workType . }}
          OPTIONAL {{ ?work cdm:work_date_document ?dateDocument . }}
          OPTIONAL {{ ?work cdm:work_date_entry-into-force ?dateEntryIntoForce . }}
          OPTIONAL {{ ?work cdm:resource_legal_id_eli ?eli . }}
          {{
            ?work cdm:work_has_expression ?expression .
            ?expression cdm:expression_title ?title .
          }}
          UNION
          {{
            ?work cdm:work_title ?title .
          }}
          UNION
          {{
            ?work dc:title ?title .
          }}
          BIND(LANG(?title) AS ?titleLang)
          FILTER({lang_filter})
          FILTER({filters})
          BIND(STRAFTER(STR(?work), "cellar/") AS ?cellarId)
        }}
        LIMIT {int(limit)}
        OFFSET {int(offset)}
        """

        try:
            response = self.client.post(
                self.SPARQL_ENDPOINT,
                data={"query": sparql_query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", {}).get("bindings", [])
            items = [
                self._parse_sparql_result(row, row.get("celex", {}).get("value", ""))
                for row in results
            ]
            if not require_language:
                allowed = {"en", "eng", "fr", "fra"}
                items = [
                    item for item in items if (item.get("title_lang") or "").lower() in allowed
                ]
            return [item for item in items if item.get("celex")]
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error searching Cellar: {exc}")
            return []
        except Exception as exc:
            logger.error(f"Error searching Cellar: {exc}")
            return []

    def _parse_sparql_result(self, result: Dict, celex: str) -> Dict[str, Any]:
        """
        Parse SPARQL JSON result into structured metadata.
        """

        def get_value(field: str) -> Optional[str]:
            return result.get(field, {}).get("value")

        def parse_date(date_str: Optional[str]) -> Optional[datetime]:
            if not date_str:
                return None
            try:
                # Cellar dates are typically in ISO format (YYYY-MM-DD)
                return datetime.fromisoformat(date_str.split("T")[0])
            except (ValueError, AttributeError):
                return None

        metadata = {
            "celex": celex,
            "cellar_id": get_value("cellarId"),
            "eli": get_value("eli"),
            "title": get_value("title"),
            "title_lang": get_value("titleLang"),
            "work_type": get_value("workType"),
            "date_document": parse_date(get_value("dateDocument")),
            "date_entry_into_force": parse_date(get_value("dateEntryIntoForce")),
            "subject": get_value("subject"),
            "directory_code": get_value("directoryCode"),
            "work_uri": get_value("work"),
        }

        logger.info(f"Parsed Cellar metadata for {celex}: title={metadata.get('title')}")
        return metadata

    def get_document_manifestations(self, cellar_id: str) -> list:
        """
        Get available manifestations (PDF, HTML, XML) for a document.
        Returns list of dictionaries with format and URL.
        """
        if not cellar_id:
            return []

        sparql_query = f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>

        SELECT DISTINCT ?format ?url
        WHERE {{
          <http://publications.europa.eu/resource/cellar/{cellar_id}>
            cdm:work_has_expression ?expression .
          ?expression cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> ;
                     cdm:expression_has_manifestation ?manifestation .
          ?manifestation cdm:manifestation_has_item ?item .
          ?item cdm:manifestation_type ?format ;
                cdm:manifestation_url ?url .
        }}
        """

        try:
            response = self.client.post(
                self.SPARQL_ENDPOINT,
                data={"query": sparql_query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            manifestations = []
            for binding in bindings:
                manifestations.append(
                    {
                        "format": binding.get("format", {}).get("value", "").split("/")[-1],
                        "url": binding.get("url", {}).get("value"),
                    }
                )

            logger.info(f"Found {len(manifestations)} manifestations for {cellar_id}")
            return manifestations

        except Exception as e:
            logger.error(f"Error fetching manifestations for {cellar_id}: {e}")
            return []

    def download_content(self, url: str) -> Optional[bytes]:
        """
        Download document content from given URL.
        Returns raw bytes or None.
        """
        try:
            logger.info(f"Downloading content from: {url}")
            response = self.client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading content from {url}: {e}")
            return None

    def get_related_documents(self, cellar_id: str) -> list:
        """
        Find related documents (amendments, based-on relationships, etc.).
        """
        if not cellar_id:
            return []

        sparql_query = f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>

        SELECT DISTINCT ?relatedWork ?relationType ?relatedCelex
        WHERE {{
          {{
            <http://publications.europa.eu/resource/cellar/{cellar_id}> ?relationType ?relatedWork .
            ?relatedWork cdm:resource_legal_id_celex ?relatedCelex .
            FILTER(?relationType IN (
              cdm:work_based_on_work,
              cdm:work_amends_work,
              cdm:work_is_amended_by_work,
              cdm:work_corrects_work,
              cdm:work_cites_work
            ))
          }}
          UNION
          {{
            ?relatedWork ?relationType <http://publications.europa.eu/resource/cellar/{cellar_id}> .
            ?relatedWork cdm:resource_legal_id_celex ?relatedCelex .
            FILTER(?relationType IN (
              cdm:work_based_on_work,
              cdm:work_amends_work,
              cdm:work_is_amended_by_work,
              cdm:work_corrects_work,
              cdm:work_cites_work
            ))
          }}
        }}
        LIMIT 50
        """

        try:
            response = self.client.post(
                self.SPARQL_ENDPOINT,
                data={"query": sparql_query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            relations = []
            for binding in bindings:
                relation_type = binding.get("relationType", {}).get("value", "").split("#")[-1]
                relations.append(
                    {
                        "related_celex": binding.get("relatedCelex", {}).get("value"),
                        "relation_type": relation_type,
                        "related_work_uri": binding.get("relatedWork", {}).get("value"),
                    }
                )

            logger.info(f"Found {len(relations)} related documents for {cellar_id}")
            return relations

        except Exception as e:
            logger.error(f"Error fetching related documents for {cellar_id}: {e}")
            return []

    def query_bulk_celex(
        self, celex_list: List[str], use_cache: bool = True
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Query multiple CELEX numbers in batch.

        Optimizations:
        - Checks cache first for all entries (single Redis MGET)
        - Only queries Cellar for cache misses
        - Caches new results in bulk

        Args:
            celex_list: List of CELEX numbers to query
            use_cache: Whether to use Redis cache

        Returns:
            Dictionary mapping CELEX to metadata (or None if not found)

        Example:
            >>> client.query_bulk_celex(["GDPR", "AI Act", "32022R1925"])
            {
                "GDPR": {...metadata...},
                "AI Act": {...metadata...},
                "32022R1925": {...metadata...}
            }
        """
        if not celex_list:
            return {}

        # Normalize all inputs
        normalized_map = {}  # original -> normalized
        for celex in celex_list:
            normalized = normalize_celex(celex)
            if normalized:
                normalized_map[celex] = normalized
            else:
                logger.warning(f"Could not normalize CELEX: {celex}")

        if not normalized_map:
            return {celex: None for celex in celex_list}

        results = {}

        # Check cache for all normalized CELEX
        if use_cache and self.cache:
            normalized_list = list(set(normalized_map.values()))
            cached_results = self.cache.get_many(normalized_list)

            # Map back to original inputs
            for original, normalized in normalized_map.items():
                if cached_results.get(normalized):
                    results[original] = cached_results[normalized]
                    logger.debug(f"Cache HIT for {original} -> {normalized}")

        # Query Cellar for cache misses
        to_fetch = [
            (original, normalized)
            for original, normalized in normalized_map.items()
            if original not in results
        ]

        if to_fetch:
            logger.info(f"Fetching {len(to_fetch)} CELEX from Cellar (cache misses)")
            new_entries = {}

            for original, normalized in to_fetch:
                # Query without cache (we'll bulk cache at the end)
                metadata = self.query_by_celex(original, use_cache=False)
                results[original] = metadata

                if metadata:
                    new_entries[normalized] = metadata

            # Bulk cache new entries
            if use_cache and self.cache and new_entries:
                self.cache.set_many(new_entries)
                logger.info(f"Bulk cached {len(new_entries)} new entries")

        # Fill in None for any missing
        for celex in celex_list:
            if celex not in results:
                results[celex] = None

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get Redis cache statistics.

        Returns:
            Dictionary with cache performance metrics
        """
        if not self.cache:
            return {"enabled": False}

        stats = self.cache.get_stats()
        stats["enabled"] = True
        return stats

    def clear_cache(self) -> int:
        """
        Clear all cached CELEX entries.

        Returns:
            Number of entries cleared
        """
        if not self.cache:
            return 0
        return self.cache.clear_all()

    def close(self):
        """Close the HTTP client and cache connection."""
        self.client.close()
        if self.cache:
            self.cache.close()
