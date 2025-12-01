"""
청크 파일 생성 스크립트
생성날짜: 2025.11.18
수정날짜: 2025.11.19 - Adler PDF 처리 추가
수정날짜: 2025.11.21 - Rogers 관련 코드 제거
리팩토링: 2025.11.25 - 1차 코드 리팩토링(쓸데 없는 print문 제거 및 코드 정리)
수정날짜: 2025.11.28 - Parent-Child Chunking 방식으로 변경
설명: Adler PDF 파일을 Parent-Child 구조로 청킹하여 개별 JSON 파일로 저장
      Parent: 1000 tokens, Child: 500 tokens
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any
import tiktoken
import fitz  # PyMuPDF

# 청크파일을 만드는 클래스
class ChunkCreator:

    # 초기화
    def __init__(self, max_tokens: int = 500, parent_max_tokens: int = 1000, overlap_ratio: float = 0.2):
        self.max_tokens = max_tokens # Child 청크당 최대 토큰 수
        self.parent_max_tokens = parent_max_tokens # Parent 청크당 최대 토큰 수
        self.overlap_ratio = overlap_ratio # Overlap 비율
        self.encoding = tiktoken.get_encoding("cl100k_base") # 토큰 인코딩 모델

    # 텍스트의 토큰 수 계산   
    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))
    
    # PDF에서 텍스트 추출(PyMuPDF(fitz)를 사용)
    def extract_text_from_pdf(self, pdf_path: Path) -> str:

        doc = fitz.open(pdf_path) # pdf 파일 열기
        full_text = [] # 전체 텍스트를 저장할 리스트
        
        # 페이지 수만큼 반복하면서 리스트에 텍스트 저장
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            full_text.append(text)
        
        doc.close()
        
        # 전체 텍스트 결합
        combined_text = '\n'.join(full_text)
        
        # 하이픈으로 끝나는 단어 복원 (예: "coun-\nseling" → "counseling")
        combined_text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', combined_text)
        
        return combined_text
    
    # PDF 텍스트 정제화
    # 정제화 규칙
    # 1. 페이지 번호 제거
    # 2. 표/그래프 특수문자 제거
    # 3. 참고문헌 섹션 제거
    # 4. URL, 이메일 제거
    # 5. 한글 제거
    # 6. 반복되는 특수문자 제거
    # 7. 과도한 공백 정리
    # 8. 앞뒤 공백 제거
    def clean_pdf_text(self, text: str) -> str:

        # 1. 페이지 번호 패턴 제거
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)  # 숫자만 있는 줄
        text = re.sub(r'^Page\s+\d+', '', text, flags=re.MULTILINE | re.IGNORECASE) # Page 번호 제거
        text = re.sub(r'^-\s*\d+\s*-$', '', text, flags=re.MULTILINE) # 하이픈으로 끝나는 단어 복원
        text = re.sub(r'^\[\d+\]$', '', text, flags=re.MULTILINE) # 대괄호에 둘러싸인 숫자 제거
        
        # 2. 표/그래프 특수문자 제거
        table_chars = ['│', '─', '┼', '├', '┤', '┬', '┴', '┌', '┐', '└', '┘', '║', '═', '╔', '╗', '╚', '╝', '╠', '╣', '╦', '╩', '╬']
        for char in table_chars:
            text = text.replace(char, '')
        
        # 3. 참고문헌 섹션 제거 (References, Bibliography 이후)
        ref_patterns = [
            r'\n\s*References\s*\n.*',
            r'\n\s*Bibliography\s*\n.*',
            r'\n\s*참고문헌\s*\n.*',
            r'\n\s*REFERENCES\s*\n.*',
            r'\n\s*BIBLIOGRAPHY\s*\n.*'
        ]
        for pattern in ref_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 4. URL 제거
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # 5. 이메일 주소 제거
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # 6. 한글 제거
        text = re.sub(r'[가-힣]+', '', text)
        
        # 7. 반복되는 특수문자 제거 (3개 이상 연속)
        # 예: ====, ----, ...., ****, ####, ____ 등
        text = re.sub(r'([=\-_.*#~`+]{3,})', '', text)
        
        # 8. 반복되는 짧은 줄 제거 (헤더/푸터 가능성)
        lines = text.split('\n')
        line_counts = {}
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 0 and len(stripped) < 50:  # 50자 이하의 짧은 줄만
                line_counts[stripped] = line_counts.get(stripped, 0) + 1
        
        # 3번 이상 반복되는 짧은 줄 제거
        repeated_lines = {line for line, count in line_counts.items() if count >= 3}
        lines = [line for line in lines if line.strip() not in repeated_lines]
        text = '\n'.join(lines)
        
        # 9. 과도한 공백 정리
        text = re.sub(r'\n{3,}', '\n\n', text)  # 3개 이상의 연속 줄바꿈을 2개로
        text = re.sub(r' {2,}', ' ', text)  # 2개 이상의 연속 공백을 1개로
        text = re.sub(r'\t+', ' ', text)  # 탭을 공백으로
        
        # 10. 앞뒤 공백 제거
        text = text.strip()
        
        return text
    
    # ==================== Adler 관련 메서드 ====================
    
    # Adler 파일명에서 메타데이터 추출
    def extract_metadata_adler(self, filename: str) -> Dict[str, Any]:

        # 확장자 제거
        clean_name = filename.replace('.pdf', '')
        parts = clean_name.split('_')
        
        file_category = parts[1] if len(parts) > 1 else "unknown"
        
        # 메타데이터
        metadata = {
            "author": "Adler",
            "source": filename,
            "category": file_category,
            "topic": "individual psychology",
            "tags": ["아들러"]
        }
        
        # 카테고리별 추가 태그
        if file_category == "case":
            metadata["tags"].extend(["사례연구", "상담"])
        elif file_category == "theory":
            metadata["tags"].extend(["이론", "개인심리학"])
        elif file_category == "interventions":
            metadata["tags"].extend(["개입기법", "치료"])
        elif file_category == "qna":
            metadata["tags"].extend(["질의응답", "FAQ"])
        elif file_category == "tone":
            metadata["tags"].extend(["어조", "성격"])
        
        return metadata
    
    # 파일명에서 메타데이터 추출
    def extract_metadata_from_filename(self, filename: str) -> Dict[str, Any]:
        return self.extract_metadata_adler(filename)
    
    # Parent 청크 생성 (큰 섹션을 parent_max_tokens 기준으로 분할)
    def split_into_parents(self, section_content: str) -> List[str]:

        token_count = self.count_tokens(section_content)
        
        if token_count <= self.parent_max_tokens:
            return [section_content]
        
        # 문단 단위로 분할 (빈 줄 기준)
        paragraphs = section_content.split('\n\n')
        
        parent_chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # 단일 문단이 parent_max_tokens를 초과하는 경우
            if para_tokens > self.parent_max_tokens:
                # 현재까지 모은 청크 저장
                if current_chunk:
                    parent_chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # 큰 문단을 줄 단위로 분할
                lines = para.split('\n')
                temp_chunk = []
                temp_tokens = 0
                
                for line in lines:
                    line_tokens = self.count_tokens(line)
                    if temp_tokens + line_tokens > self.parent_max_tokens:
                        if temp_chunk:
                            parent_chunks.append('\n'.join(temp_chunk))
                        temp_chunk = [line]
                        temp_tokens = line_tokens
                    else:
                        temp_chunk.append(line)
                        temp_tokens += line_tokens
                
                if temp_chunk:
                    parent_chunks.append('\n'.join(temp_chunk))
            
            # 현재 청크에 추가 가능한 경우
            elif current_tokens + para_tokens <= self.parent_max_tokens:
                current_chunk.append(para)
                current_tokens += para_tokens
            
            # 새로운 청크 시작
            else:
                if current_chunk:
                    parent_chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
        
        # 마지막 청크 추가
        if current_chunk:
            parent_chunks.append('\n\n'.join(current_chunk))
        
        return parent_chunks
    
    # Child 청크 생성 (Parent를 max_tokens 기준으로 분할)
    def split_parent_into_children(self, parent_content: str) -> List[str]:

        token_count = self.count_tokens(parent_content)
        
        if token_count <= self.max_tokens:
            return [parent_content]
        
        # 문단 단위로 분할 (빈 줄 기준)
        paragraphs = parent_content.split('\n\n')
        
        child_chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # 단일 문단이 max_tokens를 초과하는 경우
            if para_tokens > self.max_tokens:
                # 현재까지 모은 청크 저장
                if current_chunk:
                    child_chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # 큰 문단을 줄 단위로 분할
                lines = para.split('\n')
                temp_chunk = []
                temp_tokens = 0
                
                for line in lines:
                    line_tokens = self.count_tokens(line)
                    if temp_tokens + line_tokens > self.max_tokens:
                        if temp_chunk:
                            child_chunks.append('\n'.join(temp_chunk))
                        temp_chunk = [line]
                        temp_tokens = line_tokens
                    else:
                        temp_chunk.append(line)
                        temp_tokens += line_tokens
                
                if temp_chunk:
                    child_chunks.append('\n'.join(temp_chunk))
            
            # 현재 청크에 추가 가능한 경우
            elif current_tokens + para_tokens <= self.max_tokens:
                current_chunk.append(para)
                current_tokens += para_tokens
            
            # 새로운 청크 시작
            else:
                if current_chunk:
                    child_chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
        
        # 마지막 청크 추가
        if current_chunk:
            child_chunks.append('\n\n'.join(current_chunk))
        
        return child_chunks
    
    # PDF 파일을 Parent-Child 청크로 분할
    def process_file(self, filepath: Path, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:

        # PDF 텍스트 추출 및 정제
        content = self.extract_text_from_pdf(filepath)
        content = self.clean_pdf_text(content)
        
        # Parent 청크 생성
        parent_chunks = self.split_into_parents(content)
        
        # 청크가 없으면 전체 파일을 하나의 Parent로
        if not parent_chunks:
            parent_chunks = [content]
        
        # Parent-Child 구조 생성
        result = []
        for parent_idx, parent_text in enumerate(parent_chunks, start=1):
            # Child 청크 생성
            child_chunks = self.split_parent_into_children(parent_text)
            
            # Parent와 Children을 딕셔너리로 저장
            result.append({
                'parent_idx': parent_idx,
                'parent_text': parent_text,
                'children': child_chunks
            })
        
        return result
    
    # Parent-Child 청크 객체 생성
    def create_chunk_objects(self, parent_child_data: List[Dict[str, Any]], metadata: Dict[str, Any], base_id: str) -> List[Dict[str, Any]]:

        chunk_objects = [] # 청크 객체를 저장할 리스트
        total_parents = len(parent_child_data)
        
        # Parent-Child 구조를 순회하면서 청크 객체 생성
        for parent_data in parent_child_data:
            parent_idx = parent_data['parent_idx']
            parent_text = parent_data['parent_text']
            children = parent_data['children']
            
            # Parent ID 생성
            parent_id = f"{base_id}_p{parent_idx:03d}"
            
            # Parent 청크 객체 생성
            parent_obj = {
                "id": parent_id,
                "text": parent_text.strip(),
                "metadata": {
                    **metadata,
                    "chunk_type": "parent",
                    "parent_index": parent_idx,
                    "total_parents": total_parents,
                    "has_children": True,
                    "num_children": len(children)
                }
            }
            chunk_objects.append(parent_obj)
            
            # Child 청크 객체 생성
            for child_idx, child_text in enumerate(children, start=1):
                child_id = f"{base_id}_p{parent_idx:03d}_c{child_idx:03d}"
                
                child_obj = {
                    "id": child_id,
                    "text": child_text.strip(),
                    "metadata": {
                        **metadata,
                        "chunk_type": "child",
                        "parent_id": parent_id,
                        "parent_index": parent_idx,
                        "child_index": child_idx,
                        "total_children": len(children)
                    }
                }
                chunk_objects.append(child_obj)
        
        return chunk_objects
    
    # 단일 파일을 처리하여 개별 json 파일로 저장
    def process_single_file(self, filepath: Path, output_dir: Path) -> int:
        
        # 메타데이터 추출
        metadata = self.extract_metadata_from_filename(filepath.name)
        
        # 파일을 Parent-Child 구조로 청크 분할
        parent_child_data = self.process_file(filepath, metadata)
        
        # 베이스 ID 생성 (파일명에서 확장자 제거)
        base_id = filepath.stem  # 예: "adler_theory_1"
        
        # 청크 객체 생성
        chunk_objects = self.create_chunk_objects(parent_child_data, metadata, base_id)
        
        # 개별 JSON 파일로 저장
        output_filename = f"{filepath.stem}_chunks.json"
        output_path = output_dir / output_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_objects, f, ensure_ascii=False, indent=2)

        return len(chunk_objects)
    
    # 디렉토리 내 모든 파일 처리
    # 한개의 파일로 할건지 개별 파일로 할건지 선택
    def process_directory(self, input_dir: Path, output_dir: Path, 
                         file_pattern: str = "*.pdf", save_individually: bool = False):

        # 출력 디렉토리 생성
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 가져오기
        files = sorted(input_dir.glob(file_pattern))
        
        # 파일이 없으면 빈 리스트 리턴
        if len(files) == 0:
            return []
        
        # 개별 파일로 저장하는 경우
        if save_individually:
            # 개별 파일로 저장
            total_chunks = 0
            for file in files:
                chunk_count = self.process_single_file(file, output_dir) # 단일 파일 처리
                total_chunks += chunk_count # 청크 개수 추가

            return total_chunks
        else:
            # 단일 파일로 저장 (기존 방식)
            all_chunk_objects = []
            current_id = 1
            
            for file in files:
                
                # 메타데이터 추출
                metadata = self.extract_metadata_from_filename(file.name)
                
                # 파일을 Parent-Child 구조로 청크 분할
                parent_child_data = self.process_file(file, metadata)
                
                # 청크 객체 생성
                base_id = f"adler_{current_id:03d}"
                chunk_objects = self.create_chunk_objects(parent_child_data, metadata, base_id)
                all_chunk_objects.extend(chunk_objects)
                
                current_id += len(chunk_objects)
            
            # JSON 파일로 저장
            output_filename = "chunks_combined.json"
            output_path = output_dir / output_filename
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_chunk_objects, f, ensure_ascii=False, indent=2)
            
            return all_chunk_objects

# ==================== Adler 관련 main 함수 ====================

def main():

    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent
    adler_base_dir = base_dir / "dataset" / "adler"
    output_dir = adler_base_dir / "chunkfiles"
    
    # 청크 생성기 초기화 (Parent-Child Chunking)
    creator = ChunkCreator(max_tokens=500, parent_max_tokens=1000, overlap_ratio=0.1)
    
    # 5개 카테고리 디렉토리
    categories = ["case", "theory", "interventions", "qna", "tone"]
    
    total_files = 0
    total_chunks = 0
    
    for category in categories:
        input_dir = adler_base_dir / category
        
        # input 파일 경로가 존재하지 않으면 건너뛰기
        if not input_dir.exists():
            continue
        
        # PDF 파일 처리 (개별 저장)
        chunk_count = creator.process_directory(
            input_dir=input_dir,
            output_dir=output_dir,
            file_pattern="*.pdf",
            save_individually=True
        )
        
        # 파일 개수 세기
        pdf_files = list(input_dir.glob("*.pdf"))
        total_files += len(pdf_files)
        total_chunks += chunk_count if isinstance(chunk_count, int) else 0

if __name__ == "__main__":
    main() # 실행