# 🧭 AI 기반 취업시장 분석 & 스펙 매칭 서비스

## 📘 프로젝트 개요
국내 IT 채용 시장 데이터를 기반으로  
**현재 시장이 요구하는 기술 트렌드**와 **개인 스펙 매칭도**를 분석하여  
AI가 제시하는 **취업 로드맵**을 자동 생성하는 서비스입니다.

---

## 📂 폴더 구조

```
AI_Job_Market/
├── backend/                     # 백엔드 서버
│   ├── app.py                   # Flask/FastAPI 메인 엔트리
│   ├── routes/                  # API 라우트 정의
│   │   ├── market_overview.py   # 전체 시장 기술 비중 API
│   │   ├── stack_by_role.py     # 직군별 기술 스택 분석 API
│   │   ├── ai_jobs_insight.py   # AI 직군별 분류 API
│   │   ├── skill_match.py       # 연관 기술 매칭 API
│   │   ├── company_view.py      # 기업별 기술 Top View API
│   │   └── trends_tracker.py    # 뉴스·기사 요약 (RAG)
│   ├── services/                # 내부 로직 (AI·DB·분석)
│   │   ├── data_collector.py    # 크롤링 및 데이터 수집
│   │   ├── analyzer.py          # 기술 연관도 분석
│   │   ├── llm_processor.py     # GPT/LLM 호출 및 프롬프트 설계
│   │   ├── rag_engine.py        # RAG 기반 기사 검색·요약
│   │   └── report_generator.py  # AI 리포트 생성 모듈
│   ├── models/                  # 데이터 모델 정의 (ORM)
│   │   ├── job_posting.py
│   │   ├── tech_skill.py
│   │   └── company.py
│   └── database/
│       ├── schema.sql           # DB 스키마 정의
│       └── connection.py        # DB 연결 유틸
│
├── frontend/                    # 프론트엔드 (React or Streamlit)
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.js
│   │   │   ├── TechSearch.js
│   │   │   ├── AIInsights.js
│   │   │   ├── SkillFinder.js
│   │   │   ├── CompanyView.js
│   │   │   └── TrendNews.js
│   │   ├── services/api.js      # 백엔드 API 호출 관리
│   │   └── App.js               # 메인 페이지 구성
│   └── package.json
│
├── data/                        # 원본·전처리 데이터
│   ├── raw/                     # 수집된 원본 데이터
│   ├── processed/               # 정제·정규화된 데이터
│   └── embeddings/              # 임베딩 벡터 저장소
│
├── ai_modules/                  # AI 관련 모듈
│   ├── prompt_templates/        # 프롬프트 엔지니어링
│   ├── embeddings/              # LangChain / FAISS 구조
│   ├── classification/          # AI 직군 자동 분류
│   └── summarizer/              # 기사 요약 모델
│
├── docs/                        # 문서화 자료
│   ├── ERD.png
│   ├── system_architecture.png
│   └── project_plan.md
│
└── README.md                    # (현재 문서)
```

---

## 🧩 모듈별 설명

| 모듈 | 주요 기능 | 핵심 기술 | AI 활용 |
|------|------------|------------|----------|
| **market_overview** | 전체 시장 기술 비중 시각화 | Python, Pandas, Chart.js | ChatGPT 데이터 정제 |
| **stack_by_role** | 직군별 기술 스택 분석 | Pandas, Numpy | GPT API |
| **ai_jobs_insight** | AI 관련 직군 자동 분류 | GPT-4, Sklearn | LLM 분류 |
| **skill_match** | 언어·DB·AI 기반 연관 기술 분석 | FAISS, Pandas | ChatGPT 분석 |
| **company_view** | 기업별 Top 기술 요구 시각화 | Flask API | ChatGPT 요약 |
| **trends_tracker** | 최신 뉴스 및 트렌드 요약 | LangChain, OpenAI API | RAG 기반 요약 |

---

## ⚙️ 개발 환경

| 구분 | 도구 |
|------|------|
| **언어** | Python |
| **AI** | OpenAI GPT-4, LangChain, CursorAI |
| **DB** | MySQL or PostgreSQL |
| **IDE** | Cursor, VS Code |
| **시각화** | Chart.js, Streamlit |
| **협업** | GitHub, Notion |
| **배포** | Streamlit Cloud / Vercel / AWS EC2 |

---

## 🗓️ 개발 일정 요약 (4~5주)

| 주차 | 주요 목표 |
|------|-------------|
| **1주차** | 기획 및 DB 구조 설계, 환경 세팅 |
| **2주차** | 채용공고 데이터 수집 및 전처리 |
| **3주차** | AI 분석 모듈 (LLM / Embedding / RAG) 구현 |
| **4주차** | 프론트 시각화 + API 통합 |
| **5주차** | 문서화 및 발표 준비 |

---

## 🚀 프로젝트 특징
> “모든 팀원이 백엔드와 프론트를 구분하지 않고,  
> AI·데이터·웹 전 영역을 직접 다루며 완성하는 프로젝트.”

---

## 📈 확장 방향
- 실시간 채용 API 연동 (잡코리아, 원티드, 사람인 등)
- AI 모델 튜닝 (기술명·직무 자동 분류 정밀도 향상)
- 사용자 맞춤형 취업 리포트 자동 이메일 전송

---

### ✍️ 작성자
팀 **얼기설기**  
Project Lead: 김진모  
작성일: 2025-11-10
