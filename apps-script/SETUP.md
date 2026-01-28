# Google Apps Script 설정 가이드

## 1. Apps Script 프로젝트 생성

1. [Google Apps Script](https://script.google.com/) 접속
2. **새 프로젝트** 클릭
3. 프로젝트 이름을 `채용공고 뉴스레터`로 변경

## 2. 코드 붙여넣기

1. 기본 `Code.gs` 파일의 내용을 모두 삭제
2. `Code.gs` 파일 내용을 복사하여 붙여넣기
3. **저장** (Ctrl+S)

## 3. 웹 앱으로 배포

1. 상단 메뉴에서 **배포** → **새 배포** 클릭
2. 설정:
   - **유형 선택**: ⚙️ 톱니바퀴 → **웹 앱** 선택
   - **설명**: `채용공고 뉴스레터 v1`
   - **실행 사용자**: `나`
   - **액세스 권한**: `나만` (보안을 위해)
3. **배포** 클릭
4. 권한 승인 요청 시 승인
5. **웹 앱 URL** 복사 (예: `https://script.google.com/macros/s/AKfy.../exec`)

## 4. GitHub Secret 등록

```bash
gh secret set APPS_SCRIPT_URL --body "복사한_웹앱_URL"
```

## 5. 테스트

### Apps Script에서 직접 테스트
1. `sendDailyReport` 함수 선택
2. **실행** 버튼 클릭
3. 이메일 수신 확인

### URL로 테스트
브라우저에서 웹 앱 URL 접속 → JSON 응답 확인

## 문제 해결

### "승인 필요" 오류
- **배포** → **배포 관리** → **수정** → 권한 다시 승인

### 이메일이 안 옴
- Apps Script 실행 로그 확인 (보기 → 실행 기록)
- Gmail 스팸함 확인

### URL 변경됨
- 새 배포 시 URL이 변경됩니다
- GitHub Secret도 업데이트 필요
