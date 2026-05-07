from __future__ import annotations

import hashlib
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
from urllib.parse import urlparse

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
        response = _get_adzuna_with_retries(
            country=country,
            app_id=app_id,
            app_key=app_key,
            query=query,
            where=where,
            results_per_query=results_per_query,
        )
        if response is None:
            continue
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


def fetch_reed_jobs(
    queries: list[str],
    location: str = "United Kingdom",
    results_per_query: int = 20,
) -> list[dict[str, str]]:
    api_key = os.getenv("REED_API_KEY")
    if not api_key:
        return []

    jobs = []
    for query in queries:
        response = _get_reed_with_retries(
            api_key=api_key,
            query=query,
            location=location,
            results_per_query=results_per_query,
        )
        if response is None:
            continue
        for item in response.json().get("results", []):
            company = item.get("employerName", "")
            title = item.get("jobTitle", "")
            url = item.get("jobUrl", "")
            location_name = item.get("locationName", "")
            description = _clean(item.get("jobDescription", ""))
            jobs.append(
                {
                    "job_id": stable_job_id(company, title, url),
                    "title": title,
                    "company": company,
                    "location": location_name,
                    "remote": "remote" if "remote" in (title + " " + description).lower() else "",
                    "salary": _reed_salary_text(item),
                    "url": url,
                    "date_posted": item.get("date", ""),
                    "found_at": datetime.now(timezone.utc).isoformat(),
                    "source": f"reed:{query}",
                    "raw_description": description[:8000],
                }
            )
    return jobs


def fetch_google_search_jobs(
    queries: list[str],
    sites: list[str],
    results_per_site: int = 3,
) -> list[dict[str, str]]:
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not search_engine_id:
        return []

    jobs = []
    for site in sites:
        for query in queries:
            response = _get_google_search_with_retries(
                api_key=api_key,
                search_engine_id=search_engine_id,
                query=query,
                site=site,
                results_per_site=results_per_site,
            )
            if response is None:
                continue
            for item in response.json().get("items", []):
                title = _clean(item.get("title", ""))
                url = item.get("link", "")
                snippet = _clean(item.get("snippet", ""))
                company = _company_from_search_result(item, site)
                jobs.append(
                    {
                        "job_id": stable_job_id(company, title, url),
                        "title": title,
                        "company": company,
                        "location": "",
                        "remote": "remote" if "remote" in (title + " " + snippet).lower() else "",
                        "salary": "",
                        "url": url,
                        "date_posted": "",
                        "found_at": datetime.now(timezone.utc).isoformat(),
                        "source": f"google_search:{site}:{query}",
                        "raw_description": snippet[:8000],
                    }
                )
    return jobs


def _get_adzuna_with_retries(
    country: str,
    app_id: str,
    app_key: str,
    query: str,
    where: str,
    results_per_query: int,
) -> httpx.Response | None:
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": query,
        "where": where,
        "results_per_page": results_per_query,
        "sort_by": "date",
        "content-type": "application/json",
    }
    for attempt in range(3):
        try:
            response = httpx.get(
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {429, 500, 502, 503, 504}:
                raise
        except httpx.HTTPError:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def _get_reed_with_retries(
    api_key: str,
    query: str,
    location: str,
    results_per_query: int,
) -> httpx.Response | None:
    params = {
        "keywords": query,
        "locationName": location,
        "resultsToTake": min(results_per_query, 100),
        "postedByDirectEmployer": "false",
    }
    for attempt in range(3):
        try:
            response = httpx.get(
                "https://www.reed.co.uk/api/1.0/search",
                params=params,
                auth=(api_key, ""),
                timeout=30,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {429, 500, 502, 503, 504}:
                raise
        except httpx.HTTPError:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def _get_google_search_with_retries(
    api_key: str,
    search_engine_id: str,
    query: str,
    site: str,
    results_per_site: int,
) -> httpx.Response | None:
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": f'{query} site:{site} ("deadline" OR "apply" OR "job" OR "vacancy")',
        "num": max(1, min(results_per_site, 10)),
    }
    for attempt in range(3):
        try:
            response = httpx.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {429, 500, 502, 503, 504}:
                print(
                    "Google search source skipped "
                    f"for {site} / {query}: HTTP {exc.response.status_code}"
                )
                return None
        except httpx.HTTPError:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def _looks_like_job(text: str) -> bool:
    lowered = text.lower()
    job_terms = [
        "paralegal",
        "solicitor",
        "trainee solicitor",
        "caseworker",
        "legal",
        "law",
        "training contract",
        "sqe",
        "vacation scheme",
        "graduate",
        "associate",
        "immigration",
        "housing",
        "employment",
        "private client",
        "wills",
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


def _reed_salary_text(item: dict) -> str:
    salary_min = _number_or_none(item.get("minimumSalary"))
    salary_max = _number_or_none(item.get("maximumSalary"))
    currency = item.get("currency") or "GBP"
    if salary_min and salary_max:
        return f"{currency} {salary_min:,.0f} - {salary_max:,.0f}"
    if salary_min:
        return f"{currency} {salary_min:,.0f}+"
    if salary_max:
        return f"Up to {currency} {salary_max:,.0f}"
    return ""


def _number_or_none(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _company_from_search_result(item: dict, fallback_site: str) -> str:
    pagemap = item.get("pagemap") or {}
    metatags = pagemap.get("metatags") or []
    if metatags:
        site_name = metatags[0].get("og:site_name") or metatags[0].get("application-name")
        if site_name:
            return _clean(site_name)
    display_link = item.get("displayLink") or urlparse(item.get("link", "")).netloc
    return _clean(display_link or fallback_site)
