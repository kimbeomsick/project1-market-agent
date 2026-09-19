# Project 1: Market Agent (project1-market-agent)

제조업 AI 비전 품질검사 기업 **NovaFactory AI**를 위한 시장 동향 및 경쟁사 모니터링 자동화 에이전트 프로젝트입니다.

## 📁 프로젝트 구조

```
day1_ex1/
├── .github/
│   └── workflows/          # GitHub Actions 자동화 워크플로우
├── config/
│   └── company_profile.yaml # 기업/경쟁사/모니터링 키워드 프로필 설정
├── data/
│   ├── fallback/           # 대체 합성 데이터 (fallback_market_news.csv)
│   ├── raw/                # 수집된 원본 데이터
│   └── processed/          # 정제 및 분석 완료 데이터
├── docs/                   # GitHub Pages 배포용 웹페이지 및 리포트 (HTML)
├── logs/                   # 실행 로그
├── src/                    # 에이전트 소스 코드 (수집, 정제, 요약, 리포트 생성)
├── requirements.txt        # 프로젝트 의존성 목록
└── README.md
```

## ⚙️ 설정 (Config)
- `config/company_profile.yaml`에서 모니터링 대상 기업, 경쟁사 목록, 관심 키워드 및 지원사업 키워드를 정의합니다.
