#!/usr/bin/env python3
"""카카오 채용 정보 크롤러 - Google Sheets 자동 적재"""

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
    "part": "BUSINESS_SERVICES",
    "employeeType": "0",
    "company": "ALL",
}


def fetch_all_jobs() -> list[dict]:
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
    real_id = job.get("realId", "")
    url = f"https://careers.kakao.com/jobs/{real_id}" if real_id else ""
    return [
        real_id,
        job.get("jobOfferTitle", ""),
        job.get("companyName", ""),
        job.get("jobPartName", "") or job.get("jobTypeName", ""),
        job.get("locationName", ""),
        job.get("employeeTypeName", ""),
        format_date_iso(job.get("regDate"), default="상시채용"),
        format_date_iso(job.get("endDate"), default="상시채용"),
        url,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row)
