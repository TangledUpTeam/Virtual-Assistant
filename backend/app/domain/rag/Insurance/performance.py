"""
Insurance RAG 성능 모니터링 모듈

각 단계별 처리 시간 및 성능 메트릭 수집
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager

from .utils import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """성능 메트릭 데이터 클래스"""
    step_name: str
    durations: List[float] = field(default_factory=list)
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    
    def add_duration(self, duration: float):
        """처리 시간 추가"""
        self.durations.append(duration)
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.avg_time = self.total_time / self.count
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "step_name": self.step_name,
            "count": self.count,
            "total_time": round(self.total_time, 2),
            "min_time": round(self.min_time, 2),
            "max_time": round(self.max_time, 2),
            "avg_time": round(self.avg_time, 2)
        }


class PerformanceMonitor:
    """
    성능 모니터링 클래스
    
    사용 예시:
        monitor = PerformanceMonitor()
        
        with monitor.measure("PDF 추출"):
            extract_pdf(pdf_path)
        
        monitor.report()
    """
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
    
    @contextmanager
    def measure(self, step_name: str):
        """
        처리 시간 측정 컨텍스트 매니저
        
        Args:
            step_name: 단계 이름
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record(step_name, duration)
    
    def record(self, step_name: str, duration: float):
        """
        처리 시간 기록
        
        Args:
            step_name: 단계 이름
            duration: 처리 시간 (초)
        """
        if step_name not in self.metrics:
            self.metrics[step_name] = PerformanceMetrics(step_name=step_name)
        
        self.metrics[step_name].add_duration(duration)
        logger.debug(f"[Performance] {step_name}: {duration:.2f}초")
    
    def report(self) -> Dict[str, Dict]:
        """
        성능 리포트 생성
        
        Returns:
            Dict: 단계별 성능 메트릭
        """
        report = {}
        
        print("\n" + "=" * 60)
        print("📊 성능 모니터링 리포트")
        print("=" * 60)
        
        for step_name, metrics in self.metrics.items():
            report[step_name] = metrics.to_dict()
            
            print(f"\n{step_name}:")
            print(f"  - 실행 횟수: {metrics.count}회")
            print(f"  - 총 시간: {metrics.total_time:.2f}초")
            print(f"  - 평균 시간: {metrics.avg_time:.2f}초")
            print(f"  - 최소 시간: {metrics.min_time:.2f}초")
            print(f"  - 최대 시간: {metrics.max_time:.2f}초")
        
        print("\n" + "=" * 60 + "\n")
        
        return report
    
    def reset(self):
        """메트릭 초기화"""
        self.metrics.clear()
        logger.info("성능 메트릭 초기화 완료")


# 싱글톤 인스턴스
_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """성능 모니터 싱글톤 인스턴스 반환"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor
