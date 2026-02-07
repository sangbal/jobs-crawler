#!/usr/bin/env python3
"""Common module for job crawlers — Google Sheets integration and orchestration.

Provides shared infrastructure for all company-specific crawlers:
- Google Sheets authentication via service account
- Sheet lifecycle management (create, header setup, archiving)
- Date format normalization (ISO 8601, compact YYYYMMDD)
- Crawler orchestration with full-replace write strategy
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    # Drive scope required to open spreadsheets by key (Sheets API alone is insufficient)
    "https://www.googleapis.com/auth/drive",
]

# Canonical column order — all crawlers must produce rows matching this schema
HEADER = ["회사", "직무명", "등록일", "마감일", "URL", "직군", "근무지", "고용형태", "공고ID", "수집일시"]


@dataclass
class CrawlerConfig:
    """Per-company crawler settings passed to run_crawler().

    Attributes:
        company_name: Display name for log messages (e.g. "카카오").
        sheet_name: Google Sheets tab name where active jobs are stored.
        spreadsheet_env_var: Environment variable holding the spreadsheet ID.
        job_id_field: JSON key for the unique job identifier in the API response.
            Varies by API — e.g. "realId" (Kakao), "id" (Toss), "annoId" (Naver).
    """
    company_name: str
    sheet_name: str
    spreadsheet_env_var: str
    job_id_field: str


def get_google_spreadsheet(spreadsheet_env_var: str):
    """Authenticate with Google via service account and return a Spreadsheet object.

    Reads GOOGLE_CREDENTIALS (JSON key) and the spreadsheet ID from environment
    variables. Raises ValueError if either is missing.
    """
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
    """Return the named worksheet, creating it with the standard header if absent."""
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        sheet.update("A1:J1", [HEADER])
        print(f"{sheet_name} 시트 생성 완료")
        return sheet


def get_or_create_archive_sheet(spreadsheet):
    """Return the 'Archive' worksheet, creating it if needed."""
    return get_or_create_sheet(spreadsheet, "Archive")


def archive_closed_jobs(spreadsheet, sheet, active_job_ids: set[str]) -> int:
    """Move jobs no longer present in the API response to the Archive sheet.

    Compares the current sheet rows against active_job_ids (from the latest crawl).
    Rows whose 공고ID (column I, index 8) is not in active_job_ids are appended to Archive.
    This preserves a historical record of closed/removed postings.

    Returns the number of rows archived.
    """
    archive = get_or_create_archive_sheet(spreadsheet)

    all_rows = sheet.get_all_values()
    if len(all_rows) <= 1:  # Only header or empty
        return 0

    data_rows = all_rows[1:]  # Skip header row
    rows_to_archive = [
        row for row in data_rows
        # row[8] = 공고ID (column I); skip short/empty rows
        if row and len(row) > 8 and row[8] and row[8] not in active_job_ids
    ]

    if not rows_to_archive:
        return 0

    archive.append_rows(rows_to_archive, value_input_option="USER_ENTERED")
    return len(rows_to_archive)


def setup_header(sheet) -> None:
    """Ensure the header row is correct. Idempotent — safe to call repeatedly."""
    existing = sheet.row_values(1)
    if not existing or existing != HEADER:
        sheet.update("A1:J1", [HEADER])
        print("헤더 설정 완료")


def get_existing_ids(sheet) -> set[str]:
    """Return the set of job IDs currently in the sheet (column I, excluding header).

    Returns an empty set on API errors (e.g. empty sheet edge cases).
    """
    try:
        ids = sheet.col_values(9)[1:]  # Column I = 공고ID
        return set(ids)
    except gspread.exceptions.APIError:
        return set()


def format_date_iso(date_str: str | None, default: str = "") -> str:
    """Parse an ISO 8601 datetime string and return YYYY-MM-DD.

    Handles the 'Z' suffix (UTC) by converting to '+00:00' for fromisoformat().
    Returns *default* if date_str is falsy, or the original string on parse failure.
    """
    if not date_str:
        return default
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return date_str


def format_date_compact(date_str: str | None, fmt: str = "%Y%m%d", default: str = "상시채용") -> str:
    """Parse a compact date string (e.g. '20250115') via strptime and return YYYY-MM-DD.

    Used by Naver which returns dates in YYYYMMDD format.
    Returns *default* (상시채용) if date_str is falsy.
    """
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
    """Orchestrate a full crawl cycle: fetch → filter → archive → overwrite.

    Uses a **full-replace strategy**: after archiving closed jobs, the entire sheet
    (except Archive) is cleared and rewritten with current data. This ensures the
    sheet always reflects the exact state of the API, avoiding stale or duplicate rows.

    Args:
        config: Company-specific settings (sheet name, env var, etc.).
        fetch_fn: Fetches all raw job postings from the company API.
        job_to_row_fn: Converts a single job dict to a 10-column row.
        filter_fn: Optional post-fetch filter (e.g. by employment type or category).
    """
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
        # 필터링 결과 0건 — 시트를 헤더만 남기고 비움 (빈 데이터도 정확히 반영)
        print("조건에 맞는 채용 공고가 없습니다.")
        sheet.clear()
        setup_header(sheet)
        print("=== 크롤링 완료 ===")
        return

    data_rows = [job_to_row_fn(job) for job in jobs]
    # Sort by 회사(col 0) asc, then 등록일(col 2) desc (newest first within each company)
    data_rows.sort(key=lambda row: (row[0], row[2] if row[2] and row[2] != "상시채용" else ""), reverse=True)
    all_rows = [HEADER] + data_rows

    sheet.clear()
    sheet.update(f"A1:J{len(all_rows)}", all_rows, value_input_option="USER_ENTERED")

    print(f"\n{len(jobs)}건의 공고를 최신 데이터로 갱신했습니다.")
    print("=== 크롤링 완료 ===")
