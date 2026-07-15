"""Google Sheets 읽기/쓰기 관리"""
import re
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import CREDENTIALS_PATH, SPREADSHEET_ID, SCOPES


def get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SPREADSHEET_ID)


def _normalize_co(name: str) -> str:
    name = re.sub(r'주식회사|㈜|\(주\)|\(유\)|유한회사|\s|\(|\)', '', name)
    return name.lower()


def append_rows(sheet_name: str, rows: list[list]):
    """RAW_DATA 등 시트에 행 추가. URL 중복 + 회사+포지션 중복 체크 포함."""
    if not rows:
        return 0
    sh = get_sheet()
    ws = sh.worksheet(sheet_name)

    if sheet_name == "RAW_DATA":
        existing = ws.get_all_values()
        headers = existing[0] if existing else []
        data_rows = existing[1:] if len(existing) > 1 else []

        # 컬럼 인덱스 (헤더 기반, 없으면 고정 인덱스 fallback)
        try:
            url_idx     = headers.index("URL")
            company_idx = headers.index("회사명")
            pos_idx     = headers.index("포지션명")
        except ValueError:
            url_idx, company_idx, pos_idx = 7, 1, 2

        existing_urls = {
            row[url_idx] for row in data_rows
            if len(row) > url_idx and row[url_idx]
        }
        existing_cp = {
            (_normalize_co(row[company_idx]), row[pos_idx].strip().lower())
            for row in data_rows
            if len(row) > pos_idx
        }

        new_rows = []
        for r in rows:
            url     = r[url_idx]     if len(r) > url_idx     else ""
            company = r[company_idx] if len(r) > company_idx else ""
            pos     = r[pos_idx]     if len(r) > pos_idx     else ""
            # URL 중복 또는 회사+포지션 중복이면 건너뜀
            if url and url in existing_urls:
                continue
            cp_key = (_normalize_co(company), pos.strip().lower())
            if cp_key in existing_cp:
                continue
            new_rows.append(r)
            if url:
                existing_urls.add(url)
            existing_cp.add(cp_key)

        if not new_rows:
            return 0
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        return len(new_rows)
    else:
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        return len(rows)


def overwrite_sheet(sheet_name: str, header: list, rows: list[list]):
    """집계 시트 전체 덮어쓰기"""
    sh = get_sheet()
    ws = sh.worksheet(sheet_name)
    ws.clear()
    ws.append_row(header)
    if rows:
        ws.append_rows(rows, value_input_option="USER_ENTERED")
    ws.format("1:1", {
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "backgroundColor": {"red": 0.13, "green": 0.27, "blue": 0.42},
    })


def get_raw_data() -> list[dict]:
    """RAW_DATA 전체 읽기, dict 리스트 반환"""
    sh = get_sheet()
    ws = sh.worksheet("RAW_DATA")
    records = ws.get_all_records()
    return records
