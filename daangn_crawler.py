#!/usr/bin/env python3
"""Daangn (Karrot) job crawler — fetches postings from Gatsby page-data and writes to Google Sheets."""

from datetime import datetime

import requests

from base import CrawlerConfig, run_crawler

CONFIG = CrawlerConfig(
    company_name="당근",
    sheet_name="당근",
    spreadsheet_env_var="DAANGN_SPREADSHEET_ID",
    job_id_field="ghId",
)

# Not a REST API — this is Gatsby's static build output (pre-rendered GraphQL result).
# The deep JSON path below reflects Gatsby's internal GraphQL query structure.
API_URL = "https://about.daangn.com/page-data/jobs/business/page-data.json"

TARGET_EMPLOYMENT_TYPE = "FULL_TIME"

# 당근 계열사 영문 코드 → 한국어 표시명 매핑
CORPORATE_NAMES = {
    "KARROT_MARKET": "당근마켓",
    "KARROT_PAY": "당근페이",
    "KARROT": "당근",
}


def fetch_all_jobs() -> list[dict]:
    """Fetch all Business job postings from Gatsby's pre-built page-data JSON.

    The data is nested under result.data.allDepartmentFilteredJobPost.nodes
    because Gatsby serializes its GraphQL query results into this structure.
    """
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    jobs = data.get("result", {}).get("data", {}).get("allDepartmentFilteredJobPost", {}).get("nodes", [])
    print(f"총 {len(jobs)}건의 Business 직군 공고 조회")
    return jobs


def filter_jobs(jobs: list[dict]) -> list[dict]:
    """Keep only 정규직 (FULL_TIME) postings."""
    filtered = [job for job in jobs if job.get("employmentType") == TARGET_EMPLOYMENT_TYPE]
    print(f"필터링 후 {len(filtered)}건 (정규직)")
    return filtered


def job_to_row(job: dict) -> list[str]:
    """Convert a Daangn job dict to a 10-column spreadsheet row.

    직군 is hardcoded to 'Business' because the page-data endpoint only
    returns Business postings (filtered at the URL level).
    근무지 and 등록일 are not provided by this data source.
    """
    gh_id = str(job.get("ghId", ""))
    corporate = job.get("corporate", "")
    company_name = CORPORATE_NAMES.get(corporate, corporate)
    employment_type = "정규직" if job.get("employmentType") == "FULL_TIME" else job.get("employmentType", "")

    return [
        company_name,
        job.get("title", ""),
        "",          # 등록일: 당근 API 미제공
        "상시채용",
        job.get("absoluteUrl", ""),
        "Business",  # URL이 /jobs/business/ 이므로 항상 Business 직군
        "",          # 근무지: 당근 API 미제공
        employment_type,
        gh_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row, filter_fn=filter_jobs)
