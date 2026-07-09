/**
 * K뷰티 채용 트렌드 DB - Google Apps Script
 *
 * [배포 방법]
 * 1. Google Sheets 메뉴 → 확장 프로그램 → Apps Script
 * 2. 이 코드 전체를 붙여넣기
 * 3. 저장(Ctrl+S)
 * 4. 배포 → 새 배포 → 유형: 웹 앱
 * 5. 실행 계정: 본인 / 액세스 권한: 모든 사용자
 * 6. 배포 → URL 복사 → JD_Trend_Report_2026.html의 APPS_SCRIPT_URL에 붙여넣기
 */

const SPREADSHEET_ID = "1NUj12duoH3DF0HQxAWRRC81uVEUs9PY9GJLgqdSusI8";

function doGet(e) {
  const callback = e && e.parameter && e.parameter.callback;
  const output = buildResponse();
  const json = JSON.stringify(output);

  const response = callback
    ? ContentService.createTextOutput(callback + "(" + json + ")").setMimeType(ContentService.MimeType.JAVASCRIPT)
    : ContentService.createTextOutput(json).setMimeType(ContentService.MimeType.JSON);

  return response;
}

function buildResponse() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const now = new Date().toISOString();

  // RAW_DATA 읽기
  const rawSheet = ss.getSheetByName("RAW_DATA");
  const rawData = rawSheet ? sheetToObjects(rawSheet) : [];

  // 주간 범위
  const today = new Date();
  const oneWeekAgo = new Date(today);
  oneWeekAgo.setDate(today.getDate() - 7);
  const weeklyRange = `${formatDate(oneWeekAgo)} – ${formatDate(today)}`;

  // 주간 공고 필터 (KPI용)
  const weeklyJobs = rawData
    .filter(r => {
      const d = new Date(r["공고등록일"] || r["수집일"]);
      return d >= oneWeekAgo;
    })
    .slice(0, 200)
    .map(r => ({
      직무: r["직무"] || "기타",
      브랜드: r["회사명"] || "",
      포지션명: r["포지션명"] || "",
      경력: r["경력"] || "",
      플랫폼: r["플랫폼"] || "",
      등록일: r["공고등록일"] || r["수집일"] || "",
      URL: r["URL"] || "#",
    }));

  // 전체 공고 (HTML 클라이언트 날짜 필터용, 최근 90일)
  const ninetyDaysAgo = new Date(today);
  ninetyDaysAgo.setDate(today.getDate() - 90);
  const allJobs = rawData
    .filter(r => {
      const d = new Date(r["공고등록일"] || r["수집일"]);
      return d >= ninetyDaysAgo;
    })
    .map(r => ({
      직무: r["직무"] || "기타",
      브랜드: r["회사명"] || "",
      포지션명: r["포지션명"] || "",
      경력: r["경력"] || "",
      플랫폼: r["플랫폼"] || "",
      등록일: r["공고등록일"] || r["수집일"] || "",
      URL: r["URL"] || "#",
    }));

  // 타겟 포지션
  const targetSheet = ss.getSheetByName("TARGET_POSITIONS");
  const targetRaw = targetSheet ? sheetToObjects(targetSheet) : [];
  const targetPositions = targetRaw
    .filter(r => r["상태"] === "활성")
    .slice(0, 20)
    .map(r => ({
      포지션명: r["포지션명"] || "",
      직무: r["직무"] || "",
      주간건수: Number(r["주간건수"]) || 0,
      전월주간평균: Number(r["전월주간평균"]) || 0,
      전주건수: Number(r["전주건수"]) || 0,
      주요브랜드: (r["주요브랜드"] || "").split(",").map(s => s.trim()).filter(Boolean),
    }));

  // 라이징 포지션
  const risingSheet = ss.getSheetByName("RISING_POSITIONS");
  const risingRaw = risingSheet ? sheetToObjects(risingSheet) : [];
  const risingPositions = risingRaw
    .filter(r => r["상태"] === "활성")
    .slice(0, 20)
    .map(r => ({
      포지션명: r["포지션명"] || "",
      직무: r["직무"] || "",
      첫등장: r["첫등장일"] || "",
      이번달건수: Number(r["이번달건수"]) || 0,
      주요브랜드: (r["주요브랜드"] || "").split(",").map(s => s.trim()).filter(Boolean),
      설명: r["설명"] || "",
    }));

  // 월간 직무 통계
  const monthlySheet = ss.getSheetByName("MONTHLY_SUMMARY");
  const monthlyRaw = monthlySheet ? sheetToObjects(monthlySheet) : [];
  const thisMonth = formatMonth(today);
  const monthlyJobStats = monthlyRaw
    .filter(r => r["집계월"] === thisMonth)
    .map(r => ({
      직무: r["직무"] || "",
      건수: Number(r["건수"]) || 0,
      전월: Number(r["전월건수"]) || 0,
    }));

  // 브랜드별 통계
  const brandSheet = ss.getSheetByName("BRAND_STATS");
  const brandRaw = brandSheet ? sheetToObjects(brandSheet) : [];
  const brandStats = brandRaw
    .filter(r => r["집계월"] === thisMonth)
    .slice(0, 30)
    .map((r, i) => ({
      순위: i + 1,
      브랜드: r["브랜드"] || "",
      이번달: Number(r["건수"]) || 0,
      전월: Number(r["전월건수"]) || 0,
      주요직무: r["주요직무"] || "",
    }));

  // 스킬 트렌드
  const skillSheet = ss.getSheetByName("SKILL_TRENDS");
  const skillRaw = skillSheet ? sheetToObjects(skillSheet) : [];
  const skillUp = skillRaw
    .filter(r => r["집계월"] === thisMonth && r["방향"] === "상승")
    .slice(0, 10)
    .map(r => ({
      키워드: r["키워드"] || "",
      건수: Number(r["건수"]) || 0,
      증가율: Number(r["증가율"]) || 0,
    }));
  const skillDown = skillRaw
    .filter(r => r["집계월"] === thisMonth && r["방향"] === "하락")
    .slice(0, 5)
    .map(r => ({
      키워드: r["키워드"] || "",
      건수: Number(r["건수"]) || 0,
      증가율: Number(r["증가율"]) || 0,
    }));

  // 요약 통계
  const totalJobs = rawData.length;
  const newThisWeek = weeklyJobs.length;
  const activeBrands = new Set(rawData.map(r => r["회사명"])).size;

  return {
    updatedAt: now,
    summary: {
      totalJobs,
      newThisWeek,
      weekDiff: `+${newThisWeek}`,
      targetCount: targetPositions.length,
      risingCount: risingPositions.length,
      activeBrands,
    },
    weeklyRange,
    weeklyJobs,
    allJobs,
    targetPositions,
    risingPositions,
    monthlyJobStats,
    brandStats,
    skillTrends: { up: skillUp, down: skillDown },
  };
}

// ───── 유틸 ─────

function sheetToObjects(sheet) {
  const values = sheet.getDataRange().getValues();
  if (values.length < 2) return [];
  const headers = values[0];
  const tz = 'Asia/Seoul';
  return values.slice(1).map(row => {
    const obj = {};
    headers.forEach((h, i) => {
      const v = row[i];
      if (v instanceof Date) {
        obj[h] = Utilities.formatDate(v, tz, 'yyyy-MM-dd');
      } else {
        obj[h] = v !== undefined ? String(v) : "";
      }
    });
    return obj;
  });
}

function formatDate(d) {
  return `${d.getFullYear()}.${pad(d.getMonth()+1)}.${pad(d.getDate())}`;
}

function formatMonth(d) {
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}`;
}

function pad(n) { return String(n).padStart(2, "0"); }
