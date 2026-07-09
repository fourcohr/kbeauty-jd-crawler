"""Google Sheets 읽기/쓰기 관리"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import CREDENTIALS_PATH, SPREADSHEET_ID, SCOPES


def get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SPREADSHEET_ID)


def append_rows(sheet_name: str, rows: list[list]):
    """RAW_DATA 등 시트에 행 추가. 중복(URL+회사명) 체크 포함."""
    if not rows:
        return 0
    sh = get_sheet()
    ws = sh.worksheet(sheet_name)

    if sheet_name == "RAW_DATA":
        existing = ws.get_all_values()
        # URL(8번째 컬럼, index 7) 기준 중복 체크
        existing_urls = {row[7] for row in existing[1:] if len(row) > 7 and row[7]}
        new_rows = [r for r in rows if len(r) > 7 and r[7] not in existing_urls]
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
