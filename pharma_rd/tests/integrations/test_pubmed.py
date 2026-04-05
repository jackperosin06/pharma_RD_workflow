"""PubMed integration helpers (no live network)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pharma_rd.config import get_settings
from pharma_rd.http_client import ConnectorFailure
from pharma_rd.integrations.pubmed import (
    build_pubmed_query,
    parse_pubmed_efetch_xml,
    pubmed_search_pmids,
)


def test_build_pubmed_query_or_joins_labels() -> None:
    q = build_pubmed_query(["diabetes", "asthma"])
    assert "[Title/Abstract]" in q
    assert " OR " in q
    assert "diabetes" in q
    assert "asthma" in q
    assert "Clinical Trial[Publication Type]" in q


def test_build_pubmed_query_empty() -> None:
    assert build_pubmed_query([]) == ""


def test_parse_pubmed_efetch_xml_minimal() -> None:
    xml = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE">
      <PMID Version="1">12345678</PMID>
      <Article>
        <ArticleTitle>Example trial publication</ArticleTitle>
        <Abstract>
          <AbstractText>This is a short abstract for testing.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""
    items, gaps = parse_pubmed_efetch_xml(xml)
    assert len(items) == 1
    assert items[0].title == "Example trial publication"
    assert "abstract" in items[0].summary.lower()
    assert items[0].reference == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    assert items[0].source == "pubmed"
    assert not gaps


def test_parse_pubmed_efetch_xml_no_abstract() -> None:
    xml = """
<PubmedArticleSet><PubmedArticle>
  <MedlineCitation><PMID Version="1">1</PMID>
    <Article><ArticleTitle>Title only</ArticleTitle></Article>
  </MedlineCitation>
</PubmedArticle></PubmedArticleSet>
"""
    items, gaps = parse_pubmed_efetch_xml(xml)
    assert len(items) == 1
    assert "Abstract not available" in items[0].summary
    assert any("abstract missing" in g.lower() for g in gaps)


def test_parse_pubmed_efetch_xml_malformed() -> None:
    items, gaps = parse_pubmed_efetch_xml("not xml")
    assert items == []
    assert gaps and "parse failed" in gaps[0].lower()


def test_parse_pubmed_efetch_xml_truncation_gap() -> None:
    long_abs = "x" * 900
    xml = f"""<?xml version="1.0"?>
<PubmedArticleSet><PubmedArticle>
  <MedlineCitation><PMID Version="1">9</PMID>
    <Article><ArticleTitle>T</ArticleTitle>
      <Abstract><AbstractText>{long_abs}</AbstractText></Abstract>
    </Article>
  </MedlineCitation>
</PubmedArticle></PubmedArticleSet>
"""
    items, gaps = parse_pubmed_efetch_xml(xml)
    assert len(items) == 1
    assert len(items[0].summary) <= 803
    assert any("truncated" in g.lower() for g in gaps)


def test_pubmed_search_pmids_esearch_error_raises() -> None:
    get_settings.cache_clear()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"esearchresult": {"ERROR": "Invalid search"}}
    with patch(
        "pharma_rd.integrations.pubmed.request_with_retries",
        return_value=mock_resp,
    ):
        with pytest.raises(ConnectorFailure, match="PubMed esearch error"):
            pubmed_search_pmids(query="test")


def test_pubmed_search_pmids_non_json_raises() -> None:
    get_settings.cache_clear()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
    with patch(
        "pharma_rd.integrations.pubmed.request_with_retries",
        return_value=mock_resp,
    ):
        with pytest.raises(ConnectorFailure, match="non-JSON"):
            pubmed_search_pmids(query="test")
