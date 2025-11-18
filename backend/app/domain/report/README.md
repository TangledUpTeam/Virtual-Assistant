# 보고서 처리 모듈

이 모듈은 보고서 양식 PDF를 AI를 활용하여 JSON 형식으로 구조화하는 기능을 제공합니다.

## 지원하는 보고서 타입

- **일일 업무 보고서** (daily)
- **주간 업무 보고서** (weekly)
- **월간 업무 보고서** (monthly)
- **분기별 실적 보고서** (performance)

## 파일 구조

```
report/
├── __init__.py
├── schemas.py      # Pydantic 스키마 정의
├── service.py      # 보고서 처리 서비스
└── README.md       # 이 파일
```

## 사용 방법

### 1. CLI를 통한 테스트

```bash
# backend 디렉토리로 이동
cd backend

# 필요한 패키지 설치
pip install -r requirements.txt

# .env 파일에 OpenAI API 키 설정
# OPENAI_API_KEY=your_api_key_here

# 보고서 파싱 실행
python test_report_parser.py "Data/일일 업무 보고서.pdf"
python test_report_parser.py "Data/주간 업무 보고서.pdf"
python test_report_parser.py "Data/월간 업무 보고서.pdf"
python test_report_parser.py "Data/실적 보고서 양식.pdf"
```

### 2. API를 통한 사용

FastAPI 서버 실행 후 다음 엔드포인트를 사용할 수 있습니다:

#### 보고서 파싱
```bash
POST /api/v1/reports/parse
Content-Type: multipart/form-data

Body:
- file: PDF 파일
```

#### 보고서 타입 감지
```bash
POST /api/v1/reports/detect-type
Content-Type: multipart/form-data

Body:
- file: PDF 파일
```

#### 보고서 템플릿 조회
```bash
GET /api/v1/reports/templates/{report_type}

Path Parameters:
- report_type: daily, weekly, monthly, performance
```

### 3. Python 코드에서 직접 사용

```python
from app.domain.report.service import ReportProcessingService
import os

# 서비스 초기화
api_key = os.getenv("OPENAI_API_KEY")
service = ReportProcessingService(api_key=api_key)

# PDF 처리
report_type, json_data = service.process_report("path/to/report.pdf")

print(f"보고서 타입: {report_type}")
print(f"추출된 데이터: {json_data}")
```

## 처리 프로세스

1. **PDF → 이미지 변환**: PyMuPDF를 사용하여 PDF를 이미지로 변환
2. **문서 타입 감지**: GPT-4 Vision을 사용하여 보고서 타입 자동 감지
3. **스키마 선택**: 감지된 타입에 맞는 JSON 스키마 선택
4. **정보 추출**: GPT-4 Vision을 사용하여 OCR 및 구조화된 JSON 생성

## 출력 형식

각 보고서 타입별로 사전 정의된 JSON 스키마에 따라 데이터가 추출됩니다.

### 일일 보고서 예시
```json
{
  "문서제목": "일일 업무 보고서",
  "상단정보": {
    "작성일자": "2024-01-15",
    "성명": "홍길동"
  },
  "금일_진행_업무": "고객 상담 및 계약 진행",
  "세부업무": [
    {
      "시간": "09:00 - 10:00",
      "업무내용": "신규 고객 전화 상담",
      "비고": ""
    }
  ],
  "미종결_업무사항": "A고객 계약서 검토 중",
  "익일_업무계획": "B고객 방문 예정",
  "특이사항": ""
}
```

## 주의사항

- OpenAI API 키가 필요합니다 (.env 파일에 설정)
- PDF 파일의 품질이 좋을수록 정확한 결과를 얻을 수 있습니다
- GPT-4o 모델을 사용하므로 API 비용이 발생합니다
- 처리 시간은 PDF 페이지 수에 따라 다릅니다 (보통 10-30초)

