"""
K뷰티 채용 트렌드 크롤러 메인 실행 파일

사용법:
  python main.py          # 전체 실행 (daily 수집 + 분석)
  python main.py --mode weekly   # 주간 분석만
  python main.py --mode monthly  # 월간 분석만
  python main.py --dry-run       # 수집 테스트 (Sheets 저장 안함)
"""
import os
import sys
import time
from datetime import datetime, timedelta
from collections import defaultdict

from config import HOMEPAGE_TARGETS, PORTAL_TARGET_COMPANIES, ANTHROPIC_API_KEY
from classifier import classify_batch, analyze_positions
from sheets_manager import append_rows, overwrite_sheet, get_raw_data

import crawlers.saramin as saramin
import crawlers.wanted as wanted
import crawlers.homepage as homepage
import crawlers.detail as detail


def collect_daily(dry_run: bool = False):
    """신규 공고 수집 및 RAW_DATA 저장 — 화이트리스트 기업만"""
    all_jobs = []

    print("=" * 50)
    print(f"[수집 시작] {datetime.today().strftime('%Y-%m-%d %H:%M')}")
    print(f"대상 기업: {len(PORTAL_TARGET_COMPANIES)}개 (포털) + {len(HOMEPAGE_TARGETS)}개 (홈페이지)")
    print("=" * 50)

    # 최근 N일 이내 등록 공고만 수집 (기본 7일, 환경변수로 조정 가능)
    crawl_days = int(os.environ.get("CRAWL_DAYS", "7"))
    print(f"수집 기간: 최근 {crawl_days}일 이내 등록 공고")

    # 1. 사람인 - 기업명 직접 검색
    jobs = saramin.crawl(PORTAL_TARGET_COMPANIES, days=crawl_days)
    all_jobs.extend(jobs)
    time.sleep(2)

    # 2. 원티드 - 기업명 직접 검색
    jobs = wanted.crawl(PORTAL_TARGET_COMPANIES, days=crawl_days)
    all_jobs.extend(jobs)
    time.sleep(1)

    # 3. 타사 홈페이지 직접 크롤링
    jobs = homepage.crawl(HOMEPAGE_TARGETS)
    all_jobs.extend(jobs)

    print(f"\n[수집 완료] 총 {len(all_jobs)}건 (화이트리스트 기업만)")

    # 직무 분류
    all_jobs = classify_batch(all_jobs, use_claude=bool(ANTHROPIC_API_KEY))

    # 공고 내용 원문 수집 (신규 건만)
    print(f"[상세 수집 시작] 공고 내용 원문 크롤링 중...")
    all_jobs = detail.enrich_jobs(all_jobs)

    # Google Sheets 저장
    if not dry_run:
        rows = [_job_to_row(j) for j in all_jobs]
        saved = append_rows("RAW_DATA", rows)
        print(f"[저장] RAW_DATA에 {saved}건 저장 (중복 제외)")
    else:
        print("[DRY RUN] 저장 건너뜀")
        for j in all_jobs[:5]:
            print(f"  - {j['회사명']} | {j['포지션명']} | {j['직무']} | {j['플랫폼']}")
            print(f"    내용: {j.get('공고내용','')[:80]}...")

    return all_jobs


def run_weekly_analysis():
    """주간 집계 및 타겟/라이징 포지션 업데이트"""
    print("\n[주간 분석 시작]")
    records = get_raw_data()
    if not records:
        print("RAW_DATA 없음")
        return

    today = datetime.today()
    one_week_ago = today - timedelta(days=7)
    week_str = f"{one_week_ago.strftime('%Y.%m.%d')} - {today.strftime('%Y.%m.%d')}"

    # 직무별 주간 집계
    weekly = defaultdict(int)
    for rec in records:
        try:
            reg_date = datetime.strptime(rec.get("공고등록일", ""), "%Y-%m-%d")
        except Exception:
            continue
        if reg_date >= one_week_ago:
            job_cat = rec.get("직무") or "기타"
            weekly[job_cat] += 1

    week_label = today.strftime("%Y-W%V")
    weekly_rows = [
        [week_label, cat, cnt, "", "", ""]
        for cat, cnt in sorted(weekly.items(), key=lambda x: x[1], reverse=True)
    ]
    overwrite_sheet("WEEKLY_SUMMARY",
                    ["집계주차", "직무", "건수", "전주대비", "타겟여부", "라이징여부"],
                    weekly_rows)

    # 타겟/라이징 포지션 분석
    analysis = analyze_positions(records)

    target_rows = [
        [today.strftime("%Y-%m-%d"), t["포지션명"], t["직무"],
         t["주간건수"], "", "", t["주요브랜드"], "활성"]
        for t in analysis["target"]
    ]
    overwrite_sheet("TARGET_POSITIONS",
                    ["기준일", "포지션명", "직무", "주간건수", "전월주간평균", "전주건수", "주요브랜드", "상태"],
                    target_rows)

    rising_rows = [
        [today.strftime("%Y-%m-%d"), r["포지션명"], r["직무"],
         r["첫등장일"], r["이번달건수"], r["주요브랜드"], "", "활성"]
        for r in analysis["rising"]
    ]
    overwrite_sheet("RISING_POSITIONS",
                    ["기준일", "포지션명", "직무", "첫등장일", "이번달건수", "주요브랜드", "설명", "상태"],
                    rising_rows)

    print(f"  타겟 포지션: {len(target_rows)}개")
    print(f"  라이징 포지션: {len(rising_rows)}개")
    print(f"[주간 분석 완료] {week_str}")


def run_monthly_analysis():
    """월간 직무별 집계 + 브랜드별 통계 업데이트"""
    print("\n[월간 분석 시작]")
    records = get_raw_data()
    if not records:
        print("RAW_DATA 없음")
        return

    today = datetime.today()
    this_month = today.strftime("%Y-%m")
    last_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    monthly = defaultdict(int)
    prev_monthly = defaultdict(int)
    brand_monthly = defaultdict(lambda: defaultdict(int))

    for rec in records:
        date_str = rec.get("공고등록일", "")[:7]
        job_cat = rec.get("직무") or "기타"
        brand = rec.get("회사명", "")

        if date_str == this_month:
            monthly[job_cat] += 1
            brand_monthly[brand][job_cat] += 1
        elif date_str == last_month:
            prev_monthly[job_cat] += 1

    # MONTHLY_SUMMARY 탭
    monthly_rows = [
        [this_month, cat, cnt, cnt - prev_monthly.get(cat, 0), prev_monthly.get(cat, 0)]
        for cat, cnt in sorted(monthly.items(), key=lambda x: x[1], reverse=True)
    ]
    overwrite_sheet("MONTHLY_SUMMARY",
                    ["집계월", "직무", "건수", "전월대비", "전월건수"],
                    monthly_rows)

    # BRAND_STATS 탭
    brand_rows = []
    for brand, job_dict in sorted(brand_monthly.items(), key=lambda x: sum(x[1].values()), reverse=True):
        total = sum(job_dict.values())
        top_job = max(job_dict, key=job_dict.get) if job_dict else ""
        brand_rows.append([this_month, brand, total, "", top_job, ""])
    overwrite_sheet("BRAND_STATS",
                    ["집계월", "브랜드", "건수", "전월건수", "주요직무", "플랫폼"],
                    brand_rows)

    print(f"[월간 분석 완료] {this_month}: {len(monthly_rows)}개 직무, {len(brand_rows)}개 브랜드")


def _job_to_row(j: dict) -> list:
    return [
        j.get("수집일", ""),
        j.get("회사명", ""),
        j.get("포지션명", ""),
        j.get("직무", ""),
        j.get("경력", ""),
        j.get("고용형태", ""),
        j.get("플랫폼", ""),
        j.get("URL", ""),
        j.get("공고등록일", ""),
        j.get("공고마감일", ""),
        j.get("원문직무명", ""),
        j.get("공고내용", ""),
        j.get("중복여부", "N"),
    ]


if __name__ == "__main__":
    mode = "daily"
    dry_run = "--dry-run" in sys.argv

    for arg in sys.argv[1:]:
        if arg.startswith("--mode="):
            mode = arg.split("=")[1]
        elif arg == "--mode" and len(sys.argv) > sys.argv.index(arg) + 1:
            mode = sys.argv[sys.argv.index(arg) + 1]

    if mode == "daily" or mode == "all":
        collect_daily(dry_run=dry_run)
        run_weekly_analysis()

    if mode == "weekly":
        run_weekly_analysis()

    if mode == "monthly":
        run_monthly_analysis()

    if mode == "all":
        run_monthly_analysis()

    print("\n[완료]")
