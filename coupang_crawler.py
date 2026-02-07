#!/usr/bin/env python3
"""쿠팡 채용 정보 크롤러 - Google Sheets 자동 적재"""

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
TARGET_KEYWORD = "기획"


def fetch_all_jobs() -> list[dict]:
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    jobs = data.get("jobs", [])
    print(f"총 {len(jobs)}건의 채용 공고 조회")
    return jobs


def filter_jobs(jobs: list[dict]) -> list[dict]:
    filtered = []
    for job in jobs:
        location = job.get("location", {}).get("name", "")
        title = job.get("title", "")

        if TARGET_LOCATION in location and TARGET_KEYWORD in title:
            filtered.append(job)

    print(f"필터링 후 {len(filtered)}건 ({TARGET_LOCATION} + '{TARGET_KEYWORD}')")
    return filtered


def job_to_row(job: dict) -> list[str]:
    job_id = str(job.get("id", ""))
    departments = job.get("departments", [])
    dept_name = departments[0].get("name", "") if departments else ""

    return [
        job_id,
        job.get("title", ""),
        "쿠팡",
        dept_name,
        job.get("location", {}).get("name", ""),
        "정규직",
        format_date_iso(job.get("first_published")),
        "상시채용",
        job.get("absolute_url", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row, filter_fn=filter_jobs)
