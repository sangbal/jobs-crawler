# 채용 정보 자동 크롤러

카카오, 토스, 네이버, 쿠팡, 당근, 배민 채용 공고를 매일 자동 수집하여 Google Sheets에 적재합니다.

## 수집 대상

| 회사 | 직군 | 고용형태 |
|------|------|----------|
| 카카오 | 서비스비즈 | 정규직 |
| 토스 | Sales / Sales Support | 정규직 |
| 네이버 | Service & Business | 정규직 |
| 쿠팡 | 기획 (Seoul) | 정규직 |
| 당근 | Business | 정규직 |
| 배민 | Business & Sales | 정규직 |

## 실행 주기

- 매일 오전 9시 (한국 시간) 자동 실행
- GitHub Actions의 `workflow_dispatch`로 수동 실행 가능

## 설정 방법

### 1. Google Cloud 설정
1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Google Sheets API 활성화
3. 서비스 계정 생성 및 JSON 키 다운로드
4. 대상 스프레드시트에 서비스 계정 이메일을 **편집자**로 공유

### 2. GitHub Secrets 등록

| Secret 이름 | 설명 |
|------------|------|
| `GOOGLE_CREDENTIALS` | 서비스 계정 JSON 키 전체 내용 |
| `SPREADSHEET_ID` | 카카오용 스프레드시트 ID |
| `TOSS_SPREADSHEET_ID` | 토스용 스프레드시트 ID |
| `NAVER_SPREADSHEET_ID` | 네이버용 스프레드시트 ID |
| `COUPANG_SPREADSHEET_ID` | 쿠팡용 스프레드시트 ID |
| `DAANGN_SPREADSHEET_ID` | 당근용 스프레드시트 ID |
| `BAEMIN_SPREADSHEET_ID` | 배민용 스프레드시트 ID |

## 스프레드시트 컬럼 구조

| A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|
| 공고ID | 직무명 | 회사 | 직군 | 근무지 | 고용형태 | 등록일 | 마감일 | URL | 수집일시 |

## 로컬 테스트

```bash
# 환경변수 설정
export GOOGLE_CREDENTIALS='{"type": "service_account", ...}'
export SPREADSHEET_ID='your-spreadsheet-id'

# 실행
pip install -r requirements.txt
python crawler.py          # 카카오
python toss_crawler.py     # 토스
python naver_crawler.py    # 네이버
python coupang_crawler.py  # 쿠팡
python daangn_crawler.py   # 당근
python baemin_crawler.py   # 배민
```

## 파일 구조

```
jobs-crawler/
├── .github/
│   └── workflows/
│       └── crawl.yml          # GitHub Actions 워크플로우
├── crawler.py                 # 카카오 크롤러
├── toss_crawler.py            # 토스 크롤러
├── naver_crawler.py           # 네이버 크롤러
├── coupang_crawler.py         # 쿠팡 크롤러
├── daangn_crawler.py          # 당근 크롤러
├── baemin_crawler.py          # 배민 크롤러
├── requirements.txt           # Python 의존성
└── README.md
```
