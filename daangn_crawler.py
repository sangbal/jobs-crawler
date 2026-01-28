#!/usr/bin/env python3
"""당근 채용 정보 크롤러 - Google Sheets 자동 적재"""

import json
import os
from datetime import datetime

import gspread
import requests
from google.oauth2.service_account import Credentials

# API 설정 (Gatsby page-data)
API_URL = "https://about.daangn.com/page-data/jobs/business/page-data.json"

# 필터 조건
TARGET_EMPLOYMENT_TYPE = "FULL_TIME"

# 회사 코드 매핑
CORPORATE_NAMES = {
    "KARROT_MARKET": "당근마켓",
    "KARROT_PAY": "당근페이",
    "KARROT": "당근",
}

# Google Sheets 스코프
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def fetch_all_jobs() -> list[dict]:
    """당근 채용 정보를 가져옵니다."""
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    jobs = data.get("result", {}).get("data", {}).get("allDepartmentFilteredJobPost", {}).get("nodes", [])
    print(f"총 {len(jobs)}건의 Business 직군 공고 조회")
    return jobs


def filter_jobs(jobs: list[dict]) -> list[dict]:
    """조건에 맞는 공고만 필터링합니다."""
    filtered = [job for job in jobs if job.get("employmentType") == TARGET_EMPLOYMENT_TYPE]
    print(f"필터링 후 {len(filtered)}건 (정규직)")
    return filtered


def job_to_row(job: dict) -> list[str]:
    """채용 정보를 스프레드시트 행으로 변환합니다."""
    gh_id = str(job.get("ghId", ""))
    corporate = job.get("corporate", "")
    company_name = CORPORATE_NAMES.get(corporate, corporate)
    employment_type = "정규직" if job.get("employmentType") == "FULL_TIME" else job.get("employmentType", "")

    return [
        gh_id,
        job.get("title", ""),
        company_name,
        "Business",  # 직군 (이 API는 business 직군만 반환)
        "",  # 근무지 (API에서 제공 안함)
        employment_type,
        "",  # 등록일 (API에서 제공 안함)
        "상시채용",  # 마감일
        job.get("absoluteUrl", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


def get_google_sheet():
    """Google Sheets 클라이언트와 시트를 초기화합니다."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    spreadsheet_id = os.environ.get("DAANGN_SPREADSHEET_ID")

    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS 환경변수가 설정되지 않았습니다.")
    if not spreadsheet_id:
        raise ValueError("DAANGN_SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")

    creds_data = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.sheet1


def setup_header(sheet) -> None:
    """시트에 헤더가 없으면 추가합니다."""
    header = ["공고ID", "직무명", "회사", "직군", "근무지", "고용형태", "등록일", "마감일", "URL", "수집일시"]
    existing = sheet.row_values(1)

    if not existing or existing != header:
        sheet.update("A1:J1", [header])
        print("헤더 설정 완료")


def get_existing_ids(sheet) -> set[str]:
    """이미 등록된 공고 ID 목록을 가져옵니다."""
    try:
        ids = sheet.col_values(1)[1:]  # 헤더 제외
        return set(ids)
    except Exception:
        return set()


def main():
    """메인 실행 함수"""
    print("=== 당근 채용 정보 크롤러 시작 ===")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 채용 정보 수집
    jobs = fetch_all_jobs()

    if not jobs:
        print("수집된 채용 공고가 없습니다.")
        return

    # 필터링
    filtered_jobs = filter_jobs(jobs)

    if not filtered_jobs:
        print("조건에 맞는 채용 공고가 없습니다.")
        return

    # Google Sheets 연결
    print("\nGoogle Sheets 연결 중...")
    sheet = get_google_sheet()
    setup_header(sheet)

    # 기존 공고 ID 확인
    existing_ids = get_existing_ids(sheet)
    print(f"기존 등록 공고: {len(existing_ids)}건")

    # 신규 공고 필터링
    new_jobs = [job for job in filtered_jobs if str(job.get("ghId")) not in existing_ids]
    print(f"신규 공고: {len(new_jobs)}건")

    if not new_jobs:
        print("추가할 신규 공고가 없습니다.")
        return

    # 신규 공고 추가
    new_rows = [job_to_row(job) for job in new_jobs]
    sheet.append_rows(new_rows, value_input_option="USER_ENTERED")

    print(f"\n{len(new_rows)}건의 신규 공고가 추가되었습니다.")
    print("=== 크롤링 완료 ===")


if __name__ == "__main__":
    main()
