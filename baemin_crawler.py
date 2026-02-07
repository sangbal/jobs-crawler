#!/usr/bin/env python3
"""배민(우아한형제들) 채용 정보 크롤러 - Google Sheets 자동 적재"""

from datetime import datetime

import requests

from base import CrawlerConfig, run_crawler

CONFIG = CrawlerConfig(
    company_name="배민",
    sheet_name="배민",
    spreadsheet_env_var="BAEMIN_SPREADSHEET_ID",
    job_id_field="recruitNumber",
)

API_URL = "https://career.woowahan.com/w1/recruits"
PARAMS = {
    "jobGroupCodes": "BA005010",
    "employmentTypeCodes": "BA002001",
}


def fetch_all_jobs() -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    response = requests.get(API_URL, params=PARAMS, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    if str(data.get("code")) != "2000":
        raise ValueError(f"API 요청 실패: {data.get('message')}")

    jobs = data.get("data", {}).get("list", [])
    total = data.get("data", {}).get("totalSize", 0)
    print(f"총 {total}건의 채용 공고 조회")
    return jobs


def format_date(date_str: str | None) -> str:
    if not date_str:
        return ""
    if date_str.startswith("9999") or date_str.startswith("2999"):
        return "상시채용"
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return date_str


def job_to_row(job: dict) -> list[str]:
    recruit_number = job.get("recruitNumber", "")
    url = f"https://career.woowahan.com/recruitment/{recruit_number}/detail" if recruit_number else ""

    return [
        recruit_number,
        job.get("recruitName", ""),
        "우아한형제들",
        "Business & Sales",
        "",
        "정규직",
        format_date(job.get("recruitOpenDate")),
        format_date(job.get("recruitEndDate")),
        url,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row)
