#!/usr/bin/env python3
"""배민(우아한형제들) 채용 정보 크롤러 - Google Sheets 자동 적재"""

import json
import os
from datetime import datetime

import gspread
import requests
from google.oauth2.service_account import Credentials

# API 설정
API_URL = "https://career.woowahan.com/w1/recruits"
PARAMS = {
    "jobGroupCodes": "BA005010",  # Business & Sales
    "employmentTypeCodes": "BA002001",  # 정규직
}

# Google Sheets 스코프
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def fetch_all_jobs() -> list[dict]:
    """배민 채용 정보를 가져옵니다."""
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
    """날짜 문자열을 포맷팅합니다."""
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
    """채용 정보를 스프레드시트 행으로 변환합니다."""
    recruit_number = job.get("recruitNumber", "")
    url = f"https://career.woowahan.com/recruitment/{recruit_number}/detail" if recruit_number else ""

    return [
        recruit_number,
        job.get("recruitName", ""),
        "우아한형제들",
        "Business & Sales",  # 직군 (필터로 고정)
        "",  # 근무지 (API에서 제공 안함)
        "정규직",  # 고용형태 (필터로 고정)
        format_date(job.get("recruitOpenDate")),
        format_date(job.get("recruitEndDate")),
        url,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


def get_google_sheet():
    """Google Sheets 클라이언트와 시트를 초기화합니다."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    spreadsheet_id = os.environ.get("BAEMIN_SPREADSHEET_ID")

    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS 환경변수가 설정되지 않았습니다.")
    if not spreadsheet_id:
        raise ValueError("BAEMIN_SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")

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
    print("=== 배민 채용 정보 크롤러 시작 ===")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 채용 정보 수집
    jobs = fetch_all_jobs()

    if not jobs:
        print("수집된 채용 공고가 없습니다.")
        return

    # Google Sheets 연결
    print("\nGoogle Sheets 연결 중...")
    sheet = get_google_sheet()
    setup_header(sheet)

    # 기존 공고 ID 확인
    existing_ids = get_existing_ids(sheet)
    print(f"기존 등록 공고: {len(existing_ids)}건")

    # 신규 공고 필터링
    new_jobs = [job for job in jobs if job.get("recruitNumber") not in existing_ids]
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
