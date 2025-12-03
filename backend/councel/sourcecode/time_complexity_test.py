"""
Performance Analysis Tool
생성날짜: 2025.12.03
설명: Python 파일의 모든 함수에 대해 실행 시간, 시간복잡도, 공간복잡도, 메모리 사용량, 병목 구간을 분석
"""

import os
import sys
import time
import re
import tracemalloc
import inspect
import importlib.util
import traceback
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime
import json
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 차트 생성


class FunctionAnalyzer:
    """함수 분석 메인 클래스"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.module = None
        self.functions = {}
        self.classes = {}
        self.results = []
        
    def load_module(self) -> bool:
        """절대 경로에서 모듈 동적 로드"""
        try:
            if not self.file_path.exists():
                print(f"❌ 파일을 찾을 수 없습니다: {self.file_path}")
                return False
            
            # 모듈 이름 생성
            module_name = self.file_path.stem
            
            # 모듈 스펙 생성
            spec = importlib.util.spec_from_file_location(module_name, self.file_path)
            if spec is None or spec.loader is None:
                print(f"❌ 모듈 스펙을 생성할 수 없습니다: {self.file_path}")
                return False
            
            # 모듈 로드
            self.module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = self.module
            spec.loader.exec_module(self.module)
            
            print(f"✅ 모듈 로드 성공: {module_name}")
            return True
            
        except Exception as e:
            print(f"❌ 모듈 로드 실패: {e}")
            traceback.print_exc()
            return False
    
    def extract_functions(self):
        """모듈의 모든 함수와 클래스 메서드 추출"""
        if self.module is None:
            return
        
        # 일반 함수 추출
        for name, obj in inspect.getmembers(self.module, inspect.isfunction):
            if obj.__module__ == self.module.__name__:
                try:
                    source_code = inspect.getsource(obj)
                    source_lines = len(source_code.split('\n'))
                except:
                    source_code = ""
                    source_lines = 0
                
                self.functions[name] = {
                    'type': 'function',
                    'callable': obj,
                    'signature': str(inspect.signature(obj)),
                    'source_lines': source_lines,
                    'source_code': source_code
                }
        
        # 클래스 및 메서드 추출
        for class_name, class_obj in inspect.getmembers(self.module, inspect.isclass):
            if class_obj.__module__ == self.module.__name__:
                methods = {}
                for method_name, method_obj in inspect.getmembers(class_obj, inspect.isfunction):
                    if not method_name.startswith('_') or method_name == '__init__':
                        try:
                            source_code = inspect.getsource(method_obj)
                            source_lines = len(source_code.split('\n'))
                        except:
                            source_code = ""
                            source_lines = 0
                        
                        methods[method_name] = {
                            'type': 'method',
                            'callable': method_obj,
                            'signature': str(inspect.signature(method_obj)),
                            'source_lines': source_lines,
                            'source_code': source_code
                        }
                
                self.classes[class_name] = {
                    'class_obj': class_obj,
                    'methods': methods
                }
        
        total_functions = len(self.functions) + sum(len(c['methods']) for c in self.classes.values())
        print(f"✅ 함수 추출 완료: {len(self.functions)}개 함수, {len(self.classes)}개 클래스 ({total_functions}개 총 함수)")
    
    def measure_execution_time(self, func: Callable, args: tuple = (), kwargs: dict = None, iterations: int = 100) -> Dict[str, float]:
        """실행 시간 측정"""
        if kwargs is None:
            kwargs = {}
        
        times = []
        
        try:
            # 워밍업
            for _ in range(min(10, iterations)):
                try:
                    func(*args, **kwargs)
                except:
                    pass
            
            # 실제 측정
            for _ in range(iterations):
                start = time.perf_counter()
                try:
                    func(*args, **kwargs)
                    end = time.perf_counter()
                    times.append((end - start) * 1000)  # ms 단위
                except Exception as e:
                    # 실행 불가능한 함수
                    return {
                        'avg_time_ms': None,
                        'min_time_ms': None,
                        'max_time_ms': None,
                        'std_time_ms': None,
                        'error': str(e)
                    }
            
            return {
                'avg_time_ms': np.mean(times),
                'min_time_ms': np.min(times),
                'max_time_ms': np.max(times),
                'std_time_ms': np.std(times),
                'error': None
            }
            
        except Exception as e:
            return {
                'avg_time_ms': None,
                'min_time_ms': None,
                'max_time_ms': None,
                'std_time_ms': None,
                'error': str(e)
            }
    
    def measure_memory_usage(self, func: Callable, args: tuple = (), kwargs: dict = None) -> Dict[str, float]:
        """메모리 사용량 측정"""
        if kwargs is None:
            kwargs = {}
        
        try:
            tracemalloc.start()
            
            try:
                func(*args, **kwargs)
            except:
                pass
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            return {
                'current_mb': current / (1024 * 1024),
                'peak_mb': peak / (1024 * 1024),
                'error': None
            }
            
        except Exception as e:
            tracemalloc.stop()
            return {
                'current_mb': None,
                'peak_mb': None,
                'error': str(e)
            }
    
    def estimate_time_complexity(self, execution_time: Dict, source_lines: int, source_code: str = "") -> str:
        """시간복잡도 추정 (소스 코드 분석만 사용)"""
        # 소스 코드가 없으면 소스 라인 수 기반으로 기본 추정
        if not source_code:
            # 소스 라인 수만으로 기본 추정
            if source_lines < 10:
                return "O(1) - 상수"
            elif source_lines < 30:
                return "O(n) - 선형"
            elif source_lines < 100:
                return "O(n log n) - 선형로그"
            else:
                return "O(n²) - 이차"
        
        try:
            # 소스 코드에서 루프 패턴 분석
            nested_loops = 0
            has_while = 'while' in source_code.lower()
            has_for = 'for' in source_code.lower()
            has_nested_for = source_code.count('for ') >= 2
            
            # 재귀 함수 체크 (함수명이 소스 코드에 다시 나타나는지 확인)
            has_recursion = False
            func_def_match = re.search(r'def\s+(\w+)', source_code)
            if func_def_match:
                func_name = func_def_match.group(1)
                # 함수명이 함수 본문에서 다시 호출되는지 확인
                func_body = source_code.split(':', 1)[1] if ':' in source_code else source_code
                has_recursion = func_name in func_body or f'self.{func_name}' in func_body
            
            # 중첩된 for 루프 개수 추정
            lines = source_code.split('\n')
            indent_levels = []
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith('for ') or stripped.startswith('while '):
                    indent = len(line) - len(stripped)
                    indent_levels.append(indent)
            
            # 중첩 레벨 계산
            if len(indent_levels) > 1:
                nested_loops = len(set(indent_levels))
            
            # 소스 코드 기반 추정
            if nested_loops >= 3:
                return "O(n³+) - 삼차 이상"
            elif nested_loops == 2:
                return "O(n²) - 이차"
            elif has_nested_for:
                return "O(n²) - 이차"
            elif has_recursion:
                # 재귀 함수는 일반적으로 O(n) 또는 O(log n)
                if source_lines < 20:
                    return "O(log n) - 로그"
                else:
                    return "O(n) - 선형"
            elif has_for or has_while:
                # 단일 루프
                if source_lines < 30:
                    return "O(n) - 선형"
                else:
                    return "O(n log n) - 선형로그"
            else:
                # 루프가 없으면 O(1)
                return "O(1) - 상수"
                
        except Exception as e:
            return f"N/A (오류: {str(e)})"
    
    def estimate_space_complexity(self, memory_mb: float, source_lines: int, source_code: str = "") -> str:
        """공간복잡도 추정 (소스 코드 분석만 사용)"""
        # 소스 코드가 없으면 소스 라인 수 기반으로 기본 추정
        if not source_code:
            # 소스 라인 수만으로 기본 추정
            if source_lines < 10:
                return "O(1) - 상수"
            elif source_lines < 30:
                return "O(n) - 선형"
            elif source_lines < 100:
                return "O(n) - 선형"
            else:
                return "O(n²) - 이차"
        
        try:
            # 리스트, 딕셔너리, 배열 등의 자료구조 사용 패턴 분석
            has_list_comp = '[' in source_code and 'for' in source_code
            has_dict_comp = '{' in source_code and 'for' in source_code
            has_nested_list = source_code.count('[') >= 3
            has_recursion = False
            
            # 재귀 함수 체크
            func_def_match = re.search(r'def\s+(\w+)', source_code)
            if func_def_match:
                func_name = func_def_match.group(1)
                func_body = source_code.split(':', 1)[1] if ':' in source_code else source_code
                has_recursion = func_name in func_body or f'self.{func_name}' in func_body
            
            # 중첩 루프 개수
            lines = source_code.split('\n')
            indent_levels = []
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith('for ') or stripped.startswith('while '):
                    indent = len(line) - len(stripped)
                    indent_levels.append(indent)
            
            nested_loops = len(set(indent_levels)) if len(indent_levels) > 1 else 0
            
            # 공간복잡도 추정
            if nested_loops >= 3 or has_nested_list:
                return "O(n³+) - 삼차 이상"
            elif nested_loops == 2 or (has_list_comp and has_dict_comp):
                return "O(n²) - 이차"
            elif has_list_comp or has_dict_comp or nested_loops == 1:
                return "O(n) - 선형"
            elif has_recursion:
                return "O(log n) - 로그"
            else:
                return "O(1) - 상수"
                
        except Exception as e:
            return "N/A"
    
    def analyze_all_functions(self):
        """모든 함수 분석"""
        print("\n" + "="*60)
        print("함수 분석 시작")
        print("="*60)
        
        # 일반 함수 분석
        for func_name, func_info in self.functions.items():
            print(f"\n📊 분석 중: {func_name}()")
            result = self._analyze_single_function(func_name, func_info, None)
            self.results.append(result)
        
        # 클래스 메서드 분석
        for class_name, class_info in self.classes.items():
            print(f"\n📦 클래스: {class_name}")
            
            # 클래스 인스턴스 생성 시도
            instance = None
            try:
                # __init__에 필요한 인자가 없으면 생성
                init_sig = inspect.signature(class_info['class_obj'].__init__)
                params = [p for p in init_sig.parameters.values() if p.name != 'self']
                
                # 기본값이 있는 파라미터는 제외 (필수 인자만 확인)
                required_params = [p for p in params if p.default == inspect.Parameter.empty]
                
                if not required_params:
                    # 기본값만 있는 경우 기본값으로 인스턴스 생성
                    instance = class_info['class_obj']()
                else:
                    print(f"  ⚠️  __init__에 필수 인자가 필요하여 인스턴스 생성 불가: {[p.name for p in required_params]}")
            except Exception as e:
                print(f"  ⚠️  인스턴스 생성 실패: {e}")
            
            for method_name, method_info in class_info['methods'].items():
                full_name = f"{class_name}.{method_name}"
                print(f"  📊 분석 중: {full_name}()")
                result = self._analyze_single_function(full_name, method_info, instance)
                self.results.append(result)
        
        print("\n" + "="*60)
        print(f"✅ 분석 완료: 총 {len(self.results)}개 함수")
        print("="*60)
    
    def _analyze_single_function(self, name: str, func_info: dict, instance: Any = None) -> Dict:
        """단일 함수 분석"""
        result = {
            'name': name,
            'type': func_info['type'],
            'signature': func_info['signature'],
            'source_lines': func_info['source_lines'],
            'execution_time': {},
            'memory_usage': {},
            'time_complexity': 'N/A',
            'space_complexity': 'N/A'
        }
        
        func = func_info['callable']
        
        # 소스 코드 가져오기 (복잡도 추정에 사용)
        # 먼저 저장된 소스 코드 사용, 없으면 다시 시도
        source_code = func_info.get('source_code', '')
        
        if not source_code:
            # 저장된 소스 코드가 없으면 여러 방법 시도
            try:
                source_code = inspect.getsource(func_info['callable'])
            except (OSError, TypeError, AttributeError):
                try:
                    # 메서드인 경우 클래스에서 직접 가져오기
                    if func_info['type'] == 'method' and '.' in name:
                        class_name, method_name = name.split('.', 1)
                        if hasattr(self.module, class_name):
                            class_obj = getattr(self.module, class_name)
                            if hasattr(class_obj, method_name):
                                method_obj = getattr(class_obj, method_name)
                                source_code = inspect.getsource(method_obj)
                except:
                    try:
                        # 함수의 파일과 라인 번호로 직접 읽기
                        func_file = inspect.getfile(func_info['callable'])
                        if func_file == str(self.file_path) or os.path.samefile(func_file, self.file_path):
                            func_lines = inspect.getsourcelines(func_info['callable'])
                            source_code = ''.join(func_lines[0])
                    except:
                        pass
        
        # 메서드인 경우 인스턴스가 필요
        if func_info['type'] == 'method':
            if instance is None:
                result['execution_time'] = {'error': '인스턴스 생성 불가'}
                result['memory_usage'] = {'error': '인스턴스 생성 불가'}
                # 인스턴스가 없어도 소스 코드 기반으로 복잡도 추정
                result['time_complexity'] = self.estimate_time_complexity(
                    {},
                    result['source_lines'],
                    source_code
                )
                result['space_complexity'] = self.estimate_space_complexity(
                    None,
                    result['source_lines'],
                    source_code
                )
                return result
            
            # 바인딩된 메서드 생성
            func = func.__get__(instance, instance.__class__)
        
        # 실행 시간 측정 (인자 없이 호출 시도)
        try:
            sig = inspect.signature(func_info['callable'])
            params = [p for p in sig.parameters.values() if p.name != 'self']
            
            # 필수 인자가 없는 경우에만 측정
            required_params = [p for p in params if p.default == inspect.Parameter.empty]
            
            if not required_params:
                result['execution_time'] = self.measure_execution_time(func, iterations=10)
                result['memory_usage'] = self.measure_memory_usage(func)
                
                # 시간 복잡도 추정
                result['time_complexity'] = self.estimate_time_complexity(
                    result['execution_time'],
                    result['source_lines'],
                    source_code
                )
                
                # 공간 복잡도 추정
                memory_mb = result['memory_usage'].get('peak_mb') if result['memory_usage'] else None
                result['space_complexity'] = self.estimate_space_complexity(
                    memory_mb,
                    result['source_lines'],
                    source_code
                )
            else:
                result['execution_time'] = {'error': '필수 인자 필요'}
                result['memory_usage'] = {'error': '필수 인자 필요'}
                
                # 필수 인자가 있어도 소스 코드 기반으로 복잡도 추정
                result['time_complexity'] = self.estimate_time_complexity(
                    {},
                    result['source_lines'],
                    source_code
                )
                result['space_complexity'] = self.estimate_space_complexity(
                    None,
                    result['source_lines'],
                    source_code
                )
        except Exception as e:
            result['execution_time'] = {'error': str(e)}
            result['memory_usage'] = {'error': str(e)}
            
            # 오류가 발생해도 소스 코드 기반으로 복잡도 추정 시도
            result['time_complexity'] = self.estimate_time_complexity(
                {},
                result['source_lines'],
                source_code
            )
            result['space_complexity'] = self.estimate_space_complexity(
                None,
                result['source_lines'],
                source_code
            )
        
        return result


class ReportGenerator:
    """마크다운 보고서 생성 클래스"""
    
    def __init__(self, results: List[Dict], file_path: str, output_dir: str):
        self.results = results
        self.file_path = Path(file_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 파일명에서 확장자 제거하여 사용
        self.base_filename = f"time_{self.file_path.stem}"
        
    def generate_report(self) -> str:
        """전체 보고서 생성"""
        report_path = self.output_dir / f"{self.base_filename}_{self.timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            # 헤더
            f.write(self._generate_header())
            
            # 요약
            f.write(self._generate_summary())
            
            # 병목 구간
            f.write(self._generate_bottlenecks())
            
            # 상세 테이블
            f.write(self._generate_summary_table())
            
            # 상세 분석
            f.write(self._generate_detailed_report())
            
            # 차트
            chart_paths = self._generate_charts()
            f.write(self._generate_chart_section(chart_paths))
            
            # 푸터
            f.write(self._generate_footer())
        
        print(f"\n✅ 보고서 생성 완료: {report_path}")
        return str(report_path)
    
    def _generate_header(self) -> str:
        """헤더 생성"""
        return f"""# Performance Analysis Report

**분석 파일**: `{self.file_path.name}`  
**파일 경로**: `{self.file_path}`  
**분석 일시**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**총 분석 함수**: {len(self.results)}개

---

"""
    
    def _generate_summary(self) -> str:
        """요약 생성"""
        successful = [r for r in self.results if r['execution_time'].get('avg_time_ms') is not None]
        failed = [r for r in self.results if r['execution_time'].get('error') is not None]
        
        total_time = sum(r['execution_time']['avg_time_ms'] for r in successful)
        total_memory = sum(r['memory_usage'].get('peak_mb', 0) for r in successful if r['memory_usage'].get('peak_mb'))
        
        return f"""## 📊 분석 요약

- **성공적으로 분석된 함수**: {len(successful)}개
- **분석 실패 함수**: {len(failed)}개
- **총 실행 시간**: {total_time:.2f} ms
- **총 메모리 사용량**: {total_memory:.2f} MB

---

"""
    
    def _generate_bottlenecks(self) -> str:
        """병목 구간 식별"""
        # 실행 시간 기준 정렬
        successful = [r for r in self.results if r['execution_time'].get('avg_time_ms') is not None]
        sorted_by_time = sorted(successful, key=lambda x: x['execution_time']['avg_time_ms'], reverse=True)
        
        top_5 = sorted_by_time[:5]
        
        report = """## 🔴 병목 구간 (실행 시간 Top 5)

| 순위 | 함수명 | 평균 실행 시간 | 메모리 사용량 | 시간복잡도 |
|------|--------|---------------|--------------|-----------|
"""
        
        for i, result in enumerate(top_5, 1):
            name = result['name']
            time_ms = result['execution_time']['avg_time_ms']
            memory = result['memory_usage'].get('peak_mb', 0)
            complexity = result['time_complexity']
            
            report += f"| {i} | `{name}` | {time_ms:.4f} ms | {memory:.4f} MB | {complexity} |\n"
        
        report += "\n---\n\n"
        return report
    
    def _generate_summary_table(self) -> str:
        """요약 테이블 생성"""
        report = """## 📋 전체 함수 분석 결과

| 함수명 | 타입 | 실행 시간 (ms) | 메모리 (MB) | 시간복잡도 | 공간복잡도 | 상태 |
|--------|------|---------------|------------|-----------|-----------|------|
"""
        
        for result in self.results:
            name = result['name']
            func_type = result['type']
            
            if result['execution_time'].get('avg_time_ms') is not None:
                time_str = f"{result['execution_time']['avg_time_ms']:.4f}"
                memory_str = f"{result['memory_usage'].get('peak_mb', 0):.4f}"
                time_complexity = result['time_complexity']
                space_complexity = result['space_complexity']
                status = "✅"
            else:
                time_str = "N/A"
                memory_str = "N/A"
                time_complexity = "N/A"
                space_complexity = "N/A"
                error = result['execution_time'].get('error', 'Unknown')
                status = f"❌ ({error[:20]}...)" if len(error) > 20 else f"❌ ({error})"
            
            report += f"| `{name}` | {func_type} | {time_str} | {memory_str} | {time_complexity} | {space_complexity} | {status} |\n"
        
        report += "\n---\n\n"
        return report
    
    def _generate_detailed_report(self) -> str:
        """상세 분석 보고서"""
        report = "## 📖 상세 분석\n\n"
        
        for result in self.results:
            report += f"### `{result['name']}`\n\n"
            report += f"- **타입**: {result['type']}\n"
            report += f"- **시그니처**: `{result['signature']}`\n"
            report += f"- **소스 라인 수**: {result['source_lines']}줄\n\n"
            
            if result['execution_time'].get('avg_time_ms') is not None:
                exec_time = result['execution_time']
                report += "**실행 시간 통계**:\n"
                report += f"- 평균: {exec_time['avg_time_ms']:.4f} ms\n"
                report += f"- 최소: {exec_time['min_time_ms']:.4f} ms\n"
                report += f"- 최대: {exec_time['max_time_ms']:.4f} ms\n"
                report += f"- 표준편차: {exec_time['std_time_ms']:.4f} ms\n\n"
                
                memory = result['memory_usage']
                report += "**메모리 사용량**:\n"
                report += f"- 현재: {memory.get('current_mb', 0):.4f} MB\n"
                report += f"- 최대: {memory.get('peak_mb', 0):.4f} MB\n\n"
                
                report += f"**시간복잡도**: {result['time_complexity']}\n"
                report += f"**공간복잡도**: {result['space_complexity']}\n\n"
            else:
                report += f"**분석 실패**: {result['execution_time'].get('error', 'Unknown')}\n\n"
            
            report += "---\n\n"
        
        return report
    
    def _complexity_to_score(self, complexity: str) -> float:
        """복잡도를 수치 점수로 변환"""
        if not complexity or complexity == 'N/A' or 'N/A' in complexity:
            return 0
        
        complexity_lower = complexity.lower()
        if 'o(1)' in complexity_lower or '상수' in complexity:
            return 1.0
        elif 'o(log n)' in complexity_lower or '로그' in complexity:
            return 2.0
        elif 'o(n)' in complexity_lower and 'log' not in complexity_lower and '선형' in complexity:
            return 3.0
        elif 'o(n log n)' in complexity_lower or '선형로그' in complexity:
            return 4.0
        elif 'o(n²)' in complexity_lower or '이차' in complexity:
            return 5.0
        elif 'o(n³' in complexity_lower or '삼차' in complexity:
            return 6.0
        else:
            return 0.0
    
    def _generate_charts(self) -> Dict[str, str]:
        """시각적 차트 생성 (소스 코드 분석 기반 복잡도)"""
        # charts/{파일명}/ 폴더에 저장
        chart_dir = self.output_dir / "charts" / self.base_filename
        chart_dir.mkdir(parents=True, exist_ok=True)
        
        chart_paths = {}
        
        # 복잡도가 계산된 함수들만 필터링
        analyzed = [r for r in self.results if r.get('time_complexity') and r['time_complexity'] != 'N/A' and 'N/A' not in r['time_complexity']]
        
        if analyzed and len(analyzed) > 0:
            # 함수 개수에 따라 차트 높이 조정
            num_funcs = len(analyzed)
            fig_height = max(6, num_funcs * 0.5)  # 최소 높이 보장
            
            names = [r['name'][:30] for r in analyzed]
            time_complexities = [r['time_complexity'] for r in analyzed]
            space_complexities = [r.get('space_complexity', 'N/A') for r in analyzed]
            
            # 복잡도를 점수로 변환
            time_scores = [self._complexity_to_score(tc) for tc in time_complexities]
            space_scores = [self._complexity_to_score(sc) for sc in space_complexities]
            
            # 1. 시간복잡도 막대 그래프
            plt.figure(figsize=(12, fig_height))
            
            # 함수가 1개일 때도 y축 레이블이 보이도록 조정
            if len(names) == 1:
                plt.barh([0], time_scores, color='skyblue')
                plt.yticks([0], names)
            else:
                plt.barh(names, time_scores, color='skyblue')
            
            plt.xlabel('시간복잡도 점수 (1=O(1), 2=O(log n), 3=O(n), 4=O(n log n), 5=O(n²), 6=O(n³+))')
            plt.ylabel('함수명')
            plt.title('함수별 시간복잡도 (소스 코드 분석 기반)')
            plt.xlim(0, 6.5)
            plt.xticks(range(1, 7), ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(n³+)'])
            plt.tight_layout()
            
            chart_path = chart_dir / f"{self.base_filename}_time_complexity_{self.timestamp}.png"
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            chart_paths['time_complexity'] = str(chart_path)
            
            # 2. 공간복잡도 차트
            plt.figure(figsize=(12, fig_height))
            
            if len(names) == 1:
                plt.barh([0], space_scores, color='lightcoral')
                plt.yticks([0], names)
            else:
                plt.barh(names, space_scores, color='lightcoral')
            
            plt.xlabel('공간복잡도 점수 (1=O(1), 2=O(log n), 3=O(n), 4=O(n log n), 5=O(n²), 6=O(n³+))')
            plt.ylabel('함수명')
            plt.title('함수별 공간복잡도 (소스 코드 분석 기반)')
            plt.xlim(0, 6.5)
            plt.xticks(range(1, 7), ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(n³+)'])
            plt.tight_layout()
            
            chart_path = chart_dir / f"{self.base_filename}_space_complexity_{self.timestamp}.png"
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            chart_paths['space_complexity'] = str(chart_path)
            
            # 3. 시간복잡도 vs 공간복잡도 산점도
            plt.figure(figsize=(10, 8))
            plt.scatter(time_scores, space_scores, alpha=0.6, s=100)
            
            for i, name in enumerate(names):
                plt.annotate(name[:15], (time_scores[i], space_scores[i]), 
                           fontsize=8, alpha=0.7)
            
            plt.xlabel('시간복잡도 점수')
            plt.ylabel('공간복잡도 점수')
            plt.title('시간복잡도 vs 공간복잡도 (소스 코드 분석 기반)')
            plt.xlim(0, 6.5)
            plt.ylim(0, 6.5)
            plt.xticks(range(1, 7), ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(n³+)'])
            plt.yticks(range(1, 7), ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(n³+)'])
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            chart_path = chart_dir / f"{self.base_filename}_complexity_scatter_{self.timestamp}.png"
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            chart_paths['scatter'] = str(chart_path)
        
        return chart_paths
    
    def _generate_chart_section(self, chart_paths: Dict[str, str]) -> str:
        """차트 섹션 생성"""
        if not chart_paths:
            return ""
        
        report = "## 📈 시각적 분석 (소스 코드 기반 복잡도)\n\n"
        
        # charts/{파일명}/ 경로로 상대 경로 생성
        chart_relative_path = f"charts/{self.base_filename}"
        
        if 'time_complexity' in chart_paths:
            report += "### 시간복잡도 분석\n\n"
            chart_name = Path(chart_paths['time_complexity']).name
            report += f"![시간복잡도]({chart_relative_path}/{chart_name})\n\n"
        
        if 'space_complexity' in chart_paths:
            report += "### 공간복잡도 분석\n\n"
            chart_name = Path(chart_paths['space_complexity']).name
            report += f"![공간복잡도]({chart_relative_path}/{chart_name})\n\n"
        
        if 'scatter' in chart_paths:
            report += "### 시간복잡도 vs 공간복잡도\n\n"
            chart_name = Path(chart_paths['scatter']).name
            report += f"![복잡도 비교]({chart_relative_path}/{chart_name})\n\n"
        
        report += "---\n\n"
        return report
    
    def _generate_footer(self) -> str:
        """푸터 생성"""
        return f"""## 📝 참고사항

- 실행 시간은 10회 반복 측정의 평균값입니다.
- 메모리 사용량은 `tracemalloc` 모듈로 측정되었습니다.
- 시간복잡도와 공간복잡도는 추정값이며 실제와 다를 수 있습니다.
- 필수 인자가 있는 함수는 분석에서 제외되었습니다.
- API 호출이나 외부 의존성이 있는 함수는 오류가 발생할 수 있습니다.

---

**생성 도구**: Performance Analysis Tool  
**생성 일시**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    def identify_bottlenecks(self) -> List[Dict]:
        """병목 구간 식별"""
        successful = [r for r in self.results if r['execution_time'].get('avg_time_ms') is not None]
        sorted_by_time = sorted(successful, key=lambda x: x['execution_time']['avg_time_ms'], reverse=True)
        return sorted_by_time[:5]


def main():
    """메인 실행 함수"""
    print("="*60)
    print("Performance Analysis Tool")
    print("="*60)
    print()
    
    # 사용자 입력
    file_path = input("분석할 Python 파일의 절대 경로를 입력하세요: ").strip()
    
    if not file_path:
        print("❌ 파일 경로가 입력되지 않았습니다.")
        return
    
    # 따옴표 제거
    file_path = file_path.strip('"').strip("'")
    
    # 분석기 초기화
    analyzer = FunctionAnalyzer(file_path)
    
    # 모듈 로드
    if not analyzer.load_module():
        return
    
    # 함수 추출
    analyzer.extract_functions()
    
    if not analyzer.functions and not analyzer.classes:
        print("❌ 분석할 함수를 찾을 수 없습니다.")
        return
    
    # 함수 분석
    analyzer.analyze_all_functions()
    
    # 보고서 생성
    output_dir = Path(__file__).parent.parent / "time_test"
    generator = ReportGenerator(analyzer.results, file_path, str(output_dir))
    report_path = generator.generate_report()
    
    print(f"\n✅ 분석 완료!")
    print(f"📄 보고서 위치: {report_path}")
    
    # 병목 구간 출력
    bottlenecks = generator.identify_bottlenecks()
    if bottlenecks:
        print("\n🔴 병목 구간 Top 5:")
        for i, result in enumerate(bottlenecks, 1):
            print(f"  {i}. {result['name']}: {result['execution_time']['avg_time_ms']:.4f} ms")


if __name__ == "__main__":
    main()

