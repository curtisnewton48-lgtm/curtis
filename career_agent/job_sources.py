from __future__ import annotations

import hashlib
import os
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


def fetch_adzuna_jobs(
    queries: list[str],
    country: str = "gb",
    where: str = "United Kingdom",
    results_per_query: int = 25,
) -> list[dict[str, str]]:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []

    jobs = []
    for query in queries:
        response = httpx.get(
            f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
            params={
                "app_id": app_id,
                "app_key": app_key,
                "what": query,
                "where": where,
                "results_per_page": results_per_query,
                "sort_by": "date",
                "content-type": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        for item in response.json().get("results", []):
            company = item.get("company", {}).get("display_name", "")
            title = item.get("title", "")
            url = item.get("redirect_url", "")
            location = item.get("location", {}).get("display_name", "")
            salary = _salary_text(item)
            description = _clean(item.get("description", ""))
            jobs.append(
                {
                    "job_id": stable_job_id(company, title, url),
                    "title": title,
                    "company": company,
                    "location": location,
                    "remote": "remote" if "remote" in (title + " " + description).lower() else "",
                    "salary": salary,
                    "url": url,
                    "date_posted": item.get("created", ""),
                    "found_at": datetime.now(timezone.utc).isoformat(),
                    "source": f"adzuna:{query}",
                    "raw_description": description[:8000],
                }
            )
    return jobs


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
        "paralegal",
        "solicitor",
        "caseworker",
        "legal assistant",
        "law",
    ]
    return any(term in lowered for term in job_terms)


def _matches_keywords(text: str, keywords: str) -> bool:
    wanted = [item.strip().lower() for item in keywords.split(",") if item.strip()]
    if not wanted:
        return True
    lowered = text.lower()
    return any(keyword in lowered for keyword in wanted)


def _salary_text(item: dict) -> str:
    salary_min = item.get("salary_min")
    salary_max = item.get("salary_max")
    if salary_min and salary_max:
        return f"GBP {salary_min:,.0f} - {salary_max:,.0f}"
    if salary_min:
        return f"GBP {salary_min:,.0f}+"
    if salary_max:
        return f"Up to GBP {salary_max:,.0f}"
    return ""
