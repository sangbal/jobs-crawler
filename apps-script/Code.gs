/**
 * 채용 공고 뉴스레터 발송 스크립트
 * Google Apps Script로 실행
 */

// 설정
const CONFIG = {
  SPREADSHEET_ID: '1CkE4d64oGFDb1V_d9B2bByl7rj9lR-8u9Ux2fbOe2DA',
  EMAIL_TO: 'sangbal.h@gmail.com',
  EMAIL_SUBJECT_PREFIX: '📋 채용 공고 데일리 리포트',
  SECRET_TOKEN: 'offRIGEUUqBf27NFTpoFe5Wh5DSROo_BmrNND11rlSw'
};

// 회사 그룹 정의
const COMPANY_GROUPS = {
  '카카오': ['카카오', '카카오페이', '카카오 게임즈', '카카오헬스케어', '카카오엔터프라이즈', 'AXZ'],
  '토스': ['토스', '토스플레이스', '토스인슈어런스', '토스뱅크', '토스페이먼츠', '토스씨엑스'],
  '네이버': ['NAVER', 'NAVER WEBTOON', 'NAVER FINANCIAL', 'NAVER Cloud'],
  '쿠팡': ['쿠팡'],
  '당근': ['당근', '당근마켓', '당근페이'],
  '배민': ['우아한형제들']
};

/**
 * HTTP GET 요청 핸들러 (웹 앱 트리거용)
 */
function doGet(e) {
  // 토큰 검증
  const token = e.parameter.token;
  if (token !== CONFIG.SECRET_TOKEN) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      error: 'Unauthorized'
    })).setMimeType(ContentService.MimeType.JSON);
  }

  try {
    const result = sendDailyReport();
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      message: result
    })).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      error: error.message
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * 수동 실행용 함수
 */
function sendDailyReport() {
  const data = getSpreadsheetData();
  const yesterday = getYesterdayString();

  // 어제 수집된 공고 필터링 (09시에 발송하므로 어제 신규가 더 의미있음)
  const newJobs = data.filter(job => {
    const collectDateStr = String(job.collectDate || '');
    return collectDateStr.startsWith(yesterday);
  });

  // 최근 7일 이내 등록된 공고
  const recentJobs = getRecentJobs(data);

  // 마감 임박 공고 (7일 이내)
  const urgentJobs = getUrgentJobs(data);

  // 회사별 통계
  const stats = getCompanyStats(data);

  // 이메일 HTML 생성
  const html = generateEmailHTML(newJobs, urgentJobs, stats, data.length, recentJobs);

  // 이메일 발송
  const today = getTodayString();
  const subject = `${CONFIG.EMAIL_SUBJECT_PREFIX} - ${today}`;
  MailApp.sendEmail({
    to: CONFIG.EMAIL_TO,
    subject: subject,
    htmlBody: html
  });

  return `이메일 발송 완료: 신규 ${newJobs.length}건, 최근7일 ${recentJobs.length}건, 마감임박 ${urgentJobs.length}건`;
}

// 회사별 시트 이름
const COMPANY_SHEETS = ['카카오', '토스', '네이버', '쿠팡', '당근', '배민'];

/**
 * 스프레드시트 데이터 가져오기 (모든 회사 시트 통합)
 */
function getSpreadsheetData() {
  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const data = [];

  for (const sheetName of COMPANY_SHEETS) {
    try {
      const sheet = ss.getSheetByName(sheetName);
      if (!sheet) continue;

      const values = sheet.getDataRange().getValues();
      if (values.length <= 1) continue;  // 헤더만 있는 경우

      // 헤더 제외하고 데이터 파싱
      // 컬럼 순서: 회사, 직무명, 등록일, 마감일, URL, 직군, 근무지, 고용형태, 공고ID, 수집일시
      for (let i = 1; i < values.length; i++) {
        const row = values[i];
        if (!row[8]) continue;  // 공고ID가 없으면 건너뛰기
        data.push({
          company: String(row[0] || ''),
          title: String(row[1] || ''),
          openDate: String(row[2] || ''),
          closeDate: String(row[3] || ''),
          url: String(row[4] || ''),
          category: String(row[5] || ''),
          location: String(row[6] || ''),
          employmentType: String(row[7] || ''),
          id: String(row[8] || ''),
          collectDate: String(row[9] || '')
        });
      }
    } catch (e) {
      console.log(`${sheetName} 시트 읽기 실패: ${e.message}`);
    }
  }

  return data;
}

/**
 * 오늘 날짜 문자열 (YYYY-MM-DD)
 */
function getTodayString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * 어제 날짜 문자열 (YYYY-MM-DD)
 */
function getYesterdayString() {
  const now = new Date();
  now.setDate(now.getDate() - 1);
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * 마감 임박 공고 (7일 이내)
 */
function getUrgentJobs(data) {
  const today = new Date();
  const weekLater = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);

  return data.filter(job => {
    if (!job.closeDate || job.closeDate === '상시채용') return false;
    try {
      const closeDate = new Date(job.closeDate);
      return closeDate >= today && closeDate <= weekLater;
    } catch {
      return false;
    }
  }).sort((a, b) => new Date(a.closeDate) - new Date(b.closeDate));
}

/**
 * 최근 7일 이내 등록된 공고
 */
function getRecentJobs(data) {
  const today = new Date();
  const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  return data.filter(job => {
    if (!job.openDate || job.openDate === '상시채용') return false;
    try {
      const openDate = new Date(job.openDate);
      return openDate >= weekAgo && openDate <= today;
    } catch {
      return false;
    }
  }).sort((a, b) => new Date(b.openDate) - new Date(a.openDate));
}

/**
 * 회사 그룹별 통계
 */
function getCompanyStats(data) {
  const stats = {};

  for (const [groupName, companies] of Object.entries(COMPANY_GROUPS)) {
    const count = data.filter(job =>
      companies.some(c => job.company.includes(c))
    ).length;
    stats[groupName] = count;
  }

  return stats;
}

/**
 * 날짜를 친절한 형식으로 변환 (예: 2월 1일 (토))
 */
function formatDateFriendly(dateValue) {
  if (!dateValue || dateValue === '상시채용') return '상시채용';

  try {
    const date = new Date(dateValue);
    if (isNaN(date.getTime())) return String(dateValue);

    const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const weekday = weekdays[date.getDay()];

    return `${month}월 ${day}일 (${weekday})`;
  } catch {
    return String(dateValue);
  }
}

/**
 * 회사를 그룹으로 분류
 */
function getCompanyGroup(company) {
  for (const [groupName, companies] of Object.entries(COMPANY_GROUPS)) {
    if (companies.some(c => company.includes(c))) {
      return groupName;
    }
  }
  return '기타';
}

/**
 * 이메일 HTML 생성
 */
function generateEmailHTML(newJobs, urgentJobs, stats, totalCount, recentJobs) {
  const today = getTodayString();

  // 신규 공고를 회사 그룹별로 정리
  const newJobsByGroup = {};
  for (const job of newJobs) {
    const group = getCompanyGroup(job.company);
    if (!newJobsByGroup[group]) newJobsByGroup[group] = [];
    newJobsByGroup[group].push(job);
  }

  // 최근 7일 공고를 회사 그룹별로 정리
  const recentJobsByGroup = {};
  for (const job of (recentJobs || [])) {
    const group = getCompanyGroup(job.company);
    if (!recentJobsByGroup[group]) recentJobsByGroup[group] = [];
    recentJobsByGroup[group].push(job);
  }

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
  <div style="max-width: 600px; margin: 0 auto; padding: 20px;">

    <!-- 헤더 -->
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px 16px 0 0; padding: 32px; text-align: center;">
      <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 600;">📋 채용 공고 데일리 리포트</h1>
      <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">${today}</p>
    </div>

    <!-- 요약 카드 -->
    <div style="background: white; padding: 24px; border-bottom: 1px solid #eee;">
      <div style="display: flex; justify-content: space-around; text-align: center;">
        <div style="flex: 1;">
          <div style="font-size: 32px; font-weight: 700; color: #667eea;">${totalCount}</div>
          <div style="font-size: 12px; color: #888; margin-top: 4px;">전체 공고</div>
        </div>
        <div style="flex: 1; border-left: 1px solid #eee;">
          <div style="font-size: 32px; font-weight: 700; color: #10b981;">${newJobs.length}</div>
          <div style="font-size: 12px; color: #888; margin-top: 4px;">어제 신규</div>
        </div>
        <div style="flex: 1; border-left: 1px solid #eee;">
          <div style="font-size: 32px; font-weight: 700; color: #3b82f6;">${(recentJobs || []).length}</div>
          <div style="font-size: 12px; color: #888; margin-top: 4px;">최근 7일</div>
        </div>
        <div style="flex: 1; border-left: 1px solid #eee;">
          <div style="font-size: 32px; font-weight: 700; color: #f59e0b;">${urgentJobs.length}</div>
          <div style="font-size: 12px; color: #888; margin-top: 4px;">마감 임박</div>
        </div>
      </div>
    </div>

    <!-- 회사별 현황 -->
    <div style="background: white; padding: 24px; border-bottom: 1px solid #eee;">
      <h2 style="margin: 0 0 16px 0; font-size: 16px; color: #333;">🏢 회사별 현황</h2>
      <table style="width: 100%; border-collapse: collapse;">
        ${Object.entries(stats).map(([company, count]) => `
        <tr>
          <td style="padding: 8px 0; color: #555;">${company}</td>
          <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #333;">${count}건</td>
        </tr>
        `).join('')}
      </table>
    </div>

    <!-- 최근 7일 이내 등록 포지션 -->
    ${(recentJobs || []).length > 0 ? `
    <div style="background: white; padding: 24px; border-bottom: 1px solid #eee;">
      <h2 style="margin: 0 0 16px 0; font-size: 16px; color: #333;">📅 최근 7일 이내 등록 포지션</h2>
      ${Object.entries(recentJobsByGroup).map(([group, jobs]) => `
        <div style="margin-bottom: 20px;">
          <h3 style="font-size: 14px; color: #3b82f6; margin: 0 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #3b82f6;">${group} (${jobs.length}건)</h3>
          ${jobs.map(job => `
          <div style="padding: 12px; margin-bottom: 8px; background: #f0f7ff; border-radius: 8px; border-left: 3px solid #3b82f6;">
            <a href="${job.url}" style="color: #333; text-decoration: none; font-weight: 500; font-size: 14px; display: block; margin-bottom: 4px;">${job.title}</a>
            <div style="font-size: 12px; color: #888;">
              ${job.company} · 등록: ${formatDateFriendly(job.openDate)} ${job.closeDate && job.closeDate !== '상시채용' ? '· 마감: ' + formatDateFriendly(job.closeDate) : ''}
            </div>
          </div>
          `).join('')}
        </div>
      `).join('')}
    </div>
    ` : ''}

    <!-- 어제 신규 공고 -->
    ${newJobs.length > 0 ? `
    <div style="background: white; padding: 24px; border-bottom: 1px solid #eee;">
      <h2 style="margin: 0 0 16px 0; font-size: 16px; color: #333;">🆕 어제 신규 공고</h2>
      ${Object.entries(newJobsByGroup).map(([group, jobs]) => `
        <div style="margin-bottom: 20px;">
          <h3 style="font-size: 14px; color: #667eea; margin: 0 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #667eea;">${group} (${jobs.length}건)</h3>
          ${jobs.map(job => `
          <div style="padding: 12px; margin-bottom: 8px; background: #f9fafb; border-radius: 8px; border-left: 3px solid #667eea;">
            <a href="${job.url}" style="color: #333; text-decoration: none; font-weight: 500; font-size: 14px; display: block; margin-bottom: 4px;">${job.title}</a>
            <div style="font-size: 12px; color: #888;">
              ${job.company} ${job.location ? '· ' + job.location : ''} ${job.closeDate ? '· 마감: ' + formatDateFriendly(job.closeDate) : ''}
            </div>
          </div>
          `).join('')}
        </div>
      `).join('')}
    </div>
    ` : `
    <div style="background: white; padding: 24px; border-bottom: 1px solid #eee; text-align: center;">
      <p style="color: #888; margin: 0;">어제 신규 공고가 없습니다.</p>
    </div>
    `}

    <!-- 마감 임박 공고 -->
    ${urgentJobs.length > 0 ? `
    <div style="background: white; padding: 24px; border-bottom: 1px solid #eee;">
      <h2 style="margin: 0 0 16px 0; font-size: 16px; color: #333;">⏰ 마감 임박 (7일 이내)</h2>
      ${urgentJobs.slice(0, 10).map(job => `
      <div style="padding: 12px; margin-bottom: 8px; background: #fffbeb; border-radius: 8px; border-left: 3px solid #f59e0b;">
        <a href="${job.url}" style="color: #333; text-decoration: none; font-weight: 500; font-size: 14px; display: block; margin-bottom: 4px;">${job.title}</a>
        <div style="font-size: 12px; color: #888;">
          ${job.company} · <span style="color: #f59e0b; font-weight: 500;">마감: ${formatDateFriendly(job.closeDate)}</span>
        </div>
      </div>
      `).join('')}
    </div>
    ` : ''}

    <!-- 푸터 -->
    <div style="background: #f9fafb; border-radius: 0 0 16px 16px; padding: 20px; text-align: center;">
      <p style="margin: 0; font-size: 12px; color: #888;">
        이 메일은 자동 발송되었습니다.<br>
        <a href="https://docs.google.com/spreadsheets/d/${CONFIG.SPREADSHEET_ID}" style="color: #667eea;">스프레드시트에서 전체 목록 보기</a>
      </p>
    </div>

  </div>
</body>
</html>
  `;
}
