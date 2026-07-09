"""원티드 크롤러 - 기업명 직접 검색"""
import requests
import time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "wanted-user-agent": "wanted-web",
    "Accept": "application/json",
}


def _get_company_id(company: str) -> int | None:
    """기업명으로 원티드 company_id 조회"""
    try:
        resp = requests.get(
            "https://www.wanted.co.kr/api/v4/companies",
            params={"query": company},
            headers=HEADERS,
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        items = data.get("data", [])
        if not items:
            return None
        # 첫 번째 결과 (가장 유사한 기업)
        return items[0].get("id")
    except Exception:
        return None


def _crawl_by_company_id(company_id: int, company_name: str) -> list[dict]:
    today = datetime.today().strftime("%Y-%m-%d")
    jobs = []
    offset = 0
    while True:
        try:
            resp = requests.get(
                "https://www.wanted.co.kr/api/v4/jobs",
                params={
                    "company_ids[]": company_id,
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
                job_id = item.get("id")
                title = item.get("position", "")
                career = item.get("experience_level", {}).get("name", "")
                reg_date = (item.get("created_time") or "")[:10] or today
                deadline = (item.get("due_time") or "")[:10]
                jobs.append({
                    "수집일": today,
                    "회사명": company_name,
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
            print(f"  [원티드] {company_name} 조회 오류: {e}")
            break
    return jobs


def crawl_company(company: str) -> list[dict]:
    company_id = _get_company_id(company)
    if not company_id:
        return []
    return _crawl_by_company_id(company_id, company)


def crawl(companies: list[str]) -> list[dict]:
    """기업 리스트 전체 원티드 크롤링"""
    all_jobs = []
    for company in companies:
        jobs = crawl_company(company)
        if jobs:
            print(f"  [원티드] {company}: {len(jobs)}건")
            all_jobs.extend(jobs)
        time.sleep(1)
    print(f"[원티드] 총 {len(all_jobs)}건 수집")
    return all_jobs
