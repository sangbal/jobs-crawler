#!/usr/bin/env python3
"""토스 채용 정보 크롤러 - Google Sheets 자동 적재"""

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
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get("resultType") != "SUCCESS":
        raise ValueError(f"API 요청 실패: {data.get('error')}")

    jobs = data.get("success", [])
    print(f"총 {len(jobs)}건의 채용 공고 조회")
    return jobs


def get_metadata_value(job: dict, field_name: str) -> str | None:
    for meta in job.get("metadata", []):
        if field_name in meta.get("name", ""):
            return meta.get("value")
    return None


def filter_jobs(jobs: list[dict]) -> list[dict]:
    filtered = []
    for job in jobs:
        employment_type = get_metadata_value(job, "Employment_Type")
        job_category = get_metadata_value(job, "Job Category")

        if employment_type == TARGET_EMPLOYMENT_TYPE and job_category in TARGET_JOB_CATEGORIES:
            filtered.append(job)

    print(f"필터링 후 {len(filtered)}건 (정규직 + {TARGET_JOB_CATEGORIES})")
    return filtered


def job_to_row(job: dict) -> list[str]:
    closing_date = get_metadata_value(job, "클로징 일자")
    subsidiary = get_metadata_value(job, "소속 자회사")

    return [
        str(job.get("id", "")),
        job.get("title", ""),
        subsidiary or job.get("company_name", ""),
        get_metadata_value(job, "Job Category") or "",
        job.get("location", {}).get("name", ""),
        get_metadata_value(job, "Employment_Type") or "",
        format_date_iso(job.get("first_published")),
        format_date_iso(closing_date) if closing_date else "상시채용",
        job.get("absolute_url", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row, filter_fn=filter_jobs)
