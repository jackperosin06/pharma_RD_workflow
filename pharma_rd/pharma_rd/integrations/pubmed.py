"""PubMed E-utilities client — esearch + efetch (FR6, NFR-I1)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import httpx

from pharma_rd.config import Settings, get_settings
from pharma_rd.http_client import (
    ConnectorFailure,
    IntegrationErrorClass,
    request_with_retries,
)
from pharma_rd.pipeline.contracts import PublicationItem

_TRIAL_PUBLICATION_FILTER = "Clinical Trial[Publication Type]"


def build_pubmed_query(labels: list[str]) -> str:
    """Build PubMed query: TA terms (OR) AND clinical trial publication type."""
    parts: list[str] = []
    for label in labels:
        clean = label.strip()
        if not clean:
            continue
        escaped = clean.replace('"', r"\"")
        parts.append(f'"{escaped}"[Title/Abstract]')
    if not parts:
        return ""
    ta_or = " OR ".join(parts)
    return f"({ta_or}) AND {_TRIAL_PUBLICATION_FILTER}"


def _strip_tag(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _find_first_desc_text(parent: ET.Element, local_name: str) -> str | None:
    for el in parent.iter():
        if _strip_tag(el.tag) == local_name and el.text and el.text.strip():
            return el.text.strip()
    return None


def _collect_abstract_text(article: ET.Element) -> str:
    chunks: list[str] = []
    for el in article.iter():
        if _strip_tag(el.tag) != "AbstractText":
            continue
        label = el.get("Label")
        piece = (el.text or "").strip()
        if not piece:
            continue
        if label:
            chunks.append(f"{label}: {piece}")
        else:
            chunks.append(piece)
    return " ".join(chunks).strip()


def parse_pubmed_efetch_xml(xml_text: str) -> tuple[list[PublicationItem], list[str]]:
    """Parse efetch XML into publication items.

    Second list is parse warnings (NFR-I1).
    """
    gaps: list[str] = []
    items: list[PublicationItem] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return [], [f"PubMed XML parse failed: {e}"]

    for article in root.iter():
        if _strip_tag(article.tag) != "PubmedArticle":
            continue
        pmid = _find_first_desc_text(article, "PMID")
        title = _find_first_desc_text(article, "ArticleTitle") or "(no title)"
        abstract = _collect_abstract_text(article)
        if not pmid:
            gaps.append("Skipped one PubmedArticle with no PMID in parsed XML.")
            continue
        ref = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        if not abstract:
            abstract = "Abstract not available in this PubMed record."
            gaps.append(f"PMID {pmid}: abstract missing; using title-only context.")
        truncated = len(abstract) > 800
        summary = abstract if not truncated else abstract[:797] + "..."
        if truncated:
            gaps.append(f"PMID {pmid}: summary truncated to 800 characters.")
        items.append(
            PublicationItem(
                title=title,
                summary=summary,
                reference=ref,
                source="pubmed",
            )
        )
    return items, gaps


def _eutils_common_params(settings: Settings) -> dict[str, str]:
    params: dict[str, str] = {"tool": settings.pubmed_tool_name}
    if settings.pubmed_tool_email:
        params["email"] = settings.pubmed_tool_email
    return params


def _parse_esearch_json_body(resp: httpx.Response) -> dict[str, object]:
    """Parse esearch JSON; raise ConnectorFailure on non-JSON bodies."""
    try:
        out = resp.json()
    except json.JSONDecodeError as e:
        ct = resp.headers.get("content-type", "")
        raise ConnectorFailure(
            f"PubMed esearch returned non-JSON (status {resp.status_code}, "
            f"content-type {ct!r})",
            error_class=IntegrationErrorClass.HTTP_CLIENT_ERROR,
        ) from e
    if not isinstance(out, dict):
        raise ConnectorFailure(
            f"PubMed esearch JSON root must be an object; got {type(out).__name__}",
            error_class=IntegrationErrorClass.HTTP_CLIENT_ERROR,
        )
    return out


def _esearch_error_message(res: dict[str, object]) -> str | None:
    err = res.get("ERROR")
    if err is None:
        return None
    if isinstance(err, list):
        return "; ".join(str(x) for x in err)
    return str(err)


def pubmed_search_pmids(
    *,
    query: str,
    settings: Settings | None = None,
    retmax: int | None = None,
) -> list[str]:
    """Run esearch.fcgi and return PubMed IDs (newest first)."""
    s = settings or get_settings()
    ret = retmax if retmax is not None else s.pubmed_max_results
    params: dict[str, str] = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": str(ret),
        "sort": "relevance",
    }
    params.update(_eutils_common_params(s))
    url = f"{s.pubmed_eutils_base.rstrip('/')}/esearch.fcgi?{urlencode(params)}"
    resp = request_with_retries("GET", url, stage_key="clinical")
    data = _parse_esearch_json_body(resp)
    res_raw = data.get("esearchresult")
    if res_raw is None:
        res: dict[str, object] = {}
        if "ERROR" in data:
            top = _esearch_error_message(data)
            if top:
                raise ConnectorFailure(
                    f"PubMed esearch error: {top}",
                    error_class=IntegrationErrorClass.HTTP_CLIENT_ERROR,
                )
    elif not isinstance(res_raw, dict):
        raise ConnectorFailure(
            f"PubMed esearchresult must be an object; got {type(res_raw).__name__}",
            error_class=IntegrationErrorClass.HTTP_CLIENT_ERROR,
        )
    else:
        res = res_raw
    emsg = _esearch_error_message(res)
    if emsg:
        raise ConnectorFailure(
            f"PubMed esearch error: {emsg}",
            error_class=IntegrationErrorClass.HTTP_CLIENT_ERROR,
        )
    raw = res.get("idlist") or []
    return [str(x) for x in raw]


def pubmed_fetch_records_xml(
    pmids: list[str],
    *,
    settings: Settings | None = None,
) -> str:
    """Run efetch.fcgi for PubMed XML."""
    s = settings or get_settings()
    params: dict[str, str] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    params.update(_eutils_common_params(s))
    url = f"{s.pubmed_eutils_base.rstrip('/')}/efetch.fcgi?{urlencode(params)}"
    resp = request_with_retries("GET", url, stage_key="clinical")
    return resp.text


def fetch_publications_for_labels(
    labels: list[str],
    *,
    settings: Settings | None = None,
) -> tuple[list[PublicationItem], list[str], list[str]]:
    """
    Full esearch → efetch → parse for configured TA labels.

    Returns (publication_items, integration_notes, data_gaps).
    Does not raise on empty search results — callers embed notes instead.
    """
    s = settings or get_settings()
    notes: list[str] = []
    gaps: list[str] = []
    query = build_pubmed_query(labels)
    if not query:
        return [], [], ["Empty PubMed query after mapping therapeutic area labels."]

    notes.append(f"PubMed query: {query}")

    pmids = pubmed_search_pmids(query=query, settings=s, retmax=s.pubmed_max_results)

    if not pmids:
        notes.append("No PubMed IDs returned for query (empty result set).")
        return [], notes, []

    xml_text = pubmed_fetch_records_xml(pmids, settings=s)

    items, parse_gaps = parse_pubmed_efetch_xml(xml_text)
    gaps.extend(parse_gaps)
    if not items and pmids:
        gaps.append(
            "efetch returned XML but no PubmedArticle entries were parsed "
            f"(requested pmids: {', '.join(pmids)})."
        )
    return items, notes, gaps
