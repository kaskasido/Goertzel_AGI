"""Denker-Quellen: Podcasts, Talks und Papers grosser Theoretiker.

Standardquellen (alle ueber offizielle, oeffentliche Feeds — keine Scraper):
  - Lex Fridman Podcast  (RSS, lexfridman.com — Interviews mit Forschern)
  - TED Talks Daily      (RSS — Talks inkl. TEDx-Auswahl)
  - David Deutsch        (arXiv-Autorensuche — Constructor Theory etc.)

Eigene Denker hinzufuegen — auch "unbekannte tiefgreifende Theoretiker":
einfach data/denker_feeds.json anlegen/erweitern:

    [
      {"name": "sean_carroll", "kind": "rss",
       "url": "https://rss.art19.com/sean-carrolls-mindscape"},
      {"name": "stephen_wolfram", "kind": "arxiv",
       "query": "au:\"Stephen Wolfram\""}
    ]

Bewusste Grenze: Die Joe Rogan Experience hat keinen oeffentlichen
RSS-/Transkript-Feed (Spotify-Vertrieb). Wer sie einspeisen will, kann
Transkripte manuell als Saetze ueber die UI eingeben oder lokal mit
yt-dlp Untertitel ziehen und per kernel.tell() fuettern.
"""

from __future__ import annotations

import json
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .sources import ATOM_NS, Finding, KnowledgeSource, _http_get


class RssFeedSource:
    """Generische RSS-Quelle (Podcast-/Talk-Feeds)."""

    def __init__(self, name: str, url: str, max_items: int = 20):
        self.name = name
        self.url = url
        self.max_items = max_items

    def fetch(self) -> List[Finding]:
        raw = _http_get(self.url)
        if raw is None:
            return []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []
        findings = []
        for item in list(root.iter("item"))[: self.max_items]:
            link = (item.findtext("link") or "").strip()
            title = " ".join((item.findtext("title") or "").split())
            if not (link or title):
                continue
            findings.append(Finding(
                source=self.name,
                uid=link or f"{self.name}:{title}",
                title=title,
                summary=" ".join((item.findtext("description") or "").split())[:1500],
                url=link,
                published=(item.findtext("pubDate") or "").strip(),
            ))
        return findings


class ArxivAuthorSource:
    """arXiv-Suche fuer beliebige Autoren/Themen (query in arXiv-Syntax)."""

    def __init__(self, name: str, query: str, max_results: int = 10):
        self.name = name
        self.query = query
        self.max_results = max_results

    def fetch(self) -> List[Finding]:
        params = urllib.parse.urlencode({
            "search_query": self.query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(self.max_results),
        })
        raw = _http_get(f"https://export.arxiv.org/api/query?{params}")
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
                summary=" ".join((entry.findtext(f"{ATOM_NS}summary") or "").split())[:1500],
                url=uid,
                published=(entry.findtext(f"{ATOM_NS}published") or "").strip(),
            ))
        return findings


DEFAULT_FEEDS = [
    {"name": "lex_fridman", "kind": "rss",
     "url": "https://lexfridman.com/feed/podcast/"},
    {"name": "ted_talks", "kind": "rss",
     "url": "https://feeds.feedburner.com/TEDTalks_audio"},
    {"name": "david_deutsch", "kind": "arxiv",
     "query": 'au:"David Deutsch" AND cat:quant-ph'},
]


def load_thinker_sources(config_file: str | Path = "data/denker_feeds.json"
                         ) -> List[KnowledgeSource]:
    """Laedt Quellen aus der Konfigdatei; fehlt sie, gelten die Defaults."""
    path = Path(config_file)
    specs = DEFAULT_FEEDS
    if path.exists():
        try:
            specs = DEFAULT_FEEDS + json.loads(path.read_text())
        except ValueError:
            pass  # kaputte Konfig ignorieren, Defaults behalten
    sources: List[KnowledgeSource] = []
    for spec in specs:
        if spec.get("kind") == "rss" and spec.get("url"):
            sources.append(RssFeedSource(spec["name"], spec["url"]))
        elif spec.get("kind") == "arxiv" and spec.get("query"):
            sources.append(ArxivAuthorSource(spec["name"], spec["query"]))
    return sources
