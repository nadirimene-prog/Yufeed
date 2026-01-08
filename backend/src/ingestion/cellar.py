import httpx
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class CellarClient:
    """
    Client for querying the EU Cellar (Publications Office) SPARQL endpoint.
    Cellar is the content repository of the EU Publications Office containing
    metadata and full-text content of EU legal documents.
    """

    SPARQL_ENDPOINT = "http://publications.europa.eu/webapi/rdf/sparql"
    BASE_URL = "http://publications.europa.eu/resource/cellar"

    def __init__(self):
        self.client = httpx.Client(timeout=60.0)

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
        pattern = r'^[0-9]{1,5}[A-Z]{1,3}[0-9]{1,6}[A-Z0-9]*$'
        return re.match(pattern, celex) is not None

    @staticmethod
    def _sanitize_celex(celex: str) -> str:
        """
        Sanitize CELEX input by escaping special characters.
        """
        # Only allow alphanumeric characters
        return re.sub(r'[^A-Z0-9]', '', celex.upper())

    def query_by_celex(self, celex: str) -> Optional[Dict[str, Any]]:
        """
        Query Cellar using CELEX to get enriched metadata.
        Returns structured metadata or None if not found.

        Security: Validates and sanitizes CELEX to prevent SPARQL injection.
        """
        if not celex:
            return None

        # Validate CELEX format
        if not self._validate_celex(celex):
            logger.warning(f"Invalid CELEX format rejected: {celex}")
            return None

        # Sanitize input as additional security layer
        safe_celex = self._sanitize_celex(celex)

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
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", {}).get("bindings", [])

            if not results:
                logger.warning(f"No Cellar data found for CELEX: {celex}")
                return None

            return self._parse_sparql_result(results[0], celex)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error querying Cellar for {celex}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error querying Cellar for {celex}: {e}")
            return None

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
                return datetime.fromisoformat(date_str.split('T')[0])
            except (ValueError, AttributeError):
                return None

        metadata = {
            "celex": celex,
            "cellar_id": get_value("cellarId"),
            "eli": get_value("eli"),
            "title": get_value("title"),
            "work_type": get_value("workType"),
            "date_document": parse_date(get_value("dateDocument")),
            "date_entry_into_force": parse_date(get_value("dateEntryIntoForce")),
            "subject": get_value("subject"),
            "directory_code": get_value("directoryCode"),
            "work_uri": get_value("work")
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
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            manifestations = []
            for binding in bindings:
                manifestations.append({
                    "format": binding.get("format", {}).get("value", "").split("/")[-1],
                    "url": binding.get("url", {}).get("value")
                })

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
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            relations = []
            for binding in bindings:
                relation_type = binding.get("relationType", {}).get("value", "").split("#")[-1]
                relations.append({
                    "related_celex": binding.get("relatedCelex", {}).get("value"),
                    "relation_type": relation_type,
                    "related_work_uri": binding.get("relatedWork", {}).get("value")
                })

            logger.info(f"Found {len(relations)} related documents for {cellar_id}")
            return relations

        except Exception as e:
            logger.error(f"Error fetching related documents for {cellar_id}: {e}")
            return []

    def close(self):
        """Close the HTTP client."""
        self.client.close()
