"""
보고서 처리 서비스
PDF 파일을 읽어서 JSON 형식으로 변환하는 기능 제공
"""
import os
import json
import base64
import uuid
from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime, date

import fitz  # PyMuPDF
from openai import OpenAI

from app.domain.report.schemas import (
    ReportType,
    CanonicalReport,
    TaskItem,
    KPIItem
)


class ReportProcessingService:
    """보고서 처리 서비스"""
    
    # ========================================
    # 보고서 스키마 정의 (4종류)
    # ========================================
    DAILY_SCHEMA = """
{
  "문서제목": "일일 업무 보고서",
  "상단정보": { "작성일자": "", "성명": "" },
  "금일_진행_업무": "",
  "세부업무": [
    { "시간": "09:00 - 10:00", "업무내용": "", "비고": "" },
    { "시간": "10:00 - 11:00", "업무내용": "", "비고": "" },
    { "시간": "11:00 - 12:00", "업무내용": "", "비고": "" },
    { "시간": "12:00 - 13:00", "업무내용": "", "비고": "" },
    { "시간": "13:00 - 14:00", "업무내용": "", "비고": "" },
    { "시간": "14:00 - 15:00", "업무내용": "", "비고": "" },
    { "시간": "15:00 - 16:00", "업무내용": "", "비고": "" },
    { "시간": "16:00 - 17:00", "업무내용": "", "비고": "" },
    { "시간": "17:00 - 18:00", "업무내용": "", "비고": "" }
  ],
  "미종결_업무사항": "",
  "익일_업무계획": "",
  "특이사항": ""
}
"""

    WEEKLY_SCHEMA = """
{
  "문서제목": "주간 업무 보고서",
  "상단정보": { "작성일자": "", "성명": "" },
  "주간업무목표": [
    { "항목": "1)", "목표": "", "비고": "" },
    { "항목": "2)", "목표": "", "비고": "" },
    { "항목": "3)", "목표": "", "비고": "" }
  ],
  "요일별_세부_업무": {
    "월": { "업무내용": "", "비고": "" },
    "화": { "업무내용": "", "비고": "" },
    "수": { "업무내용": "", "비고": "" },
    "목": { "업무내용": "", "비고": "" },
    "금": { "업무내용": "", "비고": "" }
  },
  "주간_중요_업무": "",
  "특이사항": ""
}
"""

    MONTHLY_SCHEMA = """
{
  "문서제목": "월간 업무 보고서",
  "상단정보": { "월": "", "작성일자": "", "성명": "" },
  "월간_핵심_지표": {
    "신규_계약_건수": { "건수": "", "비고": "" },
    "유지_계약_건수": { "유지": "", "갱신": "", "미납_방지": "", "비고": "" },
    "상담_진행_건수": { "전화": "", "방문": "", "온라인": "", "비고": "" }
  },
  "주차별_세부_업무": {
    "1주": { "업무내용": "", "비고": "" },
    "2주": { "업무내용": "", "비고": "" },
    "3주": { "업무내용": "", "비고": "" },
    "4주": { "업무내용": "", "비고": "" },
    "5주": { "업무내용": "", "비고": "" }
  },
  "익월_계획": ""
}
"""

    PERFORMANCE_SCHEMA = """
{
  "문서제목": "분기별 실적 보고서",
  "상단정보": { "작성일자": "", "성명": "" },
  "주요지표": {
    "신계약_건수": { "건수": "" },
    "유지계약_건수": { "건수": "" },
    "소멸계약_건수": { "건수": "" },
    "고객_그래프": {
      "항목명": "계약한 고객 수",
      "1/4분기": "",
      "2/4분기": "",
      "3/4분기": "",
      "4/4분기": ""
    }
  },
  "달력": {
    "상반기": {
      "1/4분기": { "1월": "", "2월": "", "3월": "" },
      "2/4분기": { "4월": "", "5월": "", "6월": "" }
    },
    "하반기": {
      "3/4분기": { "7월": "", "8월": "", "9월": "" },
      "4/4분기": { "10월": "", "11월": "", "12월": "" }
    }
  },
  "이슈_및_계획": "",
  "비고": ""
}
"""

    SCHEMA_MAP = {
        ReportType.DAILY: DAILY_SCHEMA,
        ReportType.WEEKLY: WEEKLY_SCHEMA,
        ReportType.MONTHLY: MONTHLY_SCHEMA,
        ReportType.PERFORMANCE: PERFORMANCE_SCHEMA
    }

    def __init__(self, api_key: str = None):
        """
        서비스 초기화
        
        Args:
            api_key: OpenAI API 키 (None인 경우 환경변수에서 읽음)
        """
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        self.client = OpenAI()

    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[bytes]:
        """
        PDF를 이미지로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            dpi: 이미지 해상도 (기본값: 200)
            
        Returns:
            이미지 바이트 리스트
        """
        doc = fitz.open(pdf_path)
        images = []
        
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
        
        doc.close()
        return images

    def encode_b64(self, data: bytes) -> str:
        """
        바이트 데이터를 base64로 인코딩
        
        Args:
            data: 바이트 데이터
            
        Returns:
            base64 인코딩된 문자열
        """
        return base64.b64encode(data).decode("utf-8")

    def detect_report_type(self, images: List[bytes]) -> ReportType:
        """
        문서 타입 자동 감지
        
        Args:
            images: PDF에서 변환된 이미지 리스트
            
        Returns:
            감지된 보고서 타입
        """
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "너는 문서 종류를 분류하는 전문가다."}]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """
이 문서가 어떤 보고서인지 판단하라.
반드시 아래 중 하나로만 답하라:

daily / weekly / monthly / performance

단 한 단어만 출력하라.
"""
                    },
                    *[
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{self.encode_b64(img)}"
                            }
                        }
                        for img in images
                    ]
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model="gpt-4o",  # gpt-4.1은 gpt-4o로 변경
            messages=messages
        )

        doc_type_str = response.choices[0].message.content.strip().lower()
        
        # 문자열을 ReportType enum으로 변환
        try:
            return ReportType(doc_type_str)
        except ValueError:
            raise ValueError(f"문서 타입 감지 실패: {doc_type_str}")

    def extract_with_schema(self, images: List[bytes], schema: str) -> Dict[str, Any]:
        """
        스키마를 기반으로 PDF에서 정보 추출
        
        Args:
            images: PDF에서 변환된 이미지 리스트
            schema: 적용할 JSON 스키마
            
        Returns:
            추출된 JSON 데이터
        """
        prompt = f"""
PDF 내용을 아래 JSON 스키마에 정확히 채워 넣어 출력하라.

규칙:
1) 필드명, 계층, 구조 절대 변경 금지
2) 값 누락 시 "" 유지
3) 필드 추가 금지
4) OCR로 읽은 값만 넣기
5) JSON만 출력

스키마:
{schema}
"""

        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "너는 PDF를 JSON 스키마로 변환하는 전문가다."}]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *[
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{self.encode_b64(img)}"}
                        }
                        for img in images
                    ]
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model="gpt-4o",  # gpt-4.1은 gpt-4o로 변경
            messages=messages,
            response_format={"type": "json_object"}
        )

        json_str = response.choices[0].message.content
        return json.loads(json_str)

    def process_report(self, pdf_path: str) -> Tuple[ReportType, Dict[str, Any]]:
        """
        보고서 PDF 처리 (타입 감지 + 정보 추출)
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            (보고서 타입, 추출된 JSON 데이터) 튜플
        """
        # PDF를 이미지로 변환
        images = self.pdf_to_images(pdf_path)
        print(f"✅ PDF를 {len(images)}개 페이지로 변환했습니다.")

        # 문서 타입 감지
        report_type = self.detect_report_type(images)
        print(f"✅ 문서 타입 감지됨: {report_type.value}")

        # 해당 스키마 선택
        schema = self.SCHEMA_MAP[report_type]

        # 정보 추출
        print("⏳ 보고서 정보 추출 중...")
        json_data = self.extract_with_schema(images, schema)
        print("✅ 보고서 정보 추출 완료!")

        return report_type, json_data

    # ========================================
    # Raw JSON → Canonical JSON 변환 함수들
    # ========================================
    
    def _parse_date(self, date_str: str) -> date | None:
        """날짜 문자열을 date 객체로 변환"""
        if not date_str or date_str.strip() == "":
            return None
        
        # 다양한 날짜 형식 처리
        formats = ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y년 %m월 %d일"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def normalize_daily(self, raw_json: Dict[str, Any]) -> CanonicalReport:
        """
        일일 보고서 Raw JSON → Canonical 변환
        
        Args:
            raw_json: Vision API로부터 받은 원본 JSON
            
        Returns:
            CanonicalReport 객체
        """
        # 기본 정보 추출
        상단정보 = raw_json.get("상단정보", {})
        owner = 상단정보.get("성명", "")
        작성일자_str = 상단정보.get("작성일자", "")
        
        # 날짜 파싱
        report_date = self._parse_date(작성일자_str)
        
        # Tasks 변환 (세부업무)
        tasks = []
        세부업무_list = raw_json.get("세부업무", [])
        for idx, 세부업무 in enumerate(세부업무_list):
            시간 = 세부업무.get("시간", "")
            업무내용 = 세부업무.get("업무내용", "")
            비고 = 세부업무.get("비고", "")
            
            # 시간대에서 시작/종료 시간 추출
            time_start, time_end = None, None
            if " - " in 시간:
                parts = 시간.split(" - ")
                if len(parts) == 2:
                    time_start = parts[0].strip()
                    time_end = parts[1].strip()
            
            if 업무내용:  # 업무내용이 있는 경우만 추가
                tasks.append(TaskItem(
                    task_id=f"daily_{idx+1}",
                    title=업무내용,
                    description=업무내용,
                    time_start=time_start,
                    time_end=time_end,
                    status=None,
                    note=비고
                ))
        
        # Issues (미종결 업무사항)
        issues = []
        미종결_업무 = raw_json.get("미종결_업무사항", "")
        if 미종결_업무:
            if isinstance(미종결_업무, list):
                issues = 미종결_업무
            else:
                issues.append(미종결_업무)
        
        # Plans (익일 업무계획)
        plans = []
        익일_계획 = raw_json.get("익일_업무계획", "")
        if 익일_계획:
            if isinstance(익일_계획, list):
                plans = 익일_계획
            else:
                plans.append(익일_계획)
        
        # Metadata
        metadata = {
            "금일_진행_업무": raw_json.get("금일_진행_업무", ""),
            "특이사항": raw_json.get("특이사항", ""),
            "문서제목": raw_json.get("문서제목", "")
        }
        
        return CanonicalReport(
            report_id=str(uuid.uuid4()),
            report_type="daily",
            owner=owner,
            period_start=report_date,
            period_end=report_date,
            tasks=tasks,
            kpis=[],  # 일일 보고서에는 KPI 없음
            issues=issues,
            plans=plans,
            metadata=metadata
        )

    def normalize_weekly(self, raw_json: Dict[str, Any]) -> CanonicalReport:
        """
        주간 보고서 Raw JSON → Canonical 변환
        
        Args:
            raw_json: Vision API로부터 받은 원본 JSON
            
        Returns:
            CanonicalReport 객체
        """
        # 기본 정보 추출
        상단정보 = raw_json.get("상단정보", {})
        owner = 상단정보.get("성명", "")
        작성일자_str = 상단정보.get("작성일자", "")
        
        report_date = self._parse_date(작성일자_str)
        
        # Tasks 변환 (주간업무목표 + 요일별 세부 업무)
        tasks = []
        
        # 1) 주간업무목표
        주간업무목표 = raw_json.get("주간업무목표", [])
        for idx, 목표 in enumerate(주간업무목표):
            목표_내용 = 목표.get("목표", "")
            비고 = 목표.get("비고", "")
            
            if 목표_내용:
                tasks.append(TaskItem(
                    task_id=f"weekly_goal_{idx+1}",
                    title=목표_내용,
                    description=목표_내용,
                    time_start=None,
                    time_end=None,
                    status=None,
                    note=비고
                ))
        
        # 2) 요일별 세부 업무
        요일별_업무 = raw_json.get("요일별_세부_업무", {})
        for 요일, 업무_data in 요일별_업무.items():
            업무내용 = 업무_data.get("업무내용", "")
            비고 = 업무_data.get("비고", "")
            
            if 업무내용:
                tasks.append(TaskItem(
                    task_id=f"weekly_{요일}",
                    title=f"[{요일}] {업무내용}",
                    description=업무내용,
                    time_start=None,
                    time_end=None,
                    status=None,
                    note=비고
                ))
        
        # Issues (주간 중요 업무)
        issues = []
        주간_중요_업무 = raw_json.get("주간_중요_업무", "")
        if 주간_중요_업무:
            issues.append(주간_중요_업무)
        
        # Metadata
        metadata = {
            "특이사항": raw_json.get("특이사항", ""),
            "문서제목": raw_json.get("문서제목", "")
        }
        
        return CanonicalReport(
            report_id=str(uuid.uuid4()),
            report_type="weekly",
            owner=owner,
            period_start=report_date,
            period_end=report_date,
            tasks=tasks,
            kpis=[],
            issues=issues,
            plans=[],
            metadata=metadata
        )

    def normalize_monthly(self, raw_json: Dict[str, Any]) -> CanonicalReport:
        """
        월간 보고서 Raw JSON → Canonical 변환
        
        Args:
            raw_json: Vision API로부터 받은 원본 JSON
            
        Returns:
            CanonicalReport 객체
        """
        # 기본 정보 추출
        상단정보 = raw_json.get("상단정보", {})
        owner = 상단정보.get("성명", "")
        작성일자_str = 상단정보.get("작성일자", "")
        월 = 상단정보.get("월", "")
        
        report_date = self._parse_date(작성일자_str)
        
        # KPIs 변환 (월간 핵심 지표)
        kpis = []
        월간_핵심_지표 = raw_json.get("월간_핵심_지표", {})
        
        # 신규 계약 건수
        신규_계약 = 월간_핵심_지표.get("신규_계약_건수", {})
        if 신규_계약.get("건수"):
            kpis.append(KPIItem(
                kpi_name="신규_계약_건수",
                value=신규_계약.get("건수", ""),
                unit="건",
                category="계약",
                note=신규_계약.get("비고", "")
            ))
        
        # 유지 계약 건수
        유지_계약 = 월간_핵심_지표.get("유지_계약_건수", {})
        if 유지_계약:
            for key in ["유지", "갱신", "미납_방지"]:
                if 유지_계약.get(key):
                    kpis.append(KPIItem(
                        kpi_name=f"유지_계약_{key}",
                        value=유지_계약.get(key, ""),
                        unit="건",
                        category="유지계약",
                        note=유지_계약.get("비고", "")
                    ))
        
        # 상담 진행 건수
        상담_진행 = 월간_핵심_지표.get("상담_진행_건수", {})
        if 상담_진행:
            for key in ["전화", "방문", "온라인"]:
                if 상담_진행.get(key):
                    kpis.append(KPIItem(
                        kpi_name=f"상담_{key}",
                        value=상담_진행.get(key, ""),
                        unit="건",
                        category="상담",
                        note=상담_진행.get("비고", "")
                    ))
        
        # Tasks 변환 (주차별 세부 업무)
        tasks = []
        주차별_업무 = raw_json.get("주차별_세부_업무", {})
        for 주차, 업무_data in 주차별_업무.items():
            업무내용 = 업무_data.get("업무내용", "")
            비고 = 업무_data.get("비고", "")
            
            if 업무내용:
                tasks.append(TaskItem(
                    task_id=f"monthly_{주차}",
                    title=f"[{주차}] {업무내용}",
                    description=업무내용,
                    time_start=None,
                    time_end=None,
                    status=None,
                    note=비고
                ))
        
        # Plans (익월 계획)
        plans = []
        익월_계획 = raw_json.get("익월_계획", "")
        if 익월_계획:
            plans.append(익월_계획)
        
        # Metadata
        metadata = {
            "월": 월,
            "문서제목": raw_json.get("문서제목", "")
        }
        
        return CanonicalReport(
            report_id=str(uuid.uuid4()),
            report_type="monthly",
            owner=owner,
            period_start=report_date,
            period_end=report_date,
            tasks=tasks,
            kpis=kpis,
            issues=[],
            plans=plans,
            metadata=metadata
        )

    def normalize_performance(self, raw_json: Dict[str, Any]) -> CanonicalReport:
        """
        실적 보고서 Raw JSON → Canonical 변환
        
        Args:
            raw_json: Vision API로부터 받은 원본 JSON
            
        Returns:
            CanonicalReport 객체
        """
        # 기본 정보 추출
        상단정보 = raw_json.get("상단정보", {})
        owner = 상단정보.get("성명", "")
        작성일자_str = 상단정보.get("작성일자", "")
        
        report_date = self._parse_date(작성일자_str)
        
        # KPIs 변환 (주요지표)
        kpis = []
        주요지표 = raw_json.get("주요지표", {})
        
        # 신계약, 유지계약, 소멸계약 건수
        for key in ["신계약_건수", "유지계약_건수", "소멸계약_건수"]:
            if key in 주요지표:
                건수 = 주요지표[key].get("건수", "")
                if 건수:
                    kpis.append(KPIItem(
                        kpi_name=key,
                        value=건수,
                        unit="건",
                        category="계약",
                        note=""
                    ))
        
        # 고객 그래프 (분기별)
        고객_그래프 = 주요지표.get("고객_그래프", {})
        for 분기 in ["1/4분기", "2/4분기", "3/4분기", "4/4분기"]:
            값 = 고객_그래프.get(분기, "")
            if 값:
                kpis.append(KPIItem(
                    kpi_name=f"고객수_{분기}",
                    value=값,
                    unit="명",
                    category="고객",
                    note=""
                ))
        
        # Issues (이슈 및 계획)
        issues = []
        이슈_및_계획 = raw_json.get("이슈_및_계획", "")
        if 이슈_및_계획:
            issues.append(이슈_및_계획)
        
        # Metadata
        metadata = {
            "달력": raw_json.get("달력", {}),
            "비고": raw_json.get("비고", ""),
            "문서제목": raw_json.get("문서제목", "")
        }
        
        return CanonicalReport(
            report_id=str(uuid.uuid4()),
            report_type="performance",
            owner=owner,
            period_start=report_date,
            period_end=report_date,
            tasks=[],  # 실적 보고서에는 tasks 없음
            kpis=kpis,
            issues=issues,
            plans=[],
            metadata=metadata
        )

    def normalize_report(
        self, 
        report_type: ReportType | str, 
        raw_json: Dict[str, Any]
    ) -> CanonicalReport:
        """
        보고서 타입에 따라 적절한 normalize 함수 호출
        
        Args:
            report_type: 보고서 타입
            raw_json: Vision API로부터 받은 원본 JSON
            
        Returns:
            CanonicalReport 객체
            
        Raises:
            ValueError: 지원하지 않는 보고서 타입인 경우
        """
        # ReportType enum을 문자열로 변환
        if isinstance(report_type, ReportType):
            report_type_str = report_type.value
        else:
            report_type_str = report_type
        
        # 타입별 normalize 함수 매핑
        normalize_map = {
            "daily": self.normalize_daily,
            "weekly": self.normalize_weekly,
            "monthly": self.normalize_monthly,
            "performance": self.normalize_performance
        }
        
        normalize_func = normalize_map.get(report_type_str)
        if not normalize_func:
            raise ValueError(f"지원하지 않는 보고서 타입: {report_type_str}")
        
        return normalize_func(raw_json)

