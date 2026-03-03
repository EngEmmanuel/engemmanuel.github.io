#!/usr/bin/env python3
"""Fetch publications from a Google Scholar profile and write publications.json."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin

import requests

BASE_URL = "https://scholar.google.com/citations"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True, help="Google Scholar user id")
    parser.add_argument("--hl", default="en", help="Scholar language code")
    parser.add_argument(
        "--output",
        default="publications.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--pagesize",
        type=int,
        default=100,
        help="Rows to fetch per request (max 100)",
    )
    parser.add_argument(
        "--max-publications",
        type=int,
        default=300,
        help="Hard limit on number of publications to fetch",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.25,
        help="Pause between requests",
    )
    parser.add_argument(
        "--no-expand-venue",
        action="store_true",
        help="Skip per-publication detail fetch for full venue names",
    )
    return parser.parse_args()


def _request_page(session: requests.Session, user: str, hl: str, start: int, pagesize: int) -> str:
    params = {
        "user": user,
        "hl": hl,
        "cstart": start,
        "pagesize": min(max(pagesize, 1), 100),
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    text = response.text

    blocked_markers = [
        "Our systems have detected unusual traffic",
        "not a robot",
        "/sorry/",
        "recaptcha",
    ]
    if any(marker.lower() in text.lower() for marker in blocked_markers):
        raise RuntimeError("Google Scholar blocked the request (anti-bot challenge).")

    return text


def _request_url(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    text = response.text
    blocked_markers = [
        "Our systems have detected unusual traffic",
        "not a robot",
        "/sorry/",
        "recaptcha",
    ]
    if any(marker.lower() in text.lower() for marker in blocked_markers):
        raise RuntimeError("Google Scholar blocked the request (anti-bot challenge).")
    return text


def _extract_year(text: str) -> int | None:
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if not match:
        return None
    return int(match.group(0))


def _fetch_full_venue(session: requests.Session, publication_url: str) -> str | None:
    if not publication_url:
        return None

    bs4 = importlib.import_module("bs4")
    BeautifulSoup = bs4.BeautifulSoup

    try:
        html = _request_url(session, publication_url)
    except (requests.RequestException, RuntimeError):
        return None

    soup = BeautifulSoup(html, "html.parser")
    fields = soup.select("div.gsc_oci_field")
    values = soup.select("div.gsc_oci_value")

    venue_labels = {"journal", "conference", "book", "source"}
    for field, value in zip(fields, values):
        label = field.get_text(" ", strip=True).lower()
        if label in venue_labels:
            text = value.get_text(" ", strip=True)
            if text:
                return text

    return None


def _parse_rows(session: requests.Session, html: str, hl: str, expand_venue: bool, sleep_seconds: float) -> list[dict[str, Any]]:
    bs4 = importlib.import_module("bs4")
    BeautifulSoup = bs4.BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr.gsc_a_tr")
    publications: list[dict[str, Any]] = []

    for row in rows:
        title_link = row.select_one("a.gsc_a_at")
        title = (title_link.get_text(strip=True) if title_link else "").strip()
        if not title:
            continue

        gray_lines = row.select("td.gsc_a_t .gs_gray")
        authors = gray_lines[0].get_text(" ", strip=True) if len(gray_lines) > 0 else ""
        venue = gray_lines[1].get_text(" ", strip=True) if len(gray_lines) > 1 else ""

        year_text = ""
        year_el = row.select_one("td.gsc_a_y span")
        if year_el:
            year_text = year_el.get_text(strip=True)
        sort_year = int(year_text) if re.fullmatch(r"\d{4}", year_text) else _extract_year(venue)

        citation_path = title_link.get("href", "") if title_link else ""
        publication_url = ""
        if citation_path:
            publication_url = urljoin(
                "https://scholar.google.com",
                citation_path,
            )
            if "hl=" not in publication_url:
                joiner = "&" if "?" in publication_url else "?"
                publication_url = f"{publication_url}{joiner}hl={hl}"

        if expand_venue and publication_url:
            full_venue = _fetch_full_venue(session, publication_url)
            if full_venue:
                venue = full_venue
            time.sleep(max(sleep_seconds, 0.0))

        publications.append(
            {
                "title": title,
                "authors": authors,
                "venue": venue,
                "_sort_year": sort_year,
                "url": publication_url,
            }
        )

    return publications


def fetch_publications(user: str, hl: str, pagesize: int, max_publications: int, sleep_seconds: float, expand_venue: bool) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    all_publications: list[dict[str, Any]] = []
    start = 0

    while len(all_publications) < max_publications:
        html = _request_page(session, user=user, hl=hl, start=start, pagesize=pagesize)
        page_publications = _parse_rows(session, html, hl=hl, expand_venue=expand_venue, sleep_seconds=sleep_seconds)

        if not page_publications:
            break

        all_publications.extend(page_publications)
        if len(page_publications) < pagesize:
            break

        start += pagesize
        time.sleep(max(sleep_seconds, 0.0))

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pub in all_publications:
        key = f"{pub.get('title', '').strip().lower()}|{pub.get('_sort_year')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(pub)

    deduped.sort(key=lambda item: (item.get("_sort_year") or 0, item.get("title") or ""), reverse=True)
    for publication in deduped:
        publication.pop("_sort_year", None)
    return deduped[:max_publications]


def write_output(output_path: Path, user: str, hl: str, publications: list[dict[str, Any]]) -> None:
    output = {
        "source": {
            "name": "Google Scholar",
            "profile": f"{BASE_URL}?user={user}&hl={hl}",
            "user": user,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(publications),
        "publications": publications,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)

    publications = fetch_publications(
        user=args.user,
        hl=args.hl,
        pagesize=args.pagesize,
        max_publications=args.max_publications,
        sleep_seconds=args.sleep_seconds,
        expand_venue=not args.no_expand_venue,
    )

    if not publications:
        raise RuntimeError("No publications were fetched from Google Scholar.")

    write_output(output_path=output_path, user=args.user, hl=args.hl, publications=publications)
    print(f"Wrote {len(publications)} publications to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
