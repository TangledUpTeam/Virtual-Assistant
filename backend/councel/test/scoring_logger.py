"""
상담 스코어링 로깅 시스템
생성날짜: 2025.11.26
설명: 상담 테스트 결과를 Markdown과 JSON 형식으로 기록
      단일 파일에 계속 추가하며, 사용자가 수동으로 수정하면 자동 백업
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import hashlib

# 스코어링 결과를 로깅하는 클래스
class ScoringLogger:
    
    # 초기화 함수
    def __init__(self, log_dir: str = None, log_file_prefix: str = "scoring_log"):

        if log_dir is None:
            # 현재 파일 기준으로 councel/test 경로 설정
            log_dir = Path(__file__).parent
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 로그 파일 경로 (파일명 지정 가능)
        self.md_log_path = self.log_dir / f"{log_file_prefix}.md"
        self.json_log_path = self.log_dir / f"{log_file_prefix}.json"
        
        # 파일 해시 저장 (수동 수정 감지용)
        self.md_hash_path = self.log_dir / f".{log_file_prefix}_md_hash"
        self.json_hash_path = self.log_dir / f".{log_file_prefix}_json_hash"
        
        # 초기화
        self._initialize_logs()
    
    # 파일 해시값 계산
    def _calculate_file_hash(self, file_path: Path) -> str:

        if not file_path.exists():
            return ""
        
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    # 파일 해시 저장
    def _save_hash(self, file_path: Path, hash_path: Path):

        file_hash = self._calculate_file_hash(file_path)
        with open(hash_path, 'w') as f:
            f.write(file_hash)
    
    # 저장된 해시 로드
    def _load_hash(self, hash_path: Path) -> str:

        if not hash_path.exists():
            return ""
        with open(hash_path, 'r') as f:
            return f.read().strip()
    
    # 파일이 수동으로 수정되어있는지 확인
    def _check_manual_modification(self, file_path: Path, hash_path: Path) -> bool:

        if not file_path.exists():
            return False
        
        current_hash = self._calculate_file_hash(file_path)
        saved_hash = self._load_hash(hash_path)
        
        is_modified = current_hash != saved_hash and saved_hash != ""
        
        return is_modified
    
    # 백업 파일 생성
    def _create_backup(self, file_path: Path):

        if not file_path.exists():
            return
        
        # 백업 번호 찾기
        backup_num = 1
        while True:
            backup_path = file_path.parent / f"{file_path.stem}_backup_{backup_num}{file_path.suffix}"
            if not backup_path.exists():
                break
            backup_num += 1
        
        # 백업 생성
        with open(file_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
    
    # 로그 파일 초기화
    def _initialize_logs(self):
        
        # Markdown 파일 체크 (파일과 해시 파일이 모두 있을 때만 검증)
        if self.md_log_path.exists() and self.md_hash_path.exists():
            md_modified = self._check_manual_modification(self.md_log_path, self.md_hash_path)
            if md_modified:
                self._create_backup(self.md_log_path)
                # 새 파일로 시작
                self.md_log_path.unlink()
        else:
            print(f"  - Markdown 파일 또는 해시 파일이 없음 - 수정 검증 건너뜀")
        
        # JSON 파일 체크 (파일과 해시 파일이 모두 있을 때만 검증)
        if self.json_log_path.exists() and self.json_hash_path.exists():
            json_modified = self._check_manual_modification(self.json_log_path, self.json_hash_path)
            if json_modified:
                print(f"[알림] {self.json_log_path.name} 파일이 수동으로 수정되었습니다. 백업을 생성합니다.")
                self._create_backup(self.json_log_path)
                # 새 파일로 시작
                self.json_log_path.unlink()
        else:
            print(f"  - JSON 파일 또는 해시 파일이 없음 - 수정 검증 건너뜀")
        
        # Markdown 파일 초기화
        if not self.md_log_path.exists():
            with open(self.md_log_path, 'w', encoding='utf-8') as f:
                f.write("# 상담 스코어링 로그\n\n")
                f.write("이 파일은 상담 시스템의 테스트 결과를 기록합니다.\n\n")
                f.write("---\n\n")
            self._save_hash(self.md_log_path, self.md_hash_path)
        else:
            # 기존 파일의 현재 해시를 저장 (정상적인 로그 추가를 수정으로 감지하지 않도록)
            self._save_hash(self.md_log_path, self.md_hash_path)
        
        # JSON 파일 초기화
        if not self.json_log_path.exists():
            with open(self.json_log_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            self._save_hash(self.json_log_path, self.json_hash_path)
        else:
            # 기존 파일의 현재 해시를 저장 (정상적인 로그 추가를 수정으로 감지하지 않도록)
            self._save_hash(self.json_log_path, self.json_hash_path)
    
    # 테스트 결과를 로깅
    def log_test_result(self, 
                       question: str,
                       answer: str,
                       chunks_used: List[Dict[str, Any]],
                       scoring: Dict[str, Any],
                       metadata: Dict[str, Any] = None):
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # Markdown 로그 추가
            self._append_markdown_log(timestamp, question, answer, chunks_used, scoring, metadata)
            
            # JSON 로그 추가
            self._append_json_log(timestamp, question, answer, chunks_used, scoring, metadata)
            
        except Exception as e:
            print(f"[오류] 로그 저장 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # 마크다운 로그 추가
    def _append_markdown_log(self,
                            timestamp: str,
                            question: str,
                            answer: str,
                            chunks_used: List[Dict[str, Any]],
                            scoring: Dict[str, Any],
                            metadata: Dict[str, Any] = None):
        
        try:
            with open(self.md_log_path, 'a', encoding='utf-8') as f:
                f.write(f"## 테스트 - {timestamp}\n\n")
                
                # 질문
                f.write(f"### 질문\n{question}\n\n")
                
                # 답변
                f.write(f"### 답변\n{answer}\n\n")
                
                # 사용된 청크
                f.write(f"### 사용된 청크\n\n")
                if chunks_used:
                    for i, chunk in enumerate(chunks_used, 1):
                        f.write(f"**청크 {i}**\n")
                        f.write(f"- **출처**: {chunk.get('source', '알 수 없음')}\n")
                        f.write(f"- **청크 ID**: `{chunk.get('chunk_id', 'N/A')}`\n")
                        f.write(f"- **거리**: {chunk.get('distance', 'N/A')}\n")
                        f.write(f"- **요약**: {chunk.get('summary_kr', 'N/A')}\n")
                        
                        # 메타데이터
                        if chunk.get('metadata'):
                            f.write(f"- **메타데이터**: {json.dumps(chunk['metadata'], ensure_ascii=False)}\n")
                        f.write("\n")
                else:
                    f.write("사용된 청크가 없습니다.\n\n")
                
                # 스코어링
                f.write(f"### 스코어링 결과\n\n")
                f.write(f"- **관련성 (Relevance)**: {scoring.get('relevance', 'N/A')}/10\n")
                f.write(f"- **정확성 (Accuracy)**: {scoring.get('accuracy', 'N/A')}/10\n")
                f.write(f"- **공감도 (Empathy)**: {scoring.get('empathy', 'N/A')}/10\n")
                f.write(f"- **실용성 (Practicality)**: {scoring.get('practicality', 'N/A')}/10\n")
                f.write(f"- **총점**: {scoring.get('total', 'N/A')}/40\n")
                f.write(f"- **코멘트**: {scoring.get('comment', 'N/A')}\n\n")
                
                # 추가 메타데이터
                if metadata:
                    f.write(f"### 추가 정보\n")
                    for key, value in metadata.items():
                        f.write(f"- **{key}**: {value}\n")
                    f.write("\n")
                
                f.write("---\n\n")
            
            # 해시 업데이트
            self._save_hash(self.md_log_path, self.md_hash_path)

        except Exception as e:
            print(f"[오류] Markdown 로그 추가 중 예외: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    #Json 로그 추가
    def _append_json_log(self,
                        timestamp: str,
                        question: str,
                        answer: str,
                        chunks_used: List[Dict[str, Any]],
                        scoring: Dict[str, Any],
                        metadata: Dict[str, Any] = None):
        
        try:
            # 기존 로그 읽기
            if self.json_log_path.exists():
                with open(self.json_log_path, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # 새 로그 항목 추가
            log_entry = {
                "timestamp": timestamp,
                "question": question,
                "answer": answer,
                "chunks_used": chunks_used,
                "scoring": scoring
            }
            
            if metadata:
                log_entry["metadata"] = metadata
            
            logs.append(log_entry)
            
            # 파일에 저장
            with open(self.json_log_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            # 해시 업데이트
            self._save_hash(self.json_log_path, self.json_hash_path)

        except Exception as e:
            print(f"[오류] JSON 로그 추가 중 예외: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # 모든 로그 가져오는 함수
    def get_all_logs(self) -> List[Dict[str, Any]]:

        if not self.json_log_path.exists():
            return []
        
        with open(self.json_log_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 로그 통계 정보 반환
    def get_statistics(self) -> Dict[str, Any]:

        logs = self.get_all_logs()
        
        if not logs:
            return {
                "total_tests": 0,
                "average_scores": {},
                "best_score": None,
                "worst_score": None
            }
        
        # 점수 집계
        scores = {
            "relevance": [],
            "accuracy": [],
            "empathy": [],
            "practicality": [],
            "total": []
        }
        
        for log in logs:
            scoring = log.get("scoring", {})
            for key in scores.keys():
                if key in scoring:
                    scores[key].append(scoring[key])
        
        # 평균 계산
        avg_scores = {}
        for key, values in scores.items():
            if values:
                avg_scores[key] = sum(values) / len(values)
        
        # 최고/최저 점수
        total_scores = scores["total"]
        best_idx = total_scores.index(max(total_scores)) if total_scores else None
        worst_idx = total_scores.index(min(total_scores)) if total_scores else None
        
        return {
            "total_tests": len(logs),
            "average_scores": avg_scores,
            "best_score": logs[best_idx] if best_idx is not None else None,
            "worst_score": logs[worst_idx] if worst_idx is not None else None
        }