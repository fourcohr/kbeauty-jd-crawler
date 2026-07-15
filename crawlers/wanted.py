"""원티드 크롤러 - 기업명 키워드 검색 (company_id API 미사용)"""
import re
import requests
import time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "wanted-user-agent": "wanted-web",
    "Accept": "application/json",
}


def _normalize_co(name: str) -> str:
    name = re.sub(r'주식회사|㈜|\(주\)|\(유\)|유한회사|\s|\(|\)', '', name)
    return name.lower()


def _company_matches(found: str, searched: str) -> bool:
    f = _normalize_co(found)
    s = _normalize_co(searched)
    return bool(f and s and f == s)


def crawl_company(company: str, days: int = 7) -> list[dict]:
    today = datetime.today().strftime("%Y-%m-%d")
    from datetime import timedelta
    cutoff = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    jobs = []
    offset = 0
    while True:
        try:
            resp = requests.get(
                "https://www.wanted.co.kr/api/v4/jobs",
                params={
                    "query": company,
                    "country": "kr",
                    "job_sort": "job.latest_order",
                    "limit": 20,
                    "offset": offset,
                },
                headers=HEADERS,
                timeout=8,
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            items = data.get("data", [])
            if not items:
                break
            for item in items:
                found_company = item.get("company", {}).get("name", "")
                if not _company_matches(found_company, company):
                    continue
                job_id = item.get("id")
                title = item.get("position", "")
                career = item.get("experience_level", {}).get("name", "")
                reg_date = (item.get("created_time") or "")[:10] or today
                # 최근 N일 이내 등록된 공고만 수집
                if reg_date < cutoff:
                    continue
                deadline = (item.get("due_time") or "")[:10]
                jobs.append({
                    "수집일": today,
                    "회사명": found_company,
                    "포지션명": title,
                    "직무": "",
                    "경력": career,
                    "고용형태": "정규직",
                    "플랫폼": "원티드",
                    "URL": f"https://www.wanted.co.kr/wd/{job_id}",
                    "공고등록일": reg_date,
                    "공고마감일": deadline,
                    "원문직무명": title,
                    "중복여부": "N",
                })
            offset += 20
            if len(items) < 20:
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"  [원티드] {company} 조회 오류: {e}")
            break
    return jobs


def crawl(companies: list[str], days: int = 7) -> list[dict]:
    """기업 리스트 전체 원티드 크롤링"""
    all_jobs = []
    for company in companies:
        jobs = crawl_company(company, days=days)
        if jobs:
            print(f"  [원티드] {company}: {len(jobs)}건")
            all_jobs.extend(jobs)
        time.sleep(1)
    print(f"[원티드] 총 {len(all_jobs)}건 수집")
    return all_jobs
