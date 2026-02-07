#!/usr/bin/env python3
"""네이버 채용 정보 크롤러 - Google Sheets 자동 적재"""

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
    "subJobCdArr": "3010001,3020001,3030001,3040001,3060001,3070001",
    "empTypeCdArr": "0010",
}
PAGE_SIZE = 10


def fetch_all_jobs() -> list[dict]:
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
    anno_id = str(job.get("annoId", ""))
    url = f"https://recruit.navercorp.com/rcrt/view.do?annoId={anno_id}&lang=ko" if anno_id else ""

    return [
        anno_id,
        job.get("annoSubject", ""),
        job.get("sysCompanyCdNm", ""),
        job.get("subJobCdNm", ""),
        "",
        job.get("empTypeCdNm", ""),
        format_date_compact(job.get("staYmd")),
        format_date_compact(job.get("endYmd")),
        url,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


if __name__ == "__main__":
    run_crawler(CONFIG, fetch_all_jobs, job_to_row)
