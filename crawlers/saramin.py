"""사람인 크롤러 - 기업명 직접 검색"""
import requests
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

BASE_URL = "https://www.saramin.co.kr/zf_user/search/recruit"


def _normalize_co(name: str) -> str:
    name = re.sub(r'주식회사|㈜|\(주\)|\(유\)|유한회사|\s|\(|\)', '', name)
    return name.lower()


def _company_matches(found: str, searched: str) -> bool:
    f = _normalize_co(found)
    s = _normalize_co(searched)
    return bool(f and s and f == s)


def _parse_jobs(soup, company_name: str, today: str) -> list[dict]:
    jobs = []
    items = soup.select(".item_recruit")
    for item in items:
        try:
            company_tag = item.select_one(".corp_name a")
            title_tag = item.select_one(".job_tit a")
            if not title_tag:
                continue

            found_company = company_tag.get_text(strip=True) if company_tag else company_name
            title = title_tag.get_text(strip=True)
            url = "https://www.saramin.co.kr" + title_tag.get("href", "")

            career_tag = item.select_one(".career")
            career = career_tag.get_text(strip=True) if career_tag else ""

            employ_tag = item.select_one(".employ")
            employ = employ_tag.get_text(strip=True) if employ_tag else ""

            date_tag = item.select_one(".recruit_info .date")
            reg_date, deadline = today, ""
            if date_tag:
                text = date_tag.get_text(strip=True)
                dates = re.findall(r"\d{2}/\d{2}", text)
                year = datetime.today().year
                if dates:
                    try:
                        reg_date = datetime.strptime(f"{year}/{dates[0]}", "%Y/%m/%d").strftime("%Y-%m-%d")
                    except Exception:
                        pass
                    if len(dates) > 1:
                        try:
                            deadline = datetime.strptime(f"{year}/{dates[1]}", "%Y/%m/%d").strftime("%Y-%m-%d")
                        except Exception:
                            pass

            jobs.append({
                "수집일": today,
                "회사명": found_company,
                "포지션명": title,
                "직무": "",
                "경력": career,
                "고용형태": employ,
                "플랫폼": "사람인",
                "URL": url,
                "공고등록일": reg_date,
                "공고마감일": deadline,
                "원문직무명": title,
                "중복여부": "N",
            })
        except Exception:
            continue
    return jobs


def crawl_company(company: str, days: int = 7) -> list[dict]:
    """단일 기업명으로 사람인 검색 — 최근 days일 이내 등록 공고만 수집"""
    today = datetime.today().strftime("%Y-%m-%d")
    jobs = []
    for page in range(1, 3):
        params = {
            "searchword": company,
            "searchType": "company_nm",
            "recruitPage": page,
            "recruitPageCount": 40,
            "recruitSort": "reg_dt",   # 최신 등록순 정렬
            "period": days,            # 최근 N일 이내 등록된 공고만
        }
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            page_jobs = _parse_jobs(soup, company, today)
            if not page_jobs:
                break
            # 검색한 회사명과 실제로 일치하는 공고만 유지
            page_jobs = [j for j in page_jobs if _company_matches(j["회사명"], company)]
            jobs.extend(page_jobs)
            time.sleep(1)
        except Exception as e:
            print(f"  [사람인] {company} 오류: {e}")
            break
    return jobs


def crawl(companies: list[str], days: int = 7) -> list[dict]:
    """기업 리스트 전체 사람인 크롤링"""
    all_jobs = []
    for company in companies:
        jobs = crawl_company(company, days=days)
        if jobs:
            print(f"  [사람인] {company}: {len(jobs)}건")
            all_jobs.extend(jobs)
        time.sleep(1.2)
    print(f"[사람인] 총 {len(all_jobs)}건 수집")
    return all_jobs
