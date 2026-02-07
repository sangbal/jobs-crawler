#!/usr/bin/env python3
"""채용 크롤러 공통 모듈 - Google Sheets 연동 및 오케스트레이션"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADER = ["공고ID", "직무명", "회사", "직군", "근무지", "고용형태", "등록일", "마감일", "URL", "수집일시"]


@dataclass
class CrawlerConfig:
    company_name: str
    sheet_name: str
    spreadsheet_env_var: str
    job_id_field: str


def get_google_spreadsheet(spreadsheet_env_var: str):
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    spreadsheet_id = os.environ.get(spreadsheet_env_var)

    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS 환경변수가 설정되지 않았습니다.")
    if not spreadsheet_id:
        raise ValueError(f"{spreadsheet_env_var} 환경변수가 설정되지 않았습니다.")

    creds_data = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    client = gspread.authorize(credentials)

    return client.open_by_key(spreadsheet_id)


def get_or_create_sheet(spreadsheet, sheet_name: str):
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        sheet.update("A1:J1", [HEADER])
        print(f"{sheet_name} 시트 생성 완료")
        return sheet


def get_or_create_archive_sheet(spreadsheet):
    return get_or_create_sheet(spreadsheet, "Archive")


def archive_closed_jobs(spreadsheet, sheet, active_job_ids: set[str]) -> int:
    archive = get_or_create_archive_sheet(spreadsheet)

    all_rows = sheet.get_all_values()
    if len(all_rows) <= 1:
        return 0

    data_rows = all_rows[1:]
    rows_to_archive = [
        row for row in data_rows
        if row and row[0] and row[0] not in active_job_ids
    ]

    if not rows_to_archive:
        return 0

    archive.append_rows(rows_to_archive, value_input_option="USER_ENTERED")
    return len(rows_to_archive)


def setup_header(sheet) -> None:
    existing = sheet.row_values(1)
    if not existing or existing != HEADER:
        sheet.update("A1:J1", [HEADER])
        print("헤더 설정 완료")


def get_existing_ids(sheet) -> set[str]:
    try:
        ids = sheet.col_values(1)[1:]
        return set(ids)
    except Exception:
        return set()


def format_date_iso(date_str: str | None, default: str = "") -> str:
    if not date_str:
        return default
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return date_str


def format_date_compact(date_str: str | None, fmt: str = "%Y%m%d", default: str = "상시채용") -> str:
    if not date_str:
        return default
    try:
        dt = datetime.strptime(date_str, fmt)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return date_str


def run_crawler(
    config: CrawlerConfig,
    fetch_fn: Callable[[], list[dict]],
    job_to_row_fn: Callable[[dict], list[str]],
    filter_fn: Callable[[list[dict]], list[dict]] | None = None,
):
    print(f"=== {config.company_name} 채용 정보 크롤러 시작 ===")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    jobs = fetch_fn()

    if not jobs:
        print("수집된 채용 공고가 없습니다.")
        return

    if filter_fn:
        jobs = filter_fn(jobs)

    active_job_ids = set(
        str(job.get(config.job_id_field))
        for job in jobs
        if job.get(config.job_id_field)
    )

    print("\nGoogle Sheets 연결 중...")
    spreadsheet = get_google_spreadsheet(config.spreadsheet_env_var)
    sheet = get_or_create_sheet(spreadsheet, config.sheet_name)

    archived_count = archive_closed_jobs(spreadsheet, sheet, active_job_ids)
    if archived_count > 0:
        print(f"마감 공고 {archived_count}건을 Archive 시트로 이동")

    if not jobs:
        print("조건에 맞는 채용 공고가 없습니다.")
        sheet.clear()
        setup_header(sheet)
        print("=== 크롤링 완료 ===")
        return

    all_rows = [HEADER] + [job_to_row_fn(job) for job in jobs]

    sheet.clear()
    sheet.update(f"A1:J{len(all_rows)}", all_rows, value_input_option="USER_ENTERED")

    print(f"\n{len(jobs)}건의 공고를 최신 데이터로 갱신했습니다.")
    print("=== 크롤링 완료 ===")
