# PDF 생성 기능 가이드

## 📋 개요

Canonical JSON 및 DB 데이터를 기반으로 PDF 템플릿 위에 텍스트를 좌표 기반으로 삽입하여 보고서 PDF를 생성하는 기능입니다.

**구현 일자**: 2025-11-19  
**기술 스택**: ReportLab + PyPDF2  
**지원 보고서**: 일일/주간/월간/실적

---

## 📁 파일 구조

```
backend/
├── app/reporting/
│   ├── pdf_generator/
│   │   ├── __init__.py
│   │   ├── base.py                    # 기본 PDF 생성 클래스
│   │   ├── utils.py                   # 공통 유틸리티
│   │   ├── daily_report_pdf.py        # 일일보고서
│   │   ├── weekly_report_pdf.py       # 주간보고서
│   │   ├── monthly_report_pdf.py      # 월간보고서
│   │   └── performance_report_pdf.py  # 실적보고서
│   └── service/
│       └── report_export_service.py   # 서비스 레이어
├── api/v1/endpoints/
│   └── pdf_export.py                  # API 엔드포인트
├── Data/reports/                      # PDF 템플릿
│   ├── 일일 업무 보고서.pdf
│   ├── 주간 업무 보고서.pdf
│   ├── 월간 업무 보고서.pdf
│   └── 실적 보고서 양식.pdf
├── output_reports/                    # PDF 출력
└── debug/
    └── test_pdf_export.py             # 테스트 스크립트
```

---

## 🚀 빠른 시작

### 1. 패키지 설치

```bash
cd backend
pip install -r requirements.txt
```

새로 추가된 패키지:
- `reportlab==4.0.7` - PDF Canvas, 텍스트 렌더링
- `PyPDF2==3.0.1` - PDF 병합
- `PyMuPDF==1.23.8` - PDF 읽기 (선택적)

### 2. 테스트 실행

```bash
# 모든 PDF 타입 테스트
python backend/debug/test_pdf_export.py

# 개별 테스트 (Python에서)
python -c "from backend.debug.test_pdf_export import test_daily_pdf; test_daily_pdf()"
```

### 3. API 사용

```bash
# 일일보고서 PDF 다운로드
curl http://localhost:8000/api/v1/pdf/daily/김보험/2025-01-20 \
  --output daily.pdf

# 주간보고서 PDF 다운로드
curl http://localhost:8000/api/v1/pdf/weekly/김보험/2025-01-20/2025-01-24 \
  --output weekly.pdf

# 월간보고서 PDF 다운로드
curl http://localhost:8000/api/v1/pdf/monthly/김보험/2025-01-01/2025-01-31 \
  --output monthly.pdf

# 실적보고서 PDF 다운로드
curl http://localhost:8000/api/v1/pdf/performance/김보험/2025-01-01/2025-01-31 \
  --output performance.pdf
```

---

## 📝 사용 방법

### Python에서 직접 사용

```python
from app.infrastructure.database.session import SessionLocal
from app.reporting.service.report_export_service import ReportExportService
from datetime import date

db = SessionLocal()

# 일일보고서 PDF 생성
pdf_bytes = ReportExportService.export_daily_pdf(
    db=db,
    owner="김보험",
    report_date=date(2025, 1, 20)
)

# 파일로 저장
with open("daily_report.pdf", "wb") as f:
    f.write(pdf_bytes)

db.close()
```

### API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/v1/pdf/daily/{owner}/{report_date}` | GET | 일일보고서 PDF |
| `/api/v1/pdf/weekly/{owner}/{period_start}/{period_end}` | GET | 주간보고서 PDF |
| `/api/v1/pdf/monthly/{owner}/{period_start}/{period_end}` | GET | 월간보고서 PDF |
| `/api/v1/pdf/performance/{owner}/{period_start}/{period_end}` | GET | 실적보고서 PDF |

---

## 🎨 좌표 조정 방법

PDF 생성 후 텍스트 위치가 맞지 않을 경우 각 파일의 `TODO` 주석을 찾아 좌표를 조정하세요.

### 1. PDF 좌표계 이해

```
PDF 좌표계:
- 원점 (0, 0) = 왼쪽 아래
- X축: 왼쪽(0) → 오른쪽(595.27)
- Y축: 아래(0) → 위(841.89)

일반적 좌표계 변환:
- 상단 기준 Y를 사용하려면: _to_pdf_y(y) 사용
```

### 2. 좌표 조정 예시

#### daily_report_pdf.py 수정

```python
# 작성일자 좌표 조정
# AS-IS
self.draw_text(420, self._to_pdf_y(80), 작성일자, font_size=11)  # TODO: 좌표 미세조정

# TO-BE (오른쪽으로 10px 이동)
self.draw_text(430, self._to_pdf_y(80), 작성일자, font_size=11)  # 조정됨
```

### 3. 좌표 찾기 팁

1. PDF 뷰어에서 좌표 확인
   - Adobe Acrobat: 상단 메뉴 → 도구 → 측정
   - PDF-XChange: 도구 → 주석 → 측정

2. 시행착오로 조정
   - X: 10~20px씩 조정
   - Y: 5~10px씩 조정

3. 테이블/표는 첫 행 기준점을 먼저 맞추고, 행 간격 조정

---

## ⚙️ 기술 세부사항

### BasePDFGenerator 클래스

```python
class BasePDFGenerator:
    """PDF 생성 기본 클래스"""
    
    # 주요 메서드:
    - _init_canvas(): ReportLab Canvas 초기화
    - draw_text(x, y, text, ...): 단일 텍스트 그리기
    - draw_multiline_text(...): 여러 줄 텍스트
    - draw_table_text(...): 표 형식 텍스트
    - save_overlay(): Overlay PDF 저장
    - merge_with_template(): 템플릿과 병합
```

### PDF 생성 흐름

```
1. Canvas 초기화 (_init_canvas)
   ↓
2. 텍스트 그리기 (draw_text, draw_multiline_text)
   ↓
3. Overlay 저장 (save_overlay)
   ↓
4. 템플릿과 병합 (merge_with_template)
   ↓
5. PDF Bytes 반환
```

### 한글 폰트 처리

Windows: `맑은 고딕` (C:/Windows/Fonts/malgun.ttf)  
Mac/Linux: `NanumGothic` 또는 기본 폰트

---

## 🐛 트러블슈팅

### 문제 1: "템플릿 PDF를 찾을 수 없습니다"

**원인**: 템플릿 파일이 없음

**해결**:
```bash
# 템플릿 경로 확인
ls backend/Data/reports/

# 템플릿 파일명이 코드와 일치하는지 확인
# 예: daily_report_pdf.py에서 사용하는 파일명
```

### 문제 2: "한글이 깨져서 나옵니다"

**원인**: 한글 폰트를 찾을 수 없음

**해결**:
```python
# base.py의 _init_canvas() 메서드에서 폰트 경로 수정
try:
    pdfmetrics.registerFont(TTFont('malgun', '폰트경로/malgun.ttf'))
    self.default_font = 'malgun'
except:
    pass
```

### 문제 3: "보고서를 찾을 수 없습니다"

**원인**: DB에 해당 보고서가 없음

**해결**:
```bash
# 먼저 보고서 생성
python backend/debug/test_weekly_chain.py   # 주간
python backend/debug/test_monthly_chain.py  # 월간
python backend/debug/test_performance_chain.py  # 실적

# 또는 bulk ingest
python backend/tools/bulk_daily_ingest.py
```

### 문제 4: "텍스트 위치가 맞지 않습니다"

**원인**: 템플릿 좌표가 잘못 설정됨

**해결**: 위의 "좌표 조정 방법" 참조

---

## 📊 출력 파일 위치

기본 출력 경로: `backend/output_reports/`

생성되는 파일명:
- `일일보고서_{owner}_{date}.pdf`
- `주간보고서_{owner}_{period_start}.pdf`
- `월간보고서_{owner}_{year}년{month}월.pdf`
- `실적보고서_{owner}_{period_start}_{period_end}.pdf`

---

## 🔄 워크플로우

### 전체 보고서 생성 프로세스

```
1. 일일보고서 입력 (Daily FSM)
   ↓
2. 주간/월간/실적 보고서 자동 생성 (Chain)
   ↓
3. PDF 생성 (이 기능)
   ↓
4. 다운로드/이메일 전송
```

### 예시: 한 달치 보고서 전체 생성

```bash
# 1. 일일보고서 bulk ingest
python backend/tools/bulk_daily_ingest.py

# 2. 주간 보고서 생성 (1월 1~5주차)
curl -X POST http://localhost:8000/api/v1/weekly/generate \
  -H "Content-Type: application/json" \
  -d '{"owner": "김보험", "target_date": "2025-01-03"}'
# ... (각 주차별 반복)

# 3. 월간 보고서 생성
curl -X POST http://localhost:8000/api/v1/monthly/generate \
  -H "Content-Type: application/json" \
  -d '{"owner": "김보험", "target_date": "2025-01-15"}'

# 4. PDF 다운로드
curl http://localhost:8000/api/v1/pdf/monthly/김보험/2025-01-01/2025-01-31 \
  --output monthly_jan.pdf
```

---

## 📚 참고 자료

### 좌표 및 크기 상수 (utils.py)

```python
class PDFCoordinates:
    PAGE_WIDTH = 595.27    # A4 너비
    PAGE_HEIGHT = 841.89   # A4 높이
    MARGIN_LEFT = 50
    MARGIN_RIGHT = 50
    MARGIN_TOP = 50
    MARGIN_BOTTOM = 50
```

### ReportLab 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `canvas.setFont(name, size)` | 폰트 설정 |
| `canvas.setFillColorRGB(r, g, b)` | 색상 설정 (0~1) |
| `canvas.drawString(x, y, text)` | 텍스트 그리기 |
| `canvas.save()` | Canvas 저장 |

### PyPDF2 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `PdfReader(file)` | PDF 읽기 |
| `PdfWriter()` | PDF 작성기 생성 |
| `page.merge_page(overlay)` | 페이지 병합 |
| `writer.write(stream)` | PDF 저장 |

---

## ✅ 체크리스트

PDF 생성 전 확인사항:

- [ ] PostgreSQL 실행 중
- [ ] 템플릿 PDF 파일 존재 (backend/Data/reports/)
- [ ] 보고서 데이터 DB에 저장됨
- [ ] 한글 폰트 경로 설정 (base.py)
- [ ] output_reports 디렉토리 존재

PDF 생성 후 확인사항:

- [ ] PDF 파일 생성됨
- [ ] PDF가 정상적으로 열림
- [ ] 텍스트 위치가 적절함
- [ ] 한글이 깨지지 않음
- [ ] 모든 데이터가 표시됨

---

## 🎉 완료!

모든 PDF 생성 기능이 구현되었습니다!

다음 단계:
1. 템플릿 PDF 준비
2. 좌표 조정
3. 프론트엔드 다운로드 버튼 추가
4. 이메일 발송 기능 추가 (선택)

Happy Coding! 🚀

