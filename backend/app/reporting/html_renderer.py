"""
HTML Report Renderer

Jinja2 템플릿 엔진을 사용하여 보고서를 HTML로 렌더링
"""
from pathlib import Path
from typing import Literal, Optional, Dict, Any
from datetime import date

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from app.domain.report.core.schemas import CanonicalReport


class HTMLReportRenderer:
    """HTML 보고서 렌더러"""
    
    # 프로젝트 루트 찾기
    _BASE_DIR = Path(__file__).resolve().parent.parent.parent
    
    # 템플릿 디렉토리
    TEMPLATE_DIR = _BASE_DIR / "Data" / "reports" / "html"
    
    # 출력 디렉토리 (타입별로 분리)
    OUTPUT_BASE_DIR = _BASE_DIR / "output"
    
    def __init__(self):
        """Jinja2 Environment 초기화"""
        # 출력 디렉토리 생성 (타입별로 분리)
        (self.OUTPUT_BASE_DIR / "daily").mkdir(parents=True, exist_ok=True)
        (self.OUTPUT_BASE_DIR / "weekly").mkdir(parents=True, exist_ok=True)
        (self.OUTPUT_BASE_DIR / "monthly").mkdir(parents=True, exist_ok=True)
        
        # Jinja2 Environment 설정
        self.env = Environment(
            loader=FileSystemLoader(str(self.TEMPLATE_DIR)),
            autoescape=True,  # XSS 방지
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 템플릿 파일명 매핑
        self.template_map = {
            "daily": "일일보고서.html",
            "weekly": "주간보고서.html",
            "monthly": "월간보고서.html"
        }
    
    def _convert_daily_to_context(self, report: CanonicalReport, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        일일보고서 CanonicalReport → 템플릿 context 변환
        
        Args:
            report: CanonicalReport 객체
            display_name: HTML 보고서에 표시할 이름 (우선 사용)
        
        Returns:
            템플릿에 전달할 context 딕셔너리
        """
        if not report.daily:
            raise ValueError("CanonicalReport must have daily data for daily report HTML generation")
        
        daily = report.daily
        
        # 날짜를 문자열로 변환 (YYYY-MM-DD 형식)
        작성일자 = report.period_start.strftime("%Y-%m-%d") if report.period_start else ""
        
        # 성명 결정: display_name 우선, 없으면 daily.header의 성명 사용
        # report.owner는 더 이상 사용하지 않음 (상수이므로)
        성명 = display_name or daily.header.get("성명", "")
        
        # 헤더 정보
        header = {
            "작성일자": daily.header.get("작성일자", 작성일자),
            "성명": 성명
        }
        
        # 세부 업무 목록 (최대 9개)
        detail_tasks = []
        for task in daily.detail_tasks[:9]:
            detail_tasks.append({
                "time_start": task.time_start or "",
                "time_end": task.time_end or "",
                "time_range": f"{task.time_start or ''} - {task.time_end or ''}".strip(" -"),
                "text": task.text or "",
                "note": task.note or ""
            })
        
        # 9개가 안 되면 빈 행으로 채우기
        while len(detail_tasks) < 9:
            detail_tasks.append({
                "time_start": "",
                "time_end": "",
                "time_range": "",
                "text": "",
                "note": ""
            })
        
        # 미종결 업무 (리스트를 줄바꿈 문자열로 변환)
        pending_text = "\n".join(daily.pending) if daily.pending else ""
        
        # 익일 계획 (리스트를 줄바꿈 문자열로 변환)
        plans_text = "\n".join(daily.plans) if daily.plans else ""
        
        return {
            "header": header,
            "summary_tasks": daily.todo_tasks or [],  # todo_tasks 사용 (하위 호환성을 위해 키는 summary_tasks 유지)
            "detail_tasks": detail_tasks,
            "pending": pending_text,
            "plans": plans_text,
            "notes": daily.notes or ""
        }
    
    def _convert_weekly_to_context(self, report: CanonicalReport, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        주간보고서 CanonicalReport → 템플릿 context 변환
        
        Args:
            report: CanonicalReport 객체
            display_name: HTML 보고서에 표시할 이름 (우선 사용)
        
        Returns:
            템플릿에 전달할 context 딕셔너리
        """
        if not report.weekly:
            raise ValueError("CanonicalReport must have weekly data for weekly report HTML generation")
        
        weekly = report.weekly
        
        # 날짜를 문자열로 변환 (YYYY-MM-DD 형식)
        작성일자 = report.period_end.strftime("%Y-%m-%d") if report.period_end else ""
        
        # 성명 결정: display_name 우선, 없으면 weekly.header의 성명 사용
        # report.owner는 더 이상 사용하지 않음 (상수이므로)
        성명 = display_name or weekly.header.get("성명", "")
        
        # 헤더 정보
        header = {
            "작성일자": weekly.header.get("작성일자", 작성일자),
            "성명": 성명
        }
        
        # 요일별 업무 (날짜 키를 요일명으로 변환)
        # weekday_tasks는 { "YYYY-MM-DD": ["업무1", "업무2"], ... } 형식
        weekday_tasks_map = {}
        day_names = ["월", "화", "수", "목", "금"]
        
        # 날짜를 정렬하여 요일명에 매핑
        sorted_dates = sorted(weekly.weekday_tasks.keys())[:5]
        for idx, date_str in enumerate(sorted_dates):
            if idx < len(day_names):
                weekday_tasks_map[day_names[idx]] = weekly.weekday_tasks[date_str]
        
        # 5개 요일 모두 채우기
        for day_name in day_names:
            if day_name not in weekday_tasks_map:
                weekday_tasks_map[day_name] = []
        
        return {
            "header": header,
            "weekly_goals": weekly.weekly_goals or [],
            "weekday_tasks": weekday_tasks_map,
            "weekly_highlights": weekly.weekly_highlights or [],
            "notes": weekly.notes or ""
        }
    
    def _convert_monthly_to_context(self, report: CanonicalReport, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        월간보고서 CanonicalReport → 템플릿 context 변환
        
        Args:
            report: CanonicalReport 객체
            display_name: HTML 보고서에 표시할 이름 (우선 사용)
        
        Returns:
            템플릿에 전달할 context 딕셔너리
        """
        if not report.monthly:
            raise ValueError("CanonicalReport must have monthly data for monthly report HTML generation")
        
        monthly = report.monthly
        
        # 날짜를 문자열로 변환
        월 = ""
        작성일자 = ""
        if report.period_start:
            월 = f"{report.period_start.year}-{report.period_start.month:02d}"
            작성일자 = report.period_start.strftime("%Y-%m-%d")
        
        # 성명 결정: display_name 우선, 없으면 monthly.header의 성명 사용
        # report.owner는 더 이상 사용하지 않음 (상수이므로)
        성명 = display_name or monthly.header.get("성명", "")
        
        # 헤더 정보
        상단정보 = {
            "월": monthly.header.get("월", 월),
            "작성일자": monthly.header.get("작성일자", 작성일자),
            "성명": 성명
        }
        
        # 주차별 세부 업무 변환
        # CanonicalReport: { "1주차": ["업무1", "업무2"], ... }
        # HTML 템플릿: { "1주": { "업무내용": "...", "비고": "..." }, ... }
        주차별_세부_업무 = {}
        for 주차_key, 업무_list in monthly.weekly_summaries.items():
            # "1주차" -> "1주" 변환
            if "주차" in 주차_key:
                주차 = 주차_key.replace("주차", "주")
            else:
                주차 = 주차_key
            
            # 리스트를 하나의 문자열로 합치기
            업무내용 = "\n".join(업무_list) if isinstance(업무_list, list) else str(업무_list)
            
            주차별_세부_업무[주차] = {
                "업무내용": 업무내용,
                "비고": ""
            }
        
        # 1주~5주까지 모두 채우기 (없으면 빈 값)
        # Jinja2 템플릿에서 쉽게 접근할 수 있도록 리스트로도 제공
        주차별_세부_업무_list = []
        for i in range(1, 6):
            주차 = f"{i}주"
            if 주차 not in 주차별_세부_업무:
                주차별_세부_업무[주차] = {
                    "업무내용": "",
                    "비고": ""
                }
            주차별_세부_업무_list.append({
                "주차": 주차,
                "업무내용": 주차별_세부_업무[주차]["업무내용"],
                "비고": 주차별_세부_업무[주차]["비고"]
            })
        
        return {
            "상단정보": 상단정보,
            "월간_핵심_지표": {
                "신규_계약_건수": {
                    "건수": "",
                    "비고": ""
                },
                "유지_계약_건수": {
                    "유지": "",
                    "갱신": "",
                    "미납_방지": "",
                    "비고": ""
                },
                "상담_진행_건수": {
                    "전화": "",
                    "방문": "",
                    "온라인": "",
                    "비고": ""
                }
            },
            "주차별_세부_업무": 주차별_세부_업무,
            "주차별_세부_업무_list": 주차별_세부_업무_list,
            "익월_계획": monthly.next_month_plan or ""
        }
    
    def _convert_to_context(
        self,
        report_type: Literal["daily", "weekly", "monthly"],
        report: CanonicalReport,
        display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CanonicalReport를 템플릿 context로 변환
        
        Args:
            report_type: 보고서 타입
            report: CanonicalReport 객체
            display_name: HTML 보고서에 표시할 이름 (우선 사용)
            
        Returns:
            템플릿에 전달할 context 딕셔너리
        """
        if report_type == "daily":
            return self._convert_daily_to_context(report, display_name)
        elif report_type == "weekly":
            return self._convert_weekly_to_context(report, display_name)
        elif report_type == "monthly":
            return self._convert_monthly_to_context(report, display_name)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    
    def render_report_html(
        self,
        report_type: Literal["daily", "weekly", "monthly"],
        data: Dict[str, Any],
        output_filename: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> Path:
        """
        보고서를 HTML로 렌더링
        
        Args:
            report_type: 보고서 타입 ("daily", "weekly", "monthly")
            data: CanonicalReport JSON 딕셔너리 또는 CanonicalReport 객체
            output_filename: 출력 파일명 (None이면 자동 생성)
            
        Returns:
            생성된 HTML 파일 경로
            
        Raises:
            ValueError: 잘못된 report_type 또는 데이터 형식
            TemplateNotFound: 템플릿 파일을 찾을 수 없음
        """
        # CanonicalReport 객체로 변환
        if isinstance(data, dict):
            report = CanonicalReport(**data)
        elif isinstance(data, CanonicalReport):
            report = data
        else:
            raise ValueError(f"data must be dict or CanonicalReport, got {type(data)}")
        
        # 템플릿 파일명 확인
        template_filename = self.template_map.get(report_type)
        if not template_filename:
            raise ValueError(f"Unknown report type: {report_type}")
        
        # 템플릿 로드
        try:
            template = self.env.get_template(template_filename)
        except TemplateNotFound:
            raise TemplateNotFound(
                f"Template not found: {template_filename} in {self.TEMPLATE_DIR}"
            )
        
        # CanonicalReport → context 변환 (display_name 전달)
        context = self._convert_to_context(report_type, report, display_name)
        
        # HTML 렌더링
        html_content = template.render(**context)
        
        # 출력 파일명 생성
        if output_filename is None:
            from app.reporting.pdf_generator.utils import format_korean_date
            
            if report_type == "daily":
                date_str = format_korean_date(report.period_start) if report.period_start else ""
                output_filename = f"일일보고서_{report.owner}_{date_str}.html"
            elif report_type == "weekly":
                date_str = format_korean_date(report.period_end) if report.period_end else ""
                output_filename = f"주간보고서_{report.owner}_{date_str}.html"
            elif report_type == "monthly":
                month_str = f"{report.period_start.month}월" if report.period_start else ""
                output_filename = f"월간보고서_{report.owner}_{month_str}.html"
        
        # 파일명에서 특수문자 제거 (URL 안전하게)
        import re
        output_filename = re.sub(r'[<>:"/\\|?*]', '_', output_filename)
        
        # 타입별 출력 디렉토리 선택
        if report_type == "daily":
            output_dir = self.OUTPUT_BASE_DIR / "daily"
        elif report_type == "weekly":
            output_dir = self.OUTPUT_BASE_DIR / "weekly"
        elif report_type == "monthly":
            output_dir = self.OUTPUT_BASE_DIR / "monthly"
        else:
            output_dir = self.OUTPUT_BASE_DIR  # 기본값
        
        # HTML 파일 저장
        output_path = output_dir / output_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML 생성 완료: {output_path}")
        
        return output_path


# 전역 렌더러 인스턴스 (싱글톤)
_renderer: Optional[HTMLReportRenderer] = None


def get_html_renderer() -> HTMLReportRenderer:
    """HTML 렌더러 싱글톤 인스턴스 반환"""
    global _renderer
    if _renderer is None:
        _renderer = HTMLReportRenderer()
    return _renderer


def render_report_html(
    report_type: Literal["daily", "weekly", "monthly"],
    data: Dict[str, Any],
    output_filename: Optional[str] = None,
    display_name: Optional[str] = None
) -> Path:
    """
    보고서를 HTML로 렌더링 (편의 함수)
    
    Args:
        report_type: 보고서 타입
        data: CanonicalReport JSON 딕셔너리
        output_filename: 출력 파일명
        display_name: HTML 보고서에 표시할 이름 (우선 사용)
        
    Returns:
        생성된 HTML 파일 경로
    """
    renderer = get_html_renderer()
    return renderer.render_report_html(report_type, data, output_filename, display_name)

