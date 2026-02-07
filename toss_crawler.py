#!/usr/bin/env python3
"""Toss job crawler — fetches postings from toss.im career API and writes to Google Sheets."""

from datetime import datetime

import requests

from base import CrawlerConfig, format_date_iso, run_crawler

CONFIG = CrawlerConfig(
    company_name="토스",
    sheet_name="토스",
    spreadsheet_env_var="TOSS_SPREADSHEET_ID",
    job_id_field="id",
)

API_URL = "https://api-public.toss.im/api/v3/ipd-eggnog/career/jobs"

TARGET_EMPLOYMENT_TYPE = "정규직"
TARGET_JOB_CATEGORIES = {"Sales", "Sales Support"}


def fetch_all_jobs() -> list[dict]:
    """Fetch all job postings in a single request (no pagination).

    The Toss API returns all jobs at once; pagination is not supported.
    """
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get("resultType") != "SUCCESS":
        raise ValueError(f"API 요청 실패: {data.get('error')}")

    jobs = data.get("success", [])
    print(f"총 {len(jobs)}건의 채용 공고 조회")
    return jobs


def get_metadata_value(job: dict, field_name: str) -> str | None:
    """Extract a value from the job's metadata list by partial name match.

    Toss metadata names are verbose and occasionally change
    (e.g. "Employment_Type_경력/신입" vs "Employment_Type"). Substring matching
    ('field_name in name') avoids breakage when suffixes change, at the cost of
    potential false matches — acceptable given the small, known set of field names.
    """
    for meta in job.get("metadata", []):
        if field_name in meta.get("name", ""):
            return meta.get("value")
    return None


def filter_jobs(jobs: list[dict]) -> list[dict]:
    """Keep only 정규직 postings in Sales / Sales Support categories."""
    filtered = []
    for job in jobs:
        employment_type = get_metadata_value(job, "Employment_Type")
        job_category = get_metadata_value(job, "Job Category")

        if employment_type == TARGET_EMPLOYMENT_TYPE and job_category in TARGET_JOB_CATEGORIES:
            filtered.append(job)

    print(f"필터링 후 {len(filtered)}건 (정규직 + {TARGET_JOB_CATEGORIES})")
    return filtered


def job_to_row(job: dict) -> list[str]:
    """Convert a Toss job dict to a 10-column spreadsheet row.

    Uses '소속 자회사' (subsidiary) for company name when available,
    since Toss has multiple subsidiaries (토스뱅크, 토스증권, etc.)
    and the subsidiary is more informative than the parent company name.
    """
    closing_date = get_metadata_value(job, "클로징 일자")
    subsidiary = get_metadata_value(job, "소속 자회사")

    return [
        subsidiary or job.get("company_name", ""),
        job.get("title", ""),
        format_date_iso(job.get("first_published")),
        format_date_iso(closing_date) if closing_date else "상시채용",
        job.get("absolute_url", ""),
        get_metadata_value(job, "Job Category") or "",
        job.get("location", {}).get("name", ""),
        get_metadata_value(job, "Employment_Type") or "",
        str(job.get("id", "")),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row, filter_fn=filter_jobs)
