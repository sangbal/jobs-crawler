#!/usr/bin/env python3
"""당근 채용 정보 크롤러 - Google Sheets 자동 적재"""

from datetime import datetime

import requests

from base import CrawlerConfig, run_crawler

CONFIG = CrawlerConfig(
    company_name="당근",
    sheet_name="당근",
    spreadsheet_env_var="DAANGN_SPREADSHEET_ID",
    job_id_field="ghId",
)

API_URL = "https://about.daangn.com/page-data/jobs/business/page-data.json"

TARGET_EMPLOYMENT_TYPE = "FULL_TIME"

CORPORATE_NAMES = {
    "KARROT_MARKET": "당근마켓",
    "KARROT_PAY": "당근페이",
    "KARROT": "당근",
}


def fetch_all_jobs() -> list[dict]:
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    jobs = data.get("result", {}).get("data", {}).get("allDepartmentFilteredJobPost", {}).get("nodes", [])
    print(f"총 {len(jobs)}건의 Business 직군 공고 조회")
    return jobs


def filter_jobs(jobs: list[dict]) -> list[dict]:
    filtered = [job for job in jobs if job.get("employmentType") == TARGET_EMPLOYMENT_TYPE]
    print(f"필터링 후 {len(filtered)}건 (정규직)")
    return filtered


def job_to_row(job: dict) -> list[str]:
    gh_id = str(job.get("ghId", ""))
    corporate = job.get("corporate", "")
    company_name = CORPORATE_NAMES.get(corporate, corporate)
    employment_type = "정규직" if job.get("employmentType") == "FULL_TIME" else job.get("employmentType", "")

    return [
        gh_id,
        job.get("title", ""),
        company_name,
        "Business",
        "",
        employment_type,
        "",
        "상시채용",
        job.get("absoluteUrl", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row, filter_fn=filter_jobs)
