#!/usr/bin/env python3
"""Coupang job crawler — fetches postings from Greenhouse board API and writes to Google Sheets."""

from datetime import datetime

import requests

from base import CrawlerConfig, format_date_iso, run_crawler

CONFIG = CrawlerConfig(
    company_name="쿠팡",
    sheet_name="쿠팡",
    spreadsheet_env_var="COUPANG_SPREADSHEET_ID",
    job_id_field="id",
)

API_URL = "https://api.greenhouse.io/v1/boards/coupang/jobs"

TARGET_LOCATION = "Seoul"
# Greenhouse has no job-category codes, so we filter by Korean keyword in title
TARGET_KEYWORD = "기획"


def fetch_all_jobs() -> list[dict]:
    """Fetch all Coupang jobs from the Greenhouse public board API (single request)."""
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    jobs = data.get("jobs", [])
    print(f"총 {len(jobs)}건의 채용 공고 조회")
    return jobs


def filter_jobs(jobs: list[dict]) -> list[dict]:
    """Keep only Seoul-based jobs with '기획' in the title.

    Greenhouse board API lacks structured category codes, so keyword matching
    on the title is the only way to approximate a 기획 (planning) filter.
    """
    filtered = []
    for job in jobs:
        location = job.get("location", {}).get("name", "")
        title = job.get("title", "")

        if TARGET_LOCATION in location and TARGET_KEYWORD in title:
            filtered.append(job)

    print(f"필터링 후 {len(filtered)}건 ({TARGET_LOCATION} + '{TARGET_KEYWORD}')")
    return filtered


def job_to_row(job: dict) -> list[str]:
    """Convert a Greenhouse job dict to a 10-column spreadsheet row.

    Company name, employment type, and closing date are hardcoded because
    the Greenhouse public board API does not expose these fields.
    """
    job_id = str(job.get("id", ""))
    departments = job.get("departments", [])
    dept_name = departments[0].get("name", "") if departments else ""

    return [
        "쿠팡",       # Greenhouse API에 회사명 필드 없음
        job.get("title", ""),
        format_date_iso(job.get("first_published")),
        "상시채용",    # Greenhouse API에 마감일 필드 없음
        job.get("absolute_url", ""),
        dept_name,
        job.get("location", {}).get("name", ""),
        "정규직",      # Greenhouse API에 고용형태 필드 없음
        job_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row, filter_fn=filter_jobs)
