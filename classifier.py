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
    """RAW_DATA 기반 타겟/라이징 포지션 분석

    타겟 포지션: 이번 주에 N개 이상의 회사가 동시에 채용 중인 포지션
    라이징 포지션: 이번 달에 처음 등장한 포지션 (이전 달 데이터에 없던 것)
    """
    from datetime import datetime, timedelta
    from collections import defaultdict
    from config import TARGET_THRESHOLD

    today = datetime.today()
    one_week_ago = today - timedelta(days=7)
    this_month = today.strftime("%Y-%m")

    # 공채/일반 채용 및 플랫폼 UI 노이즈 키워드
    generic_kw = ["신입", "인턴", "공채", "공개채용", "수시채용", "수시모집",
                  "상반기", "하반기", "채용전형", "대졸",
                  "greeting", "hot100", "지역별", "직업별", "역세권별",
                  "헤드헌팅", "파견대행", "공고 요청", "커리어피드",
                  "현직자 인터뷰", "스크랩", "최근본", "커뮤니티"]

    def normalize(name: str) -> str:
        return re.sub(r"\s+", " ", name.strip().lower())

    def normalize_company(name: str) -> str:
        """회사명 정규화 — (주), ㈜ 등 제거하여 같은 회사를 하나로 집계"""
        name = re.sub(r'주식회사|㈜|\(주\)|\(유\)|유한회사|\s|\(|\)', '', name)
        return name.lower()

    # ── 타겟 포지션 ──────────────────────────────────────────
    # 이번 주 등록 공고에서 포지션명별 채용 회사 수 집계
    weekly = defaultdict(lambda: {"직무": "", "회사들": set()})

    for rec in records:
        pos = normalize(rec.get("포지션명", ""))
        if not pos or any(kw in pos for kw in generic_kw):
            continue
        try:
            reg_date = datetime.strptime(rec.get("공고등록일", ""), "%Y-%m-%d")
        except Exception:
            continue
        if reg_date < one_week_ago:
            continue
        weekly[pos]["직무"] = rec.get("직무", "기타")
        weekly[pos]["회사들"].add(normalize_company(rec.get("회사명", "")))

    target = []
    for pos, info in weekly.items():
        company_count = len(info["회사들"])
        if company_count >= TARGET_THRESHOLD:
            target.append({
                "포지션명": pos,
                "직무": info["직무"],
                "주간건수": company_count,       # 채용 회사 수
                "주요브랜드": ", ".join(list(info["회사들"])[:5]),
            })
    target.sort(key=lambda x: x["주간건수"], reverse=True)

    # ── 라이징 포지션 ─────────────────────────────────────────
    # 이전 달까지 한 번도 등장한 적 없는 포지션이 이번 달 새로 등장한 것
    known = set()      # 이전 달 이전 데이터에 있던 포지션명 집합
    this_month_data = defaultdict(lambda: {"직무": "", "회사들": set(), "첫등장일": None})

    for rec in records:
        pos = normalize(rec.get("포지션명", ""))
        if not pos or any(kw in pos for kw in generic_kw):
            continue
        try:
            reg_date = datetime.strptime(rec.get("공고등록일", ""), "%Y-%m-%d")
        except Exception:
            continue

        month_str = reg_date.strftime("%Y-%m")
        if month_str < this_month:
            known.add(pos)
        elif month_str == this_month:
            d = this_month_data[pos]
            d["직무"] = rec.get("직무", "기타")
            d["회사들"].add(normalize_company(rec.get("회사명", "")))
            if d["첫등장일"] is None or reg_date < d["첫등장일"]:
                d["첫등장일"] = reg_date

    rising = []
    for pos, info in this_month_data.items():
        if pos in known:
            continue  # 이전 달에도 있었던 포지션
        if len(info["회사들"]) < 2:
            continue  # 1개 회사만 올린 건 노이즈로 제외
        rising.append({
            "포지션명": pos,
            "직무": info["직무"],
            "첫등장일": info["첫등장일"].strftime("%Y-%m-%d") if info["첫등장일"] else "",
            "이번달건수": len(info["회사들"]),   # 채용 회사 수
            "주요브랜드": ", ".join(list(info["회사들"])[:5]),
        })
    rising.sort(key=lambda x: x["이번달건수"], reverse=True)

    return {"target": target, "rising": rising}
