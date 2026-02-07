#!/usr/bin/env python3
"""Naver job crawler — fetches postings from recruit.navercorp.com and writes to Google Sheets."""

from datetime import datetime

import requests

from base import CrawlerConfig, format_date_compact, run_crawler

CONFIG = CrawlerConfig(
    company_name="네이버",
    sheet_name="네이버",
    spreadsheet_env_var="NAVER_SPREADSHEET_ID",
    job_id_field="annoId",
)

API_URL = "https://recruit.navercorp.com/rcrt/loadJobList.do"
PARAMS = {
    # subJobCdArr: Service & Business 하위 직군 코드 (기획, 마케팅, 사업개발 등)
    "subJobCdArr": "3010001,3020001,3030001,3040001,3060001,3070001",
    "empTypeCdArr": "0010",  # 0010 = 정규직
}
PAGE_SIZE = 10  # Naver API 기본값; 다음 offset 계산에 사용


def fetch_all_jobs() -> list[dict]:
    """Fetch all postings via offset-based pagination (firstIndex parameter).

    Unlike page-based APIs (e.g. Kakao), Naver uses an absolute offset.
    We increment by PAGE_SIZE until accumulated results reach totalSize.
    """
    all_jobs = []
    first_index = 0

    while True:
        params = {**PARAMS, "firstIndex": first_index}
        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("result") != "Y":
            raise ValueError(f"API 요청 실패: {data}")

        jobs = data.get("list", [])
        all_jobs.extend(jobs)

        total_size = data.get("totalSize", 0)
        print(f"수집 중... {len(all_jobs)}/{total_size}건")

        if len(all_jobs) >= total_size:
            break
        first_index += PAGE_SIZE

    print(f"총 {len(all_jobs)}건의 채용 공고 수집 완료")
    return all_jobs


def job_to_row(job: dict) -> list[str]:
    """Convert a Naver job dict to a 10-column spreadsheet row.

    Naver API does not provide a work location field, so 근무지 is left empty.
    Dates are in YYYYMMDD format (e.g. '20250115'), parsed by format_date_compact.
    """
    anno_id = str(job.get("annoId", ""))
    url = f"https://recruit.navercorp.com/rcrt/view.do?annoId={anno_id}&lang=ko" if anno_id else ""

    return [
        job.get("sysCompanyCdNm", ""),
        job.get("annoSubject", ""),
        format_date_compact(job.get("staYmd")),
        format_date_compact(job.get("endYmd")),
        url,
        job.get("subJobCdNm", ""),
        "",  # 근무지: Naver API 미제공
        job.get("empTypeCdNm", ""),
        anno_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row)
