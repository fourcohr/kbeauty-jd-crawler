"""K뷰티 브랜드 검증 모듈"""
import re
from config import TOP30_COMPANIES, HOMEPAGE_TARGETS, ANTHROPIC_API_KEY

# 알려진 K뷰티 브랜드 화이트리스트 (포털 크롤링 결과 검증용)
KNOWN_BEAUTY_BRANDS = set(TOP30_COMPANIES + [t["회사명"] for t in HOMEPAGE_TARGETS] + [
    # 주요 K뷰티 브랜드 추가
    "아모레퍼시픽", "LG생활건강", "이니스프리", "에뛰드", "헤라", "설화수", "라네즈",
    "미샤", "에이블씨엔씨", "토니모리", "더샘", "네이처리퍼블릭", "스킨푸드", "잇츠스킨",
    "클리오", "페리페라", "구달", "잇츠한불", "코리아나", "한국화장품",
    "에이피알", "메디힐", "제이준", "마녀공장", "조선미녀", "토리든", "라운드랩",
    "달바", "달바글로벌", "구다이글로벌", "코스알엑스", "COSRX", "실리콘투",
    "브이티", "VT", "스킨1004", "닥터지", "이지듀", "CNP", "셀퓨전씨",
    "닥터자르트", "아누아", "넘버즈인", "원씽", "아비브", "ABIB",
    "포컴퍼니", "포렌코즈", "네이밍", "바솔", "네이처컬렉션",
    "올리브영", "씨제이올리브영", "CJ올리브영",
    "더파운더즈", "에프앤코", "크레이버코퍼레이션",
    "한국콜마", "코스맥스", "콜마비앤에이치",  # ODM이지만 업계 주요 기업
    "애터미", "웰코스", "바이오코즈", "세화피앤씨",
    "이엔씨기술", "나우코스", "에이씨티", "케어젠",
    "화장품", "뷰티", "코스메틱",  # 회사명에 이 단어가 포함되면 뷰티 관련
])

# 확실히 제외할 비뷰티 키워드 (회사명에 포함 시 제외)
EXCLUDE_KEYWORDS = [
    "건설", "부동산", "의료", "병원", "클리닉", "약국", "제약",  # 단, 화장품 제약은 예외
    "자동차", "자동차부품", "조선", "철강", "기계",
    "금융", "은행", "보험", "증권", "투자",
    "교육", "학원", "학교", "대학",
    "식품", "음식", "레스토랑", "카페",
    "IT", "소프트웨어", "테크놀로지", "시스템즈",
    "물류", "운송", "배송",
    "패션", "의류",  # 뷰티와 겹치는 경우가 있어 주의
]

# 뷰티 관련 확인 키워드
BEAUTY_KEYWORDS = [
    "화장품", "코스메틱", "cosmetic", "beauty", "뷰티", "스킨케어", "skincare",
    "색조", "메이크업", "makeup", "헤어", "바디", "향수", "퍼퓨", "perfume",
    "클렌징", "에센스", "세럼", "로션", "크림",
]


def normalize(name: str) -> str:
    return re.sub(r"[\s\(\)주식회사㈜(주)]", "", name).lower()


def is_beauty_brand(company: str) -> bool:
    """회사명 기반 K뷰티 브랜드 여부 판단 (1차: 키워드, 2차: 화이트리스트)"""
    c_norm = normalize(company)

    # 화이트리스트 정확 매칭
    for known in KNOWN_BEAUTY_BRANDS:
        if normalize(known) in c_norm or c_norm in normalize(known):
            return True

    # 회사명에 뷰티 키워드 포함 → True
    c_lower = company.lower()
    for kw in BEAUTY_KEYWORDS:
        if kw in c_lower:
            return True

    # 명확히 비뷰티 키워드 포함 → False
    for kw in EXCLUDE_KEYWORDS:
        if kw in company:
            return False

    # 판단 불가 → True (보수적으로 포함)
    return True


def filter_jobs(jobs: list[dict], use_claude: bool = True) -> tuple[list[dict], list[dict]]:
    """
    jobs를 K뷰티 브랜드 여부로 분류
    Returns: (beauty_jobs, excluded_jobs)
    """
    beauty, excluded = [], []

    for job in jobs:
        company = job.get("회사명", "")
        if is_beauty_brand(company):
            beauty.append(job)
        else:
            excluded.append(job)

    # Claude API로 불확실한 케이스 재검토 (excluded 중 판단이 애매한 것들)
    if use_claude and ANTHROPIC_API_KEY and excluded:
        reclassified = _claude_classify(excluded)
        beauty.extend(reclassified["beauty"])
        excluded = reclassified["excluded"]

    return beauty, excluded


def _claude_classify(jobs: list[dict]) -> dict:
    """Claude API로 K뷰티 브랜드 여부 재분류"""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # 회사명 중복 제거
        companies = list({j["회사명"] for j in jobs})
        beauty_set = set()

        # 50개씩 배치
        batch_size = 50
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            prompt = f"""아래 회사들이 K뷰티 화장품 브랜드사(브랜드를 직접 운영하는 회사)인지 판단해주세요.
포함: 화장품/스킨케어/색조/헤어케어 브랜드사, 뷰티 플랫폼, H&B 스토어
제외: 단순 ODM/OEM 제조사, IT회사, 건설사, 식품사, 의료기관 등

회사 목록:
{chr(10).join(f'{j+1}. {c}' for j, c in enumerate(batch))}

각 번호에 대해 Y(K뷰티 관련) 또는 N(비관련)만 한 줄씩 출력:"""

            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            lines = msg.content[0].text.strip().split("\n")
            for idx, line in enumerate(lines):
                if idx < len(batch):
                    answer = line.strip().upper()
                    if "Y" in answer:
                        beauty_set.add(batch[idx])

        beauty_jobs = [j for j in jobs if j["회사명"] in beauty_set]
        excluded_jobs = [j for j in jobs if j["회사명"] not in beauty_set]
        print(f"[브랜드 검증] Claude 재분류: {len(beauty_jobs)}건 포함, {len(excluded_jobs)}건 제외")
        return {"beauty": beauty_jobs, "excluded": excluded_jobs}

    except Exception as e:
        print(f"[브랜드 검증] Claude API 오류: {e}")
        return {"beauty": [], "excluded": jobs}
