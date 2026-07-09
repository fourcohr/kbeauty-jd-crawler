"""공고 상세 내용(JD 원문) 크롤링"""
import requests
import time
import re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def fetch_saramin(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        # 사람인 JD 본문 영역
        cont = soup.select_one(".wrap_jd_cont") or soup.select_one(".jd_cont") or soup.select_one(".job_detail")
        if cont:
            return cont.get_text(separator="\n", strip=True)[:3000]
    except Exception:
        pass
    return ""


def fetch_wanted(url: str) -> str:
    try:
        # URL에서 job_id 추출: https://www.wanted.co.kr/wd/12345
        job_id = url.rstrip("/").split("/")[-1]
        if not job_id.isdigit():
            return ""
        api_url = f"https://www.wanted.co.kr/api/v4/jobs/{job_id}"
        resp = requests.get(api_url, headers={**HEADERS, "Accept": "application/json"}, timeout=8)
        if resp.status_code != 200:
            return ""
        data = resp.json().get("job", {}).get("detail", {})
        parts = [
            data.get("intro", ""),
            data.get("main_tasks", ""),
            data.get("requirements", ""),
            data.get("preferred_points", ""),
            data.get("benefits", ""),
        ]
        return "\n".join(p for p in parts if p)[:3000]
    except Exception:
        pass
    return ""


def fetch_homepage(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        # 공통 JD 본문 셀렉터
        for sel in [".job-detail", ".recruit-detail", ".jd-content", ".contents", "article", "main"]:
            cont = soup.select_one(sel)
            if cont:
                text = cont.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text[:3000]
    except Exception:
        pass
    return ""


def fetch(job: dict) -> str:
    """플랫폼에 맞는 JD 상세 내용 가져오기"""
    platform = job.get("플랫폼", "")
    url = job.get("URL", "")
    if not url or url == "#":
        return ""

    if platform == "사람인":
        content = fetch_saramin(url)
    elif platform == "원티드":
        content = fetch_wanted(url)
    else:
        content = fetch_homepage(url)

    # 공백/특수문자 정리
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def enrich_jobs(jobs: list[dict], delay: float = 0.8) -> list[dict]:
    """jobs 리스트에 공고내용 필드 추가"""
    for i, job in enumerate(jobs):
        if not job.get("공고내용"):
            job["공고내용"] = fetch(job)
        if (i + 1) % 10 == 0:
            print(f"  [상세 수집] {i+1}/{len(jobs)}건 완료")
        time.sleep(delay)
    return jobs
