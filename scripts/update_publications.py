#!/usr/bin/env python3
"""Fetch publications from Semantic Scholar and write publications.json.

Semantic Scholar is used instead of Google Scholar because GitHub Actions
IP ranges are blocked by Google Scholar's anti-bot systems.

Papers not indexed by Semantic Scholar (e.g. industry conference papers)
can be kept by adding them to the MANUAL_PAPERS list below.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
PAPER_FIELDS = "title,authors,venue,year,externalIds,publicationVenue"
USER_AGENT = "portfolio-publications-updater/2.0 (github.com/EngEmmanuel/engemmanuel.github.io)"

# Papers not indexed by Semantic Scholar — add any missing ones here.
MANUAL_PAPERS: list[dict[str, Any]] = [
    {
        "title": "Machine-learning informed prediction of linear solver tolerance for non-linear solution methods in numerical simulation",
        "authors": "E Oladokun, S Sheth, T Jönsthövel, K Neylon",
        "venue": "ECMOR XVII",
        "year": 2021,
        "url": "https://scholar.google.com/citations?view_op=view_citation&hl=en&user=X8GzMrEAAAAJ&pagesize=100&citation_for_view=X8GzMrEAAAAJ:u5HHmVD_uO8C",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-id", default="2299780720", help="Semantic Scholar author ID")
    parser.add_argument("--output", default="publications.json", help="Output JSON file path")
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Pause between requests")
    return parser.parse_args()


def fetch_papers(author_id: str, sleep_seconds: float) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    papers: list[dict[str, Any]] = []
    limit = 100
    offset = 0

    while True:
        url = f"{SEMANTIC_SCHOLAR_API}/author/{author_id}/papers"
        resp = session.get(url, params={"fields": PAPER_FIELDS, "limit": limit, "offset": offset}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        batch = data.get("data", [])
        papers.extend(batch)

        if len(batch) < limit:
            break
        offset += limit
        time.sleep(sleep_seconds)

    return papers


def format_paper(raw: dict[str, Any]) -> dict[str, Any]:
    authors = ", ".join(a["name"] for a in raw.get("authors", []))

    venue = raw.get("venue") or ""
    pub_venue = raw.get("publicationVenue") or {}
    if pub_venue.get("name"):
        venue = pub_venue["name"]

    external_ids = raw.get("externalIds") or {}
    url = ""
    if external_ids.get("ArXiv"):
        url = f"https://arxiv.org/abs/{external_ids['ArXiv']}"
    elif external_ids.get("DOI"):
        url = f"https://doi.org/{external_ids['DOI']}"

    return {
        "title": raw.get("title", ""),
        "authors": authors,
        "venue": venue,
        "year": raw.get("year"),
        "url": url,
    }


def merge_papers(fetched: list[dict[str, Any]], manual: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def normalise(title: str) -> str:
        return title.lower().strip()

    seen = {normalise(p["title"]) for p in fetched}
    merged = list(fetched)
    for paper in manual:
        if normalise(paper["title"]) not in seen:
            merged.append(paper)
            seen.add(normalise(paper["title"]))

    merged.sort(key=lambda p: (p.get("year") or 0, p.get("title") or ""), reverse=True)
    return merged


def write_output(output_path: Path, author_id: str, papers: list[dict[str, Any]]) -> None:
    output = {
        "source": {
            "name": "Semantic Scholar",
            "profile": f"https://www.semanticscholar.org/author/{author_id}",
            "author_id": author_id,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(papers),
        "publications": papers,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)

    print(f"Fetching papers for Semantic Scholar author {args.author_id}...")
    raw_papers = fetch_papers(author_id=args.author_id, sleep_seconds=args.sleep_seconds)
    print(f"Fetched {len(raw_papers)} papers from Semantic Scholar.")

    fetched = [format_paper(p) for p in raw_papers]
    merged = merge_papers(fetched, MANUAL_PAPERS)
    print(f"Total after merging manual entries: {len(merged)}")

    write_output(output_path=output_path, author_id=args.author_id, papers=merged)
    print(f"Wrote {len(merged)} publications to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
