"""Wissensquellen fuer das Selbst-Update nach dem "Vordenker".

Das System haelt sein Wissen ueber Ben Goertzels aktuelle Arbeit selbst
aktuell: arXiv-API (neue Papers) und Substack-RSS (neue Essays). Beides
nur Python-Stdlib (urllib + xml.etree), mit hartem Timeout und sauberem
Verhalten ohne Netz: dann liefern die Quellen einfach nichts.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Protocol

FETCH_TIMEOUT = 15  # Sekunden
USER_AGENT = "goertzel-agi-selfupdate/0.1 (research prototype)"

ATOM_NS = "{http://www.w3.org/2005/Atom}"


@dataclass(frozen=True)
class Finding:
    """Ein gefundenes Werk des Vordenkers."""

    source: str   # "arxiv" | "substack" | ...
    uid: str      # stabile ID (arXiv-ID, Artikel-URL)
    title: str
    summary: str
    url: str
    published: str  # ISO-Datum, soweit verfuegbar


class KnowledgeSource(Protocol):
    name: str

    def fetch(self) -> List[Finding]: ...


def _http_get(url: str) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


class ArxivGoertzelSource:
    """Neueste arXiv-Eintraege mit Autor Goertzel (export.arxiv.org-API)."""

    name = "arxiv"

    def __init__(self, max_results: int = 15):
        self.max_results = max_results

    def fetch(self) -> List[Finding]:
        query = urllib.parse.urlencode({
            "search_query": 'au:"Goertzel"',
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(self.max_results),
        })
        raw = _http_get(f"https://export.arxiv.org/api/query?{query}")
        if raw is None:
            return []
        try:
            feed = ET.fromstring(raw)
        except ET.ParseError:
            return []
        findings = []
        for entry in feed.findall(f"{ATOM_NS}entry"):
            uid = (entry.findtext(f"{ATOM_NS}id") or "").strip()
            findings.append(Finding(
                source=self.name,
                uid=uid,
                title=" ".join((entry.findtext(f"{ATOM_NS}title") or "").split()),
                summary=" ".join((entry.findtext(f"{ATOM_NS}summary") or "").split())[:500],
                url=uid,
                published=(entry.findtext(f"{ATOM_NS}published") or "").strip(),
            ))
        return findings


class SubstackSource:
    """RSS-Feed von bengoertzel.substack.com."""

    name = "substack"

    def __init__(self, feed_url: str = "https://bengoertzel.substack.com/feed"):
        self.feed_url = feed_url

    def fetch(self) -> List[Finding]:
        raw = _http_get(self.feed_url)
        if raw is None:
            return []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []
        findings = []
        for item in root.iter("item"):
            link = (item.findtext("link") or "").strip()
            findings.append(Finding(
                source=self.name,
                uid=link,
                title=" ".join((item.findtext("title") or "").split()),
                summary=" ".join((item.findtext("description") or "").split())[:500],
                url=link,
                published=(item.findtext("pubDate") or "").strip(),
            ))
        return findings


def default_sources() -> List[KnowledgeSource]:
    return [ArxivGoertzelSource(), SubstackSource()]
