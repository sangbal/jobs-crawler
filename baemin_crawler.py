#!/usr/bin/env python3
"""Baemin (Woowahan Brothers) job crawler — fetches postings from career.woowahan.com and writes to Google Sheets."""

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
    "jobGroupCodes": "BA005010",       # 직군: Business & Sales
    "employmentTypeCodes": "BA002001", # 고용형태: 정규직
}


def fetch_all_jobs() -> list[dict]:
    """Fetch all Business & Sales postings from the Woowahan career API.

    Requires a User-Agent header — the API returns 403 without one.
    Success is indicated by code=2000; compared as string because
    the API inconsistently returns it as int or string across versions.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    response = requests.get(API_URL, params=PARAMS, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    # str() 비교: API가 code를 int 또는 string으로 반환할 수 있음
    if str(data.get("code")) != "2000":
        raise ValueError(f"API 요청 실패: {data.get('message')}")

    jobs = data.get("data", {}).get("list", [])
    total = data.get("data", {}).get("totalSize", 0)
    print(f"총 {total}건의 채용 공고 조회")
    return jobs


def format_date(date_str: str | None) -> str:
    """Parse a Baemin date string (YYYY-MM-DD...) and return YYYY-MM-DD.

    Separate from base.format_date_compact because the input format differs:
    Baemin uses "%Y-%m-%d" (with hyphens), while base uses "%Y%m%d" (compact).
    Also handles sentinel years 9999/2999 which Baemin uses for 상시채용.
    """
    if not date_str:
        return ""
    # 9999, 2999 = 상시채용 (배민 API의 마감일 없음 표현)
    if date_str.startswith("9999") or date_str.startswith("2999"):
        return "상시채용"
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return date_str


def job_to_row(job: dict) -> list[str]:
    """Convert a Baemin job dict to a 10-column spreadsheet row.

    Company name (우아한형제들), 직군 (Business & Sales), and 고용형태 (정규직)
    are hardcoded because the API params already filter to these values.
    """
    recruit_number = job.get("recruitNumber", "")
    url = f"https://career.woowahan.com/recruitment/{recruit_number}/detail" if recruit_number else ""

    return [
        "우아한형제들",
        job.get("recruitName", ""),
        format_date(job.get("recruitOpenDate")),
        format_date(job.get("recruitEndDate")),
        url,
        "Business & Sales",
        "",          # 근무지: 배민 API 미제공
        "정규직",
        recruit_number,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row)
