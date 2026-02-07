#!/usr/bin/env python3
"""Kakao job crawler — fetches postings from careers.kakao.com and writes to Google Sheets."""

from datetime import datetime

import requests

from base import CrawlerConfig, format_date_iso, run_crawler

CONFIG = CrawlerConfig(
    company_name="카카오",
    sheet_name="카카오",
    spreadsheet_env_var="SPREADSHEET_ID",
    job_id_field="realId",
)

API_URL = "https://careers.kakao.com/public/api/job-list"
PARAMS = {
    "part": "BUSINESS_SERVICES",   # 직군: 서비스비즈
    "employeeType": "0",           # 0 = 정규직 (1 = 계약직)
    "company": "ALL",              # 카카오 전체 계열사
}


def fetch_all_jobs() -> list[dict]:
    """Fetch all job postings via 1-based pagination.

    The API returns totalPage in each response; we iterate until page >= totalPage.
    """
    all_jobs = []
    page = 1

    while True:
        params = {**PARAMS, "page": page}
        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        jobs = data.get("jobList", [])
        all_jobs.extend(jobs)

        total_page = data.get("totalPage", 1)
        print(f"페이지 {page}/{total_page} 수집 완료 ({len(jobs)}건)")

        if page >= total_page:
            break
        page += 1

    print(f"총 {len(all_jobs)}건의 채용 공고 수집 완료")
    return all_jobs


def job_to_row(job: dict) -> list[str]:
    """Convert a Kakao job dict to a 10-column spreadsheet row.

    Uses jobPartName for 직군, falling back to jobTypeName when the API
    returns null for jobPartName (occurs for some cross-functional roles).
    """
    real_id = job.get("realId", "")
    url = f"https://careers.kakao.com/jobs/{real_id}" if real_id else ""
    return [
        job.get("companyName", ""),
        job.get("jobOfferTitle", ""),
        format_date_iso(job.get("regDate"), default="상시채용"),
        format_date_iso(job.get("endDate"), default="상시채용"),
        url,
        job.get("jobPartName", "") or job.get("jobTypeName", ""),
        job.get("locationName", ""),
        job.get("employeeTypeName", ""),
        real_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row)
