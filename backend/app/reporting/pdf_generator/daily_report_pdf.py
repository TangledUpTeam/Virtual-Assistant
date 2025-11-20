"""
Daily Report PDF Generator

일일보고서를 PDF로 생성
템플릿: backend/Data/reports/일일 업무 보고서.pdf
"""
from datetime import date
from typing import Optional
from pathlib import Path

from app.reporting.pdf_generator.base import BasePDFGenerator
from app.reporting.pdf_generator.utils import format_korean_date, truncate_text
from app.domain.report.schemas import CanonicalReport


class DailyReportPDFGenerator(BasePDFGenerator):
    """일일보고서 PDF 생성기"""
    
    def __init__(self):
        # 템플릿 파일명 (실제 파일명에 맞게 수정 필요)
        super().__init__("일일 업무 보고서.pdf")
    
    def generate(
        self, 
        report: CanonicalReport,
        output_filename: Optional[str] = None
    ) -> bytes:
        """
        일일보고서 PDF 생성
        
        Args:
            report: CanonicalReport 객체 (daily 타입)
            output_filename: 출력 파일명 (None이면 자동 생성)
            
        Returns:
            PDF 바이트 스트림
        """
        # Canvas 초기화
        self._init_canvas()
        
        # ========================================
        # 헤더: 작성일자, 성명
        # ========================================
        # TODO: 실제 템플릿에 맞게 좌표 조정 필요
        작성일자 = format_korean_date(report.period_start)
        성명 = report.owner
        
        # 작성일자 (오른쪽 상단)
        self.draw_text(420, self._to_pdf_y(80), 작성일자, font_size=11)  # TODO: 좌표 미세조정
        
        # 성명 (오른쪽 상단 아래)
        self.draw_text(450, self._to_pdf_y(110), 성명, font_size=11)  # TODO: 좌표 미세조정
        
        # ========================================
        # 금일 진행 업무 (요약)
        # ========================================
        금일_진행_업무 = report.metadata.get('summary', '')
        if 금일_진행_업무:
            # TODO: 템플릿의 "금일 진행 업무" 섹션 좌표
            self.draw_multiline_text(
                x=70,  # TODO: 좌표 미세조정
                y=self._to_pdf_y(180),  # TODO: 좌표 미세조정
                text=금일_진행_업무,
                font_size=10,
                line_height=14,
                max_width=450
            )
        
        # ========================================
        # 세부업무 (시간대별 - 최대 9칸)
        # ========================================
        # TODO: 템플릿의 표 시작 좌표 확인 필요
        table_start_y = 250  # TODO: 실제 표 시작 위치로 조정
        row_height = 30  # TODO: 실제 행 높이로 조정
        
        # 시간대별 업무를 최대 9개까지 표시
        tasks = report.tasks[:9] if len(report.tasks) > 9 else report.tasks
        
        for idx, task in enumerate(tasks):
            # 각 행의 Y 좌표 계산
            current_y = self._to_pdf_y(table_start_y + (idx * row_height))
            
            # 시간 (09:00 - 10:00)
            time_text = ""
            if task.time_start and task.time_end:
                time_text = f"{task.time_start} - {task.time_end}"
            elif task.time_start:
                time_text = task.time_start
            
            self.draw_text(
                x=70,  # TODO: 시간 열 X 좌표 조정
                y=current_y,
                text=time_text,
                font_size=9
            )
            
            # 업무내용
            업무내용 = task.description or task.title
            업무내용 = truncate_text(업무내용, max_length=40)  # 너무 길면 자르기
            
            self.draw_text(
                x=150,  # TODO: 업무내용 열 X 좌표 조정
                y=current_y,
                text=업무내용,
                font_size=9
            )
            
            # 비고
            비고 = task.note or ""
            if 비고:
                비고 = truncate_text(비고, max_length=20)
                self.draw_text(
                    x=450,  # TODO: 비고 열 X 좌표 조정
                    y=current_y,
                    text=비고,
                    font_size=9
                )
        
        # ========================================
        # 미종결 업무사항
        # ========================================
        if report.issues:
            미종결_업무 = ", ".join(report.issues)
            self.draw_multiline_text(
                x=70,  # TODO: 좌표 미세조정
                y=self._to_pdf_y(550),  # TODO: 좌표 미세조정
                text=미종결_업무,
                font_size=10,
                line_height=14
            )
        
        # ========================================
        # 익일 업무계획
        # ========================================
        익일_업무계획 = report.metadata.get('next_plan', '')
        if 익일_업무계획:
            self.draw_multiline_text(
                x=70,  # TODO: 좌표 미세조정
                y=self._to_pdf_y(620),  # TODO: 좌표 미세조정
                text=익일_업무계획,
                font_size=10,
                line_height=14
            )
        
        # ========================================
        # 특이사항
        # ========================================
        특이사항 = report.metadata.get('notes', '')
        if 특이사항:
            self.draw_multiline_text(
                x=70,  # TODO: 좌표 미세조정
                y=self._to_pdf_y(690),  # TODO: 좌표 미세조정
                text=특이사항,
                font_size=10,
                line_height=14
            )
        
        # Overlay 저장
        self.save_overlay()
        
        # 템플릿과 병합
        if output_filename is None:
            output_filename = f"일일보고서_{report.owner}_{format_korean_date(report.period_start)}.pdf"
        
        # 일일 보고서 전용 디렉토리에 저장
        daily_dir = self.OUTPUT_DIR / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        output_path = daily_dir / output_filename
        pdf_bytes = self.merge_with_template(output_path)
        
        return pdf_bytes


def generate_daily_pdf_from_json(report_json: dict, output_filename: Optional[str] = None) -> bytes:
    """
    JSON에서 직접 PDF 생성 (편의 함수)
    
    Args:
        report_json: CanonicalReport JSON dict
        output_filename: 출력 파일명
        
    Returns:
        PDF 바이트 스트림
    """
    report = CanonicalReport(**report_json)
    generator = DailyReportPDFGenerator()
    return generator.generate(report, output_filename)

