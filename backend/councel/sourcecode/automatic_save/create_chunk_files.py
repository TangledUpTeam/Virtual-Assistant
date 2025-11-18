"""
청크 파일 생성 스크립트
생성날짜: 2025.11.18
설명: rogers/original 폴더의 모든 파일을 의미 단위로 청킹하여 JSON 배열 형태로 저장
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import tiktoken


class ChunkCreator:

    # 초기화
    def __init__(self, max_tokens: int = 500, overlap_ratio: float = 0.1):
        self.max_tokens = max_tokens # 청크당 최대 토큰 수
        self.overlap_ratio = overlap_ratio # Overlap 비율
        self.encoding = tiktoken.get_encoding("cl100k_base") # 토큰 인코딩 모델

    # 텍스트의 토큰 수 계산   
    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))
    
    # 파일명에서 메타데이터 추출
    def extract_metadata_from_filename(self, filename: str) -> Dict[str, Any]:

        # 파일당 메타데이터 추출 예시
        # rogers_theory_1.md -> type: theory
        # rogers_example_1.md -> type: example
        # rogers_information_1.md -> type: information
        # rogers_techniques_1.md -> type: techniques
        
        parts = filename.replace('.md', '').split('_')
        file_type = parts[1] if len(parts) > 1 else "unknown"
        
        metadata = {
            "psychologist": "Carl Rogers",
            "source": filename,
            "type": file_type,
            "topic": "client-centered therapy",
            "tags": ["상담", "인간중심"]
        }
        
        # 타입별 추가 태그
        if file_type == "theory":
            metadata["tags"].extend(["이론", "개념"])
        elif file_type == "example":
            metadata["tags"].extend(["사례", "예시"])
        elif file_type == "information":
            metadata["tags"].extend(["정보", "배경"])
        elif file_type == "techniques":
            metadata["tags"].extend(["기법", "실습"])
            
        return metadata
    
    def split_by_sections(self, content: str) -> List[Tuple[str, str]]:
        """
        마크다운 파일을 의미 단위(섹션)로 분할
        Returns: List of (section_title, section_content)
        """
        lines = content.split('\n')
        sections = []
        current_title = ""
        current_content = []
        
        # 최상위 제목 패턴 (# Title)
        main_title_pattern = r'^# .+'
        # 섹션 제목 패턴 (## 1. 또는 ## Title)
        section_pattern = r'^## (?:\d+\.\s*)?(.+)'
        
        for line in lines:
            # 최상위 제목
            if re.match(main_title_pattern, line):
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))
                current_title = line
                current_content = [line]
            # 섹션 제목 (## 로 시작)
            elif re.match(section_pattern, line):
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))
                current_title = line
                current_content = [line]
            else:
                current_content.append(line)
        
        # 마지막 섹션 추가
        if current_content:
            sections.append((current_title, '\n'.join(current_content)))
        
        return sections
    
    def add_overlap(self, chunks: List[str]) -> List[str]:
        """청크 간 10% overlap 추가"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                # 첫 번째 청크는 그대로
                overlapped_chunks.append(chunk)
            else:
                # 이전 청크의 마지막 10% 가져오기
                prev_chunk = chunks[i-1]
                prev_tokens = self.encoding.encode(prev_chunk)
                overlap_size = int(len(prev_tokens) * self.overlap_ratio)
                
                if overlap_size > 0:
                    overlap_tokens = prev_tokens[-overlap_size:]
                    overlap_text = self.encoding.decode(overlap_tokens)
                    
                    # 현재 청크에 overlap 추가
                    overlapped_chunks.append(overlap_text + "\n\n" + chunk)
                else:
                    overlapped_chunks.append(chunk)
        
        return overlapped_chunks
    
    def split_large_section(self, section_content: str) -> List[str]:
        """
        큰 섹션을 토큰 제한에 맞춰 분할
        문단 단위로 분할하여 의미를 유지
        """
        token_count = self.count_tokens(section_content)
        
        if token_count <= self.max_tokens:
            return [section_content]
        
        # 문단 단위로 분할 (빈 줄 기준)
        paragraphs = section_content.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # 단일 문단이 max_tokens를 초과하는 경우
            if para_tokens > self.max_tokens:
                # 현재까지 모은 청크 저장
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
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
                            chunks.append('\n'.join(temp_chunk))
                        temp_chunk = [line]
                        temp_tokens = line_tokens
                    else:
                        temp_chunk.append(line)
                        temp_tokens += line_tokens
                
                if temp_chunk:
                    chunks.append('\n'.join(temp_chunk))
            
            # 현재 청크에 추가 가능한 경우
            elif current_tokens + para_tokens <= self.max_tokens:
                current_chunk.append(para)
                current_tokens += para_tokens
            
            # 새로운 청크 시작
            else:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def process_file(self, filepath: Path, metadata: Dict[str, Any]) -> List[str]:
        """
        파일을 의미 단위로 청크 분할
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 섹션별로 분할
        sections = self.split_by_sections(content)
        
        all_chunks = []
        
        for section_title, section_content in sections:
            # 빈 섹션 건너뛰기
            if not section_content.strip():
                continue
            
            # 섹션이 토큰 제한을 초과하면 분할
            section_chunks = self.split_large_section(section_content)
            all_chunks.extend(section_chunks)
        
        # 청크가 없으면 전체 파일을 하나의 청크로
        if not all_chunks:
            all_chunks = [content]
        
        # Overlap 적용
        all_chunks = self.add_overlap(all_chunks)
        
        return all_chunks
    
    def create_chunk_objects(self, chunks: List[str], metadata: Dict[str, Any], 
                            start_id: int) -> List[Dict[str, Any]]:
        """청크 텍스트를 JSON 객체로 변환"""
        total_chunks = len(chunks)
        chunk_objects = []
        
        for idx, chunk_text in enumerate(chunks, start=1):
            chunk_obj = {
                "id": f"rogers_{start_id + idx - 1:03d}",
                "text": chunk_text.strip(),
                "metadata": {
                    **metadata,
                    "chunk_index": idx,
                    "total_chunks": total_chunks
                }
            }
            chunk_objects.append(chunk_obj)
        
        return chunk_objects
    
    def process_directory(self, input_dir: Path, output_dir: Path, 
                         output_filename: str = "rogers_chunks_phrasing.json"):
        """디렉토리 내 모든 파일을 처리하여 청크 파일 생성"""
        # 출력 디렉토리 생성
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 모든 마크다운 파일 가져오기
        md_files = sorted(input_dir.glob("*.md"))
        
        all_chunk_objects = []
        current_id = 1
        
        print(f"총 {len(md_files)}개 파일 처리 시작...\n")
        
        for md_file in md_files:
            print(f"처리 중: {md_file.name}")
            
            # 메타데이터 추출
            metadata = self.extract_metadata_from_filename(md_file.name)
            
            # 파일을 의미 단위로 청크 분할
            chunks = self.process_file(md_file, metadata)
            
            # 청크 객체 생성
            chunk_objects = self.create_chunk_objects(chunks, metadata, current_id)
            all_chunk_objects.extend(chunk_objects)
            
            current_id += len(chunk_objects)
            
            # 각 청크의 토큰 수 출력
            for i, chunk in enumerate(chunks, start=1):
                token_count = self.count_tokens(chunk)
                print(f"  청크 {i}: {token_count} tokens")
            
            print(f"  -> 총 {len(chunk_objects)}개 청크 생성\n")
        
        # JSON 파일로 저장
        output_path = output_dir / output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_chunk_objects, f, ensure_ascii=False, indent=2)
        
        print(f"{'='*50}")
        print(f"완료! 총 {len(all_chunk_objects)}개 청크 생성")
        print(f"저장 위치: {output_path}")
        print(f"{'='*50}")
        
        # 통계 출력
        self.print_statistics(all_chunk_objects)
        
        return all_chunk_objects
    
    def print_statistics(self, chunk_objects: List[Dict[str, Any]]):
        """청크 생성 통계 출력"""
        print("\n[청크 생성 통계]")
        print(f"  - 총 청크 수: {len(chunk_objects)}")
        
        # 타입별 통계
        type_counts = {}
        for chunk in chunk_objects:
            file_type = chunk['metadata']['type']
            type_counts[file_type] = type_counts.get(file_type, 0) + 1
        
        print("\n  타입별 청크 수:")
        for file_type, count in sorted(type_counts.items()):
            print(f"    - {file_type}: {count}개")
        
        # 토큰 통계
        token_counts = [self.count_tokens(chunk['text']) for chunk in chunk_objects]
        avg_tokens = sum(token_counts) / len(token_counts)
        max_tokens = max(token_counts)
        min_tokens = min(token_counts)
        
        print(f"\n  토큰 통계:")
        print(f"    - 평균: {avg_tokens:.1f} tokens")
        print(f"    - 최대: {max_tokens} tokens")
        print(f"    - 최소: {min_tokens} tokens")


def main():
    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent
    input_dir = base_dir / "dataset" / "rogers" / "original"
    output_dir = base_dir / "dataset" / "rogers" / "chunk"
    
    # 청크 생성기 초기화
    creator = ChunkCreator(max_tokens=500, overlap_ratio=0.1)
    
    # 처리 실행
    creator.process_directory(input_dir, output_dir, "rogers_chunks_phrasing.json")


if __name__ == "__main__":
    main()

