import os
import json

CREDENTIALS_PATH = os.environ.get(
    "CREDENTIALS_PATH",
    os.path.join(os.path.dirname(__file__), "credentials.json"),
)
SPREADSHEET_ID = "1NUj12duoH3DF0HQxAWRRC81uVEUs9PY9GJLgqdSusI8"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

JOB_CATEGORIES = [
    "개발", "경영관리", "기획", "디자인", "마케팅",
    "상품기획", "영업", "제작", "SCM", "기타"
]

TARGET_THRESHOLD = 3  # 동일 포지션을 채용 중인 최소 회사 수
RISING_LOOKBACK_DAYS = 30

# ── 수집 대상 기업 목록 (두 엑셀 파일 기반 확정 화이트리스트) ──
_lists_path = os.path.join(os.path.dirname(__file__), "company_lists.json")
with open(_lists_path, encoding="utf-8-sig") as f:
    _data = json.load(f)

# 상위 90개 기업명 (헤더 행 제외)
TOP90_COMPANIES = [
    c["회사명"] for c in _data["top90"]
    if c["회사명"] not in ("회사명", "") and c["순위"] != "순위"
]

# 타사 홈페이지 리스트 (URL 있는 것만 홈페이지 크롤링, 없는 것은 포털로)
HOMEPAGE_TARGETS = [
    c for c in _data["homepage"]
    if c["회사명"] not in ("포컴퍼니", "회사명", "") and c["URL"]
]

# 홈페이지 URL 없는 기업 → 잡포털에서 회사명 검색
HOMEPAGE_NO_URL = [
    c["회사명"] for c in _data["homepage"]
    if c["회사명"] not in ("포컴퍼니", "회사명", "") and not c["URL"]
]

# 포털 검색 대상: TOP90 + 홈페이지 리스트(URL 없는 것) — 중복 제거
_homepage_names = {c["회사명"] for c in _data["homepage"]}
PORTAL_TARGET_COMPANIES = list({
    *TOP90_COMPANIES,
    *HOMEPAGE_NO_URL,
})
