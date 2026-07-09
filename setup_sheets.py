"""
Google Sheets 연결 테스트 및 탭 구조 초기화
"""
import gspread
from google.oauth2.service_account import Credentials

CREDENTIALS_PATH = r"C:\Users\fourcompany\jd_crawler\credentials.json"
SPREADSHEET_ID = "1NUj12duoH3DF0HQxAWRRC81uVEUs9PY9GJLgqdSusI8"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = {
    "RAW_DATA": [
        "수집일", "회사명", "포지션명", "직무", "경력", "고용형태",
        "플랫폼", "URL", "공고등록일", "공고마감일", "원문직무명", "중복여부"
    ],
    "WEEKLY_SUMMARY": [
        "집계주차", "직무", "건수", "전주대비", "타겟여부", "라이징여부"
    ],
    "MONTHLY_SUMMARY": [
        "집계월", "직무", "건수", "전월대비", "전월건수"
    ],
    "TARGET_POSITIONS": [
        "기준일", "포지션명", "직무", "주간건수", "전월주간평균", "전주건수", "주요브랜드", "상태"
    ],
    "RISING_POSITIONS": [
        "기준일", "포지션명", "직무", "첫등장일", "이번달건수", "주요브랜드", "설명", "상태"
    ],
    "BRAND_STATS": [
        "집계월", "브랜드", "건수", "전월건수", "주요직무", "플랫폼"
    ],
    "SKILL_TRENDS": [
        "집계월", "키워드", "건수", "전월건수", "증가율", "방향"
    ],
}


def setup():
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)

    print("[OK] 연결 성공: " + sh.title)

    existing = [ws.title for ws in sh.worksheets()]
    print("기존 탭: " + str(existing))

    for sheet_name, headers in SHEET_HEADERS.items():
        if sheet_name in existing:
            print(f"  - {sheet_name}: 이미 존재 (건너뜀)")
        else:
            ws = sh.add_worksheet(title=sheet_name, rows=10000, cols=len(headers))
            ws.append_row(headers)
            ws.format("1:1", {
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "backgroundColor": {"red": 0.13, "green": 0.27, "blue": 0.42},
                "horizontalAlignment": "CENTER",
            })
            print(f"  [생성] {sheet_name}: {len(headers)}개 컬럼")

    # 기본 Sheet1 삭제 (비어있는 경우)
    for default_name in ["시트1", "Sheet1"]:
        if default_name in existing:
            try:
                sh.del_worksheet(sh.worksheet(default_name))
                print(f"  - 기본 {default_name} 삭제")
            except Exception:
                pass

    print("\n[완료] Google Sheets 구조 초기화 완료!")
    print(f"URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


if __name__ == "__main__":
    setup()
