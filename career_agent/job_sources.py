from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup


def stable_job_id(company: str, title: str, url: str) -> str:
    raw = f"{company}|{title}|{url}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch_rss_jobs(company: str, feed_url: str, keywords: str = "") -> list[dict[str, str]]:
    feed = feedparser.parse(feed_url)
    jobs = []
    for entry in feed.entries:
        title = _clean(getattr(entry, "title", ""))
        url = getattr(entry, "link", feed_url)
        description = _clean(getattr(entry, "summary", ""))
        if keywords and not _matches_keywords(title + " " + description, keywords):
            continue
        jobs.append(
            {
                "job_id": stable_job_id(company, title, url),
                "title": title,
                "company": company,
                "location": "",
                "remote": "",
                "salary": "",
                "url": url,
                "date_posted": getattr(entry, "published", ""),
                "found_at": datetime.now(timezone.utc).isoformat(),
                "source": "rss",
                "raw_description": description[:8000],
            }
        )
    return jobs


def fetch_career_page_jobs(company: str, careers_url: str, keywords: str = "") -> list[dict[str, str]]:
    response = httpx.get(careers_url, timeout=20, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for anchor in soup.find_all("a"):
        text = _clean(anchor.get_text(" "))
        href = anchor.get("href")
        if not href or len(text) < 4:
            continue
        combined = f"{text} {href}"
        if not _looks_like_job(combined):
            continue
        if keywords and not _matches_keywords(combined, keywords):
            continue
        links.append((text, urljoin(careers_url, href)))

    deduped = []
    seen = set()
    for title, url in links:
        key = (title.lower(), url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "job_id": stable_job_id(company, title, url),
                "title": title[:180],
                "company": company,
                "location": "",
                "remote": "unknown",
                "salary": "",
                "url": url,
                "date_posted": "",
                "found_at": datetime.now(timezone.utc).isoformat(),
                "source": "career_page",
                "raw_description": "",
            }
        )
    return deduped


def fetch_jobs_for_company(company_config: dict[str, str]) -> list[dict[str, str]]:
    company = company_config.get("company", "")
    url = company_config.get("careers_url", "")
    source_type = company_config.get("source_type", "career_page")
    keywords = company_config.get("keywords", "")
    if not company or not url:
        return []
    if source_type == "rss":
        return fetch_rss_jobs(company, url, keywords)
    return fetch_career_page_jobs(company, url, keywords)


def _looks_like_job(text: str) -> bool:
    lowered = text.lower()
    job_terms = [
        "engineer",
        "manager",
        "designer",
        "analyst",
        "specialist",
        "associate",
        "director",
        "lead",
        "sales",
        "success",
        "product",
        "marketing",
        "operations",
        "remote",
    ]
    return any(term in lowered for term in job_terms)


def _matches_keywords(text: str, keywords: str) -> bool:
    wanted = [item.strip().lower() for item in keywords.split(",") if item.strip()]
    if not wanted:
        return True
    lowered = text.lower()
    return any(keyword in lowered for keyword in wanted)
