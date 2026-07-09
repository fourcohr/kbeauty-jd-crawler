/**
 * 잡플래닛 리뷰 알림 자동화 - Google Apps Script (Slack Bot 방식)
 *
 * [설정 방법]
 * 1. api.slack.com/apps → 새 앱 생성 → Bot Token 발급
 * 2. SLACK_BOT_TOKEN, SLACK_CHANNEL 입력
 * 3. setupTrigger() 함수 실행 (최초 1회) → Gmail 권한 허용
 *
 * [발신자 확인]
 * 실제 수신 이메일: do_not_reply@jobplanet.co.kr
 * 제목 패턴: [잡플래닛] (주)포컴퍼니의 면접후기가 등록되었습니다.
 *            [잡플래닛] (주)포컴퍼니의 기업리뷰가 등록되었습니다.
 */

const CONFIG = {
  // ★ 필수 1: Slack Bot Token (xoxb- 로 시작)
  SLACK_BOT_TOKEN: "xoxb-XXXXXXXXX-XXXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXX",

  // ★ 필수 2: 알림 받을 채널명 또는 채널 ID
  //   채널명: "#hr-알림"  /  채널 ID: "C01234ABCDE" (채널 우클릭 → 링크 복사에서 확인)
  SLACK_CHANNEL: "#잡플래닛-리뷰알림",

  // 잡플래닛 발신자 (이메일 캡처 기준)
  GMAIL_SEARCH_QUERY: "from:(do_not_reply@jobplanet.co.kr) is:unread label:inbox",

  // 처리 완료 라벨 (자동 생성)
  PROCESSED_LABEL: "잡플래닛/처리완료",
};


// ── 메인 ──────────────────────────────────────────────────────────────────

function checkJobplanetReviews() {
  const label = getOrCreateLabel(CONFIG.PROCESSED_LABEL);
  const threads = GmailApp.search(CONFIG.GMAIL_SEARCH_QUERY);

  threads.forEach(thread => {
    thread.getMessages().forEach(msg => {
      if (!msg.isUnread()) return;

      const parsed = parseJobplanetEmail(
        msg.getSubject(),
        msg.getPlainBody(),
        msg.getBody(),       // HTML body — 링크 추출용
        msg.getDate()
      );

      sendSlackAlert(parsed);
      msg.markRead();
    });
    thread.addLabel(label);
  });
}


// ── 이메일 파싱 ────────────────────────────────────────────────────────────

function parseJobplanetEmail(subject, plainBody, htmlBody, date) {
  // 리뷰 타입 판별 (면접후기 / 기업리뷰)
  const reviewType = subject.includes("면접후기") ? "면접후기" : "기업리뷰";

  // 리뷰 본문 요약 추출
  // 이메일 본문 패턴: "• 서류 접수 후 일주일 후에..." 형태의 bullet 라인
  const summaryLines = extractSummaryLines(plainBody, reviewType);

  // 작성일 추출 (예: 작성일: 26.06 → 2026.06)
  const dateText = extractWrittenDate(plainBody, date);

  // 잡플래닛 링크 추출 (HTML body에서 기업관리센터 URL)
  const link = extractLink(htmlBody);

  return { reviewType, summaryLines, dateText, link };
}

function extractSummaryLines(body, reviewType) {
  const lines = body.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const results = [];

  // "새로 등록된 면접후기" 또는 "새로 등록된 기업리뷰" 섹션 이후 bullet 수집
  let inSection = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.includes("새로 등록된")) {
      inSection = true;
      continue;
    }

    if (inSection) {
      // bullet 포인트 라인 (•, -, *, · 로 시작하거나 내용 있는 라인)
      if (/^[•\-\*·]/.test(line)) {
        const content = line.replace(/^[•\-\*·]\s*/, "").trim();
        if (content && !content.startsWith("작성일")) {
          results.push(content.slice(0, 200));
        }
      }
      // 본문 내용이 bullet 없이 바로 오는 경우
      else if (results.length === 0 && line.length > 10 && !line.includes("작성일") && !line.includes("기업관리")) {
        results.push(line.slice(0, 200));
      }
      // 구분선 또는 다른 섹션 도달 시 중단
      else if (line.startsWith("*") || line.includes("기업관리센터") || line.includes("전체내용")) {
        break;
      }
    }
  }

  // fallback: 아무것도 못 잡으면 본문 상단 의미있는 첫 줄 사용
  if (results.length === 0) {
    const fallback = lines.find(l =>
      l.length > 15 &&
      !l.includes("잡플래닛") &&
      !l.includes("포컴퍼니") &&
      !l.includes("등록되었") &&
      !l.includes("댓글") &&
      !l.includes("작성일") &&
      !l.includes("기업관리")
    );
    if (fallback) results.push(fallback.slice(0, 200));
  }

  return results;
}

function extractWrittenDate(body, fallbackDate) {
  // "작성일: 26.06" 패턴 추출
  const match = body.match(/작성일\s*[:\s]\s*(\d{2,4}\.\d{2}(?:\.\d{2})?)/);
  if (match) return match[1];

  // fallback: 이메일 수신일
  const d = new Date(fallbackDate);
  return `${String(d.getFullYear()).slice(2)}.${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function extractLink(htmlBody) {
  // "기업관리센터 바로가기" 버튼 href 추출
  const match = htmlBody.match(/href="(https?:\/\/[^"]*jobplanet\.co\.kr[^"]*)"/i);
  return match ? match[1] : "https://www.jobplanet.co.kr/companies";
}


// ── Slack 알림 전송 ────────────────────────────────────────────────────────

function sendSlackAlert(info) {
  if (!CONFIG.SLACK_BOT_TOKEN || CONFIG.SLACK_BOT_TOKEN.includes("XXXXXXXXX")) {
    Logger.log("⚠️ SLACK_BOT_TOKEN 을 설정해주세요.");
    return;
  }

  const isInterview = info.reviewType === "면접후기";
  const typeLabel   = isInterview ? "면접리뷰" : "기업리뷰";
  const headerText  = isInterview
    ? "🚨 잡플래닛 새 <면접리뷰> 등록 알림"
    : "⭐ 잡플래닛 새 <기업리뷰> 등록 알림";

  // 요약 bullet 조합
  const summaryText = info.summaryLines.length > 0
    ? info.summaryLines.map(l => `• ${l}`).join("\n")
    : "• (요약 내용 없음)";

  const blocks = [
    {
      type: "header",
      text: { type: "plain_text", text: headerText, emoji: true }
    },
    {
      type: "section",
      text: {
        type: "mrkdwn",
        text: `*요약:*\n${summaryText}\n작성일: ${info.dateText}`
      }
    },
    {
      type: "section",
      text: {
        type: "mrkdwn",
        text: `👉 <${info.link}|${typeLabel} 확인하기>`
      }
    }
  ];

  UrlFetchApp.fetch("https://slack.com/api/chat.postMessage", {
    method: "post",
    headers: { "Authorization": "Bearer " + CONFIG.SLACK_BOT_TOKEN },
    contentType: "application/json",
    payload: JSON.stringify({ channel: CONFIG.SLACK_CHANNEL, blocks }),
  });
}


// ── 유틸 ──────────────────────────────────────────────────────────────────

function getOrCreateLabel(name) {
  return GmailApp.getUserLabelByName(name) || GmailApp.createLabel(name);
}


// ── 트리거 설정 (최초 1회 실행) ───────────────────────────────────────────

function setupTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === "checkJobplanetReviews")
    .forEach(t => ScriptApp.deleteTrigger(t));

  // 15분마다 실행 — 이메일 도착 후 최대 15분 이내 Slack 알림
  ScriptApp.newTrigger("checkJobplanetReviews")
    .timeBased()
    .everyMinutes(15)
    .create();

  Logger.log("✅ 트리거 설정 완료: 15분마다 실행");
}

// 즉시 테스트 실행
function testRun() {
  checkJobplanetReviews();
}
