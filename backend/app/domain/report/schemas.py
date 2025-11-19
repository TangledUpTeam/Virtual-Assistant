"""
보고서 관련 스키마 정의
"""
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from datetime import date
from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """보고서 타입"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    PERFORMANCE = "performance"


# ========================================
# 일일 업무 보고서 스키마
# ========================================
class DailyWorkDetail(BaseModel):
    """일일 업무 세부사항"""
    시간: str = Field(..., description="시간대 (예: 09:00 - 10:00)")
    업무내용: str = Field(default="", description="업무 내용")
    비고: str = Field(default="", description="비고")


class DailyReportHeader(BaseModel):
    """일일 보고서 상단 정보"""
    작성일자: str = Field(default="", description="작성 일자")
    성명: str = Field(default="", description="작성자 성명")


class DailyReportSchema(BaseModel):
    """일일 업무 보고서 전체 구조"""
    문서제목: str = Field(default="일일 업무 보고서")
    상단정보: DailyReportHeader
    금일_진행_업무: str = Field(default="", description="금일 진행 업무 요약")
    세부업무: List[DailyWorkDetail] = Field(default_factory=list)
    미종결_업무사항: str = Field(default="", description="미종결 업무사항")
    익일_업무계획: str = Field(default="", description="익일 업무계획")
    특이사항: str = Field(default="", description="특이사항")


# ========================================
# 주간 업무 보고서 스키마
# ========================================
class WeeklyGoal(BaseModel):
    """주간 업무 목표"""
    항목: str = Field(..., description="항목 번호")
    목표: str = Field(default="", description="목표 내용")
    비고: str = Field(default="", description="비고")


class DayWork(BaseModel):
    """요일별 업무"""
    업무내용: str = Field(default="", description="업무 내용")
    비고: str = Field(default="", description="비고")


class WeeklyReportHeader(BaseModel):
    """주간 보고서 상단 정보"""
    작성일자: str = Field(default="", description="작성 일자")
    성명: str = Field(default="", description="작성자 성명")


class WeeklyReportSchema(BaseModel):
    """주간 업무 보고서 전체 구조"""
    문서제목: str = Field(default="주간 업무 보고서")
    상단정보: WeeklyReportHeader
    주간업무목표: List[WeeklyGoal] = Field(default_factory=list)
    요일별_세부_업무: Dict[str, DayWork] = Field(default_factory=dict)
    주간_중요_업무: str = Field(default="", description="주간 중요 업무")
    특이사항: str = Field(default="", description="특이사항")


# ========================================
# 월간 업무 보고서 스키마
# ========================================
class MonthlyKPI(BaseModel):
    """월간 핵심 지표"""
    신규_계약_건수: Dict[str, str] = Field(default_factory=dict)
    유지_계약_건수: Dict[str, str] = Field(default_factory=dict)
    상담_진행_건수: Dict[str, str] = Field(default_factory=dict)


class WeekWork(BaseModel):
    """주차별 업무"""
    업무내용: str = Field(default="", description="업무 내용")
    비고: str = Field(default="", description="비고")


class MonthlyReportHeader(BaseModel):
    """월간 보고서 상단 정보"""
    월: str = Field(default="", description="해당 월")
    작성일자: str = Field(default="", description="작성 일자")
    성명: str = Field(default="", description="작성자 성명")


class MonthlyReportSchema(BaseModel):
    """월간 업무 보고서 전체 구조"""
    문서제목: str = Field(default="월간 업무 보고서")
    상단정보: MonthlyReportHeader
    월간_핵심_지표: MonthlyKPI
    주차별_세부_업무: Dict[str, WeekWork] = Field(default_factory=dict)
    익월_계획: str = Field(default="", description="익월 계획")


# ========================================
# 실적 보고서 스키마
# ========================================
class PerformanceIndicator(BaseModel):
    """주요 지표"""
    건수: str = Field(default="", description="건수")


class CustomerGraph(BaseModel):
    """고객 그래프"""
    항목명: str = Field(default="계약한 고객 수")
    분기1: str = Field(default="", description="1/4분기", alias="1/4분기")
    분기2: str = Field(default="", description="2/4분기", alias="2/4분기")
    분기3: str = Field(default="", description="3/4분기", alias="3/4분기")
    분기4: str = Field(default="", description="4/4분기", alias="4/4분기")


class QuarterMonths(BaseModel):
    """분기별 월"""
    월1: str = Field(default="", alias="1월")
    월2: str = Field(default="", alias="2월")
    월3: str = Field(default="", alias="3월")


class HalfYear(BaseModel):
    """반기"""
    분기1: QuarterMonths = Field(default_factory=QuarterMonths, alias="1/4분기")
    분기2: QuarterMonths = Field(default_factory=QuarterMonths, alias="2/4분기")


class CalendarData(BaseModel):
    """달력 데이터"""
    상반기: HalfYear
    하반기: HalfYear


class PerformanceReportHeader(BaseModel):
    """실적 보고서 상단 정보"""
    작성일자: str = Field(default="", description="작성 일자")
    성명: str = Field(default="", description="작성자 성명")


class PerformanceReportSchema(BaseModel):
    """분기별 실적 보고서 전체 구조"""
    문서제목: str = Field(default="분기별 실적 보고서")
    상단정보: PerformanceReportHeader
    주요지표: Dict[str, Any] = Field(default_factory=dict)
    달력: CalendarData
    이슈_및_계획: str = Field(default="", description="이슈 및 계획")
    비고: str = Field(default="", description="비고")


# ========================================
# Canonical 스키마 (통합 보고서 스키마)
# ========================================
class TaskItem(BaseModel):
    """작업 항목"""
    task_id: Optional[str] = Field(default=None, description="작업 ID")
    title: str = Field(..., description="작업 제목")
    description: str = Field(default="", description="작업 설명")
    time_start: Optional[str] = Field(default=None, description="시작 시간 (HH:MM)")
    time_end: Optional[str] = Field(default=None, description="종료 시간 (HH:MM)")
    status: Optional[str] = Field(default=None, description="상태 (완료/진행중/미완료)")
    note: str = Field(default="", description="비고")


class KPIItem(BaseModel):
    """KPI 항목"""
    kpi_name: str = Field(..., description="KPI 이름")
    value: str = Field(default="", description="값")
    unit: Optional[str] = Field(default=None, description="단위")
    category: Optional[str] = Field(default=None, description="카테고리")
    note: str = Field(default="", description="비고")


class CanonicalReport(BaseModel):
    """통합 보고서 스키마"""
    report_id: str = Field(..., description="보고서 ID")
    report_type: Literal["daily", "weekly", "monthly", "performance"] = Field(..., description="보고서 타입")
    owner: str = Field(default="", description="작성자")
    period_start: Optional[date] = Field(default=None, description="시작 일자")
    period_end: Optional[date] = Field(default=None, description="종료 일자")
    tasks: List[TaskItem] = Field(default_factory=list, description="작업 목록")
    kpis: List[KPIItem] = Field(default_factory=list, description="KPI 목록")
    issues: List[str] = Field(default_factory=list, description="이슈/미종결 사항")
    plans: List[str] = Field(default_factory=list, description="계획 사항")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


# ========================================
# 응답 스키마
# ========================================
class ReportParseResponse(BaseModel):
    """보고서 파싱 응답"""
    report_type: ReportType
    data: Dict[str, Any]
    message: str = Field(default="보고서를 성공적으로 파싱했습니다.")


class ReportParseWithCanonicalResponse(BaseModel):
    """보고서 파싱 응답 (Canonical 포함)"""
    report_type: str
    raw: Dict[str, Any] = Field(..., description="원본 Raw JSON")
    canonical: CanonicalReport = Field(..., description="정규화된 Canonical JSON")
    message: str = Field(default="보고서를 성공적으로 파싱했습니다.")


class ReportTypeDetectionResponse(BaseModel):
    """보고서 타입 감지 응답"""
    report_type: ReportType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

