"""
Performance Report PDF Generator

실적보고서를 PDF로 생성
템플릿: backend/Data/reports/실적 보고서 양식.pdf
"""
from datetime import date
from typing import Optional
from pathlib import Path

from app.reporting.pdf_generator.base import BasePDFGenerator
from app.reporting.pdf_generator.utils import format_korean_date, truncate_text
from app.domain.report.schemas import CanonicalReport


class PerformanceReportPDFGenerator(BasePDFGenerator):
    """실적보고서 PDF 생성기"""
    
    def __init__(self):
        super().__init__("실적 보고서 양식.pdf")
    
    def generate(
        self, 
        report: CanonicalReport,
        output_filename: Optional[str] = None
    ) -> bytes:
        """
        실적보고서 PDF 생성
        
        Args:
            report: CanonicalReport 객체 (performance 타입)
            output_filename: 출력 파일명
            
        Returns:
            PDF 바이트 스트림
        """
        self._init_canvas()
        
        # ========================================
        # 헤더: 작성일자, 성명, 기간
        # ========================================
        작성일자 = format_korean_date(report.period_end)
        성명 = report.owner
        기간 = f"{format_korean_date(report.period_start)} ~ {format_korean_date(report.period_end)}"
        
        self.draw_text(420, self._to_pdf_y(80), 작성일자, font_size=11)  # TODO: 좌표 조정
        self.draw_text(450, self._to_pdf_y(110), 성명, font_size=11)  # TODO: 좌표 조정
        self.draw_text(70, self._to_pdf_y(140), f"기간: {기간}", font_size=10)  # TODO: 좌표 조정
        
        # ========================================
        # 주요 지표 (KPIs) - 가장 중요한 부분
        # ========================================
        kpi_start_y = 200  # TODO: 좌표 조정
        kpi_col_width = 180
        
        # KPI를 2열로 배치
        for idx, kpi in enumerate(report.kpis[:10]):  # 최대 10개
            row = idx // 2
            col = idx % 2
            
            x = 70 + (col * kpi_col_width)  # TODO: 좌표 조정
            y = self._to_pdf_y(kpi_start_y + (row * 35))
            
            # KPI 이름: 값 단위
            kpi_text = f"{kpi.kpi_name}"
            value_text = f"{kpi.value} {kpi.unit or ''}"
            
            self.draw_text(x, y, kpi_text, font_size=9, color=(0.3, 0.3, 0.3))
            self.draw_text(x, y - 15, value_text, font_size=11, color=(0, 0, 0))
        
        # ========================================
        # KPI 관련 업무 내역 (tasks)
        # ========================================
        if report.tasks:
            task_start_y = 450  # TODO: 좌표 조정
            
            self.draw_text(70, self._to_pdf_y(task_start_y), "주요 활동 내역", font_size=12)
            
            for idx, task in enumerate(report.tasks[:8]):  # 최대 8개
                task_y = task_start_y + 40 + (idx * 30)
                
                # 날짜 (있으면)
                date_text = ""
                if task.time_start:
                    date_text = f"[{task.time_start}]"
                
                # 업무 내용
                task_text = f"• {date_text} {truncate_text(task.title, 50)}"
                
                self.draw_text(
                    x=80,  # TODO: 좌표 조정
                    y=self._to_pdf_y(task_y),
                    text=task_text,
                    font_size=9
                )
        
        # ========================================
        # 이슈 및 계획 (issues)
        # ========================================
        if report.issues:
            이슈_y = 700  # TODO: 좌표 조정
            
            self.draw_text(70, self._to_pdf_y(이슈_y), "이슈 및 계획", font_size=12)
            
            이슈_텍스트 = "\n".join([f"• {issue}" for issue in report.issues[:5]])
            self.draw_multiline_text(
                x=80,  # TODO: 좌표 조정
                y=self._to_pdf_y(이슈_y + 30),
                text=이슈_텍스트,
                font_size=10,
                line_height=14
            )
        
        # ========================================
        # 비고 (metadata에서 추출)
        # ========================================
        비고 = report.metadata.get('notes', '')
        if 비고:
            self.draw_multiline_text(
                x=70,  # TODO: 좌표 조정
                y=self._to_pdf_y(800),
                text=f"비고: {비고}",
                font_size=9,
                line_height=12
            )
        
        self.save_overlay()
        
        if output_filename is None:
            output_filename = f"실적보고서_{report.owner}_{format_korean_date(report.period_start)}.pdf"
        
        # 실적 보고서 전용 디렉토리에 저장
        performance_dir = self.OUTPUT_DIR / "performance"
        performance_dir.mkdir(parents=True, exist_ok=True)
        output_path = performance_dir / output_filename
        pdf_bytes = self.merge_with_template(output_path)
        
        return pdf_bytes


def generate_performance_pdf_from_json(report_json: dict, output_filename: Optional[str] = None) -> bytes:
    """JSON에서 직접 PDF 생성"""
    report = CanonicalReport(**report_json)
    generator = PerformanceReportPDFGenerator()
    return generator.generate(report, output_filename)

