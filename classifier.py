"""직무 분류 로직 - 키워드 우선, Claude API 보완"""
import re
from config import JOB_CATEGORIES

# 키워드 → 직무 매핑
KEYWORD_MAP = {
    "개발": ["개발자", "engineer", "developer", "백엔드", "프론트엔드", "풀스택", "iOS", "Android",
              "데이터", "ML", "AI", "인프라", "DevOps", "QA", "firmware"],
    "경영관리": ["인사", "HR", "재무", "회계", "법무", "총무", "경영지원", "CFO", "COO", "구매", "감사"],
    "기획": ["기획", "PM", "PO", "서비스기획", "사업기획", "전략", "UX", "리서치"],
    "디자인": ["디자인", "designer", "UI", "그래픽", "비주얼", "패키지", "VMD", "브랜딩"],
    "마케팅": ["마케팅", "marketing", "퍼포먼스", "SNS", "콘텐츠", "브랜드마케팅", "CRM",
               "광고", "MD커머스", "그로스", "SEO", "influencer", "인플루언서", "커뮤니케이션"],
    "상품기획": ["상품기획", "MD", "머천다이저", "제품기획", "R&D", "연구개발", "원료", "포뮬레이션",
                 "제품개발", "코스메틱 개발"],
    "영업": ["영업", "sales", "세일즈", "거래처", "바이어", "수출", "무역", "해외영업", "국내영업",
             "B2B", "B2C", "채널", "유통"],
    "제작": ["촬영", "편집", "영상", "포토", "스튜디오", "PD", "제작", "영상편집"],
    "SCM": ["SCM", "물류", "공급망", "생산관리", "품질", "QC", "구매", "재고", "CS", "고객서비스",
             "배송", "창고", "포워딩"],
}


def classify_by_keyword(position: str) -> str:
    """포지션명 키워드로 직무 분류"""
    pos_lower = position.lower()
    for category, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw.lower() in pos_lower:
                return category
    return "기타"


def classify_batch(jobs: list[dict], use_claude: bool = False) -> list[dict]:
    """직무 분류 일괄 처리"""
    for job in jobs:
        if not job.get("직무"):
            job["직무"] = classify_by_keyword(job.get("포지션명", ""))

    # Claude API로 '기타' 분류 보완 (선택)
    if use_claude:
        others = [j for j in jobs if j["직무"] == "기타"]
        if others:
            _classify_with_claude(others)

    return jobs


def _classify_with_claude(jobs: list[dict]):
    """Claude API로 직무 분류 보완 (기타 분류된 것들)"""
    try:
        import anthropic
        from config import ANTHROPIC_API_KEY
        if not ANTHROPIC_API_KEY:
            return

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        categories_str = ", ".join(JOB_CATEGORIES)

        # 최대 50개씩 배치 처리
        batch_size = 50
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            positions = "\n".join([f"{idx+1}. {j['포지션명']}" for idx, j in enumerate(batch)])

            prompt = f"""K뷰티 화장품 회사의 채용 포지션들을 아래 직무 카테고리 중 하나로 분류해주세요.

카테고리: {categories_str}

포지션 목록:
{positions}

각 번호에 대해 카테고리만 한 줄씩 출력하세요. 예:
1. 마케팅
2. 개발
"""
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            lines = msg.content[0].text.strip().split("\n")
            for idx, line in enumerate(lines):
                if idx < len(batch):
                    match = re.search(r"[\.\s]+(.+)", line)
                    if match:
                        category = match.group(1).strip()
                        if category in JOB_CATEGORIES:
                            batch[idx]["직무"] = category
    except Exception as e:
        print(f"[분류] Claude API 오류: {e}")


# 타겟/라이징 포지션 분석
def analyze_positions(records: list[dict]) -> dict:
    """RAW_DATA 기반 타겟/라이징 포지션 분석"""
    from datetime import datetime, timedelta
    from collections import defaultdict
    from config import TARGET_THRESHOLD, RISING_LOOKBACK_DAYS

    today = datetime.today()
    one_week_ago = today - timedelta(days=7)
    one_month_ago = today - timedelta(days=RISING_LOOKBACK_DAYS)

    # 포지션명 정규화 (소문자 + 공백 제거)
    def normalize(name: str) -> str:
        return re.sub(r"\s+", " ", name.strip().lower())

    weekly_counts = defaultdict(lambda: {"건수": 0, "직무": "", "브랜드": set()})
    monthly_first_seen = {}  # 포지션명 -> 첫 등장일

    for rec in records:
        pos = normalize(rec.get("포지션명", ""))
        if not pos:
            continue

        # 등록일 파싱
        try:
            reg_date = datetime.strptime(rec.get("공고등록일", ""), "%Y-%m-%d")
        except Exception:
            reg_date = today

        company = rec.get("회사명", "")
        job_cat = rec.get("직무", "기타")

        # 주간 집계
        if reg_date >= one_week_ago:
            weekly_counts[pos]["건수"] += 1
            weekly_counts[pos]["직무"] = job_cat
            weekly_counts[pos]["브랜드"].add(company)

        # 첫 등장일 추적 (전체 기간)
        if pos not in monthly_first_seen or reg_date < monthly_first_seen[pos]:
            monthly_first_seen[pos] = reg_date

    # 타겟 포지션: 주간 10건 이상
    target = []
    for pos, info in weekly_counts.items():
        if info["건수"] >= TARGET_THRESHOLD:
            target.append({
                "포지션명": pos,
                "직무": info["직무"],
                "주간건수": info["건수"],
                "주요브랜드": ", ".join(list(info["브랜드"])[:5]),
            })
    target.sort(key=lambda x: x["주간건수"], reverse=True)

    # 공개채용/수시채용/신입인턴 등 일반 채용공고 제외 키워드
    generic_kw = ["신입", "인턴", "공채", "공개채용", "수시채용", "수시모집",
                  "상반기", "하반기", "채용전형", "대졸"]

    # 라이징 포지션: 최근 1개월 내 처음 등장한 포지션 (일반 채용공고 제외)
    rising = []
    for pos, first_date in monthly_first_seen.items():
        if any(kw in pos for kw in generic_kw):
            continue
        if first_date >= one_month_ago:
            info = weekly_counts.get(pos, {})
            rising.append({
                "포지션명": pos,
                "직무": info.get("직무", "기타"),
                "첫등장일": first_date.strftime("%Y-%m-%d"),
                "이번달건수": sum(
                    1 for r in records
                    if normalize(r.get("포지션명", "")) == pos
                ),
                "주요브랜드": ", ".join(list(info.get("브랜드", set()))[:5]),
            })
    rising.sort(key=lambda x: x["이번달건수"], reverse=True)

    return {"target": target, "rising": rising}
