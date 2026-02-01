import pytest
from types import SimpleNamespace

from src.ingestion.rss import RSSFetcher
import src.ingestion.rss as rss_module


@pytest.mark.unit
def test_rss_extract_helpers():
    fetcher = RSSFetcher()
    assert fetcher._extract_celex("CELEX:32020R0001") == "32020R0001"
    assert fetcher._extract_eli("https://data.europa.eu/eli/reg/2020/1")
    assert fetcher._extract_oj_reference("Official Journal L 1")
    assert fetcher._extract_oj_series("OJ L 1") == "L"


@pytest.mark.unit
def test_rss_fallback_parser():
    fetcher = RSSFetcher()
    content = """
    <rss><channel>
      <item>
        <title>Test Doc</title>
        <link>https://eur-lex.europa.eu/?uri=CELEX:32020R0002</link>
        <description>Desc</description>
        <pubDate>2024-01-01</pubDate>
      </item>
    </channel></rss>
    """
    entries = fetcher._parse_rss_fallback(content, language="en")
    assert entries
    assert entries[0]["celex"] == "32020R0002"


@pytest.mark.unit
def test_parse_cellar_ingestion_feed():
    fetcher = RSSFetcher()
    xml = """
    <rss><channel>
      <item>
        <title>OJ L 1</title>
        <link>https://eur-lex.europa.eu/?uri=CELEX:32020R0003</link>
        <description>OJ L 1</description>
        <pubDate>2024-01-02</pubDate>
      </item>
    </channel></rss>
    """
    entries = fetcher._parse_cellar_ingestion_feed(xml, language="en")
    assert entries
    assert entries[0]["celex"] == "32020R0003"


@pytest.mark.unit
def test_fetch_cellar_ingestion(monkeypatch):
    fetcher = RSSFetcher()

    class DummyResponse:
        def __init__(self, text):
            self.text = text

    xml = """
    <rss><channel>
      <item>
        <title>OJ L 2</title>
        <link>https://eur-lex.europa.eu/?uri=CELEX:32020R0004</link>
        <description>OJ L 2</description>
        <pubDate>2024-01-03</pubDate>
      </item>
    </channel></rss>
    """

    monkeypatch.setattr(rss_module, "_retry_request", lambda *args, **kwargs: DummyResponse(xml))

    entries = fetcher.fetch_cellar_ingestion(language="en")
    assert entries
