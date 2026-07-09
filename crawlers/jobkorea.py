"""잡코리아 크롤러"""
import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.jobkorea.co.kr/",
}

BASE_URL = "https://www.jobkorea.co.kr/Search/"


def crawl(keyword: str = "화장품", pages: int = 3) -> list[dict]:
    jobs = []
    today = datetime.today().strftime("%Y-%m-%d")

    for page in range(1, pages + 1):
        params = {
            "stext": keyword,
            "Page_No": page,
        }
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[잡코리아] 페이지 {page} 오류: {e}")
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select(".list-post .post-list-info")

        if not items:
            # 대안 셀렉터 시도
            items = soup.select(".recruit-info")

        for item in items:
            try:
                title_tag = item.select_one(".title a") or item.select_one("a.tit")
                company_tag = item.select_one(".name a") or item.select_one(".corp-name a")
                if not title_tag or not company_tag:
                    continue

                title = title_tag.get_text(strip=True)
                company = company_tag.get_text(strip=True)
                href = title_tag.get("href", "")
                url = href if href.startswith("http") else f"https://www.jobkorea.co.kr{href}"

                career_tag = item.select_one(".career") or item.select_one(".exp")
                career = career_tag.get_text(strip=True) if career_tag else ""

                jobs.append({
                    "수집일": today,
                    "회사명": company,
                    "포지션명": title,
                    "직무": "",
                    "경력": career,
                    "고용형태": "",
                    "플랫폼": "잡코리아",
                    "URL": url,
                    "공고등록일": today,
                    "공고마감일": "",
                    "원문직무명": title,
                    "중복여부": "N",
                })
            except Exception as e:
                print(f"[잡코리아] 파싱 오류: {e}")

        time.sleep(1.5)

    print(f"[잡코리아] '{keyword}' {len(jobs)}건 수집")
    return jobs
