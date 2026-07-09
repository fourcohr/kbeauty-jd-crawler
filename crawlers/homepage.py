"""타사 채용 홈페이지 크롤러 - GreetingHR / NineHire / recruiter.co.kr 등"""
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
}


def _crawl_greetinghr(company: str, url: str) -> list[dict]:
    """GreetingHR (*.career.greetinghr.com) 공고 수집"""
    jobs = []
    today = datetime.today().strftime("%Y-%m-%d")
    api_base = url.rstrip("/")
    # GreetingHR 공개 API 엔드포인트
    api_url = f"{api_base}/job-notices"
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data if isinstance(data, list) else data.get("data", data.get("items", []))
            for item in items:
                title = item.get("title") or item.get("jobTitle") or item.get("name", "")
                job_id = item.get("id") or item.get("jobNoticeId", "")
                detail_url = f"{api_base}/job-notices/{job_id}" if job_id else api_base
                career = item.get("career") or item.get("experienceCondition", "")
                jobs.append({
                    "수집일": today,
                    "회사명": company,
                    "포지션명": title,
                    "직무": "",
                    "경력": career,
                    "고용형태": "",
                    "플랫폼": "자사홈페이지",
                    "URL": detail_url,
                    "공고등록일": today,
                    "공고마감일": "",
                    "원문직무명": title,
                    "중복여부": "N",
                })
            return jobs
    except Exception:
        pass

    # API 실패 시 HTML 파싱
    return _crawl_html(company, url)


def _crawl_ninehire(company: str, url: str) -> list[dict]:
    """NineHire (*.ninehire.site) 공고 수집"""
    today = datetime.today().strftime("%Y-%m-%d")
    jobs = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        # NineHire 구조
        items = soup.select(".job-card") or soup.select(".recruit-item") or soup.select("li.item")
        for item in items:
            title_tag = item.select_one("h3, h4, .title, .job-title, a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "") if title_tag.name == "a" else ""
            detail_url = href if href.startswith("http") else (url.rstrip("/") + href if href else url)
            jobs.append({
                "수집일": today,
                "회사명": company,
                "포지션명": title,
                "직무": "",
                "경력": "",
                "고용형태": "",
                "플랫폼": "자사홈페이지",
                "URL": detail_url,
                "공고등록일": today,
                "공고마감일": "",
                "원문직무명": title,
                "중복여부": "N",
            })
    except Exception as e:
        print(f"[홈페이지] {company} NineHire 오류: {e}")
    return jobs


def _crawl_recruiter(company: str, url: str) -> list[dict]:
    """recruiter.co.kr 공고 수집"""
    today = datetime.today().strftime("%Y-%m-%d")
    jobs = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select(".recruit_list li") or soup.select(".job-list .item")
        for item in items:
            title_tag = item.select_one("a.title, .recruit_tit a, a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            detail_url = href if href.startswith("http") else ("https://www.recruiter.co.kr" + href if href else url)
            jobs.append({
                "수집일": today,
                "회사명": company,
                "포지션명": title,
                "직무": "",
                "경력": "",
                "고용형태": "",
                "플랫폼": "자사홈페이지",
                "URL": detail_url,
                "공고등록일": today,
                "공고마감일": "",
                "원문직무명": title,
                "중복여부": "N",
            })
    except Exception as e:
        print(f"[홈페이지] {company} recruiter 오류: {e}")
    return jobs


def _crawl_html(company: str, url: str) -> list[dict]:
    """일반 HTML 채용페이지 파싱 (범용)"""
    today = datetime.today().strftime("%Y-%m-%d")
    jobs = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        # 공고 링크 후보 셀렉터
        candidates = (
            soup.select("a[href*='recruit'], a[href*='career'], a[href*='job']")
        )
        seen = set()
        for a in candidates:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not title or len(title) < 3 or href in seen:
                continue
            if any(skip in title for skip in ["채용", "Career", "Jobs", "공고", "지원"]) and len(title) < 8:
                continue
            seen.add(href)
            detail_url = href if href.startswith("http") else (url.rstrip("/") + "/" + href.lstrip("/"))
            jobs.append({
                "수집일": today,
                "회사명": company,
                "포지션명": title,
                "직무": "",
                "경력": "",
                "고용형태": "",
                "플랫폼": "자사홈페이지",
                "URL": detail_url,
                "공고등록일": today,
                "공고마감일": "",
                "원문직무명": title,
                "중복여부": "N",
            })
    except Exception as e:
        print(f"[홈페이지] {company} HTML 파싱 오류: {e}")
    return jobs


def crawl(targets: list[dict]) -> list[dict]:
    """
    targets: [{"회사명": "달바글로벌", "URL": "https://..."}, ...]
    """
    all_jobs = []
    for t in targets:
        company = t["회사명"]
        url = t.get("URL") or ""
        if not url:
            print(f"[홈페이지] {company}: URL 없음, 건너뜀")
            continue

        print(f"[홈페이지] {company} 수집 중... ({url})")
        if "greetinghr.com" in url:
            jobs = _crawl_greetinghr(company, url)
        elif "ninehire.site" in url:
            jobs = _crawl_ninehire(company, url)
        elif "recruiter.co.kr" in url:
            jobs = _crawl_recruiter(company, url)
        else:
            jobs = _crawl_html(company, url)

        print(f"  -> {len(jobs)}건")
        all_jobs.extend(jobs)
        time.sleep(1)

    return all_jobs
