"""
일일 보고서 자동 Ingestion 파이프라인

backend/Data/mock_reports/ 아래 모든 txt 파일을 재귀적으로 스캔하여
각 txt 파일의 여러 JSON 객체를 파싱 → normalize → chunk → embed → Chroma 저장

사용법:
    python -m ingestion.ingest_daily_reports
    
    또는 OpenAI API 키를 명시적으로 전달:
    python -m ingestion.ingest_daily_reports --api-key YOUR_API_KEY
"""
import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드됨: {env_path}")
    else:
        print(f"⚠️  .env 파일이 없습니다: {env_path}")
except ImportError:
    print("⚠️  python-dotenv가 설치되지 않았습니다. pip install python-dotenv를 실행하세요.")
except Exception as e:
    print(f"⚠️  .env 파일 로드 오류: {e}")

from app.domain.report.service import ReportProcessingService
from app.domain.report.chunker import chunk_report, get_chunk_statistics
from ingestion.embed import embed_texts
from ingestion.chroma_client import get_chroma_service


# ========================================
# 설정
# ========================================
DATA_DIR = project_root / "Data" / "mock_reports"
COLLECTION_NAME = "daily_reports"
BATCH_SIZE = 100


# ========================================
# JSON 파싱 함수
# ========================================
def parse_multi_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    txt 파일에서 여러 개의 JSON 객체를 파싱
    
    각 JSON 객체는 줄바꿈으로만 구분되어 있음 (배열이 아님)
    
    Args:
        file_path: txt 파일 경로
        
    Returns:
        파싱된 JSON 객체 리스트
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 방법 1: 정규식으로 JSON 객체 블록 추출
    # {로 시작하고 }로 끝나는 패턴을 찾음
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    json_strings = re.findall(json_pattern, content, re.DOTALL)
    
    parsed_objects = []
    
    for idx, json_str in enumerate(json_strings):
        try:
            obj = json.loads(json_str)
            parsed_objects.append(obj)
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 파싱 오류 (인덱스 {idx}): {e}")
            # 실패한 JSON은 건너뛰기
            continue
    
    return parsed_objects


def parse_month_folder(month_str: str) -> tuple:
    """
    월 폴더 이름을 파싱하여 (year, month) 튜플 반환
    
    예: "2024년 11월" -> (2024, 11)
        "2025년 1월" -> (2025, 1)
    """
    try:
        # "2024년 11월" 형식 파싱
        parts = month_str.replace("년", "").replace("월", "").strip().split()
        if len(parts) >= 2:
            year = int(parts[0])
            month = int(parts[1])
            return (year, month)
    except:
        pass
    return (0, 0)


def parse_file_date(file_name: str, month_folder: str = "") -> str:
    """
    파일 이름에서 시작 날짜 추출
    
    예: "2024-11-01 ~ 2024-11-05.txt" -> "2024-11-01"
        "2025년 12월 1일 ~ 12월 5일.txt" (month_folder="2025년 12월") -> "2025-12-01"
    """
    # "2024-11-01 ~ 2024-11-05.txt" 형식
    if " ~ " in file_name:
        date_part = file_name.split(" ~ ")[0].strip()
        # .txt 제거
        date_part = date_part.replace(".txt", "").strip()
        # YYYY-MM-DD 형식인지 확인
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_part):
            return date_part
        
        # "2025년 12월 1일" 형식 파싱
        # 폴더에서 연도와 월 추출
        if month_folder:
            year_month = parse_month_folder(month_folder)
            if year_month[0] > 0 and year_month[1] > 0:
                # "1일", "12일" 등에서 일 추출
                day_match = re.search(r'(\d+)일', date_part)
                if day_match:
                    day = int(day_match.group(1))
                    return f"{year_month[0]:04d}-{year_month[1]:02d}-{day:02d}"
    
    return ""


def scan_mock_reports(base_dir: Path) -> List[Dict[str, Any]]:
    """
    mock_reports 폴더의 모든 txt 파일을 재귀적으로 스캔하고 날짜 순으로 정렬
    
    Args:
        base_dir: mock_reports 폴더 경로
        
    Returns:
        파일 정보 리스트 (날짜 순으로 정렬됨)
        [
            {
                "file_path": Path(...),
                "relative_path": "2024년 11월/2024-11-01 ~ 2024-11-05.txt",
                "month": "2024년 11월"
            },
            ...
        ]
    """
    if not base_dir.exists():
        print(f"❌ 경로가 존재하지 않습니다: {base_dir}")
        return []
    
    file_infos = []
    
    # 모든 txt 파일 찾기
    for txt_file in base_dir.rglob("*.txt"):
        # 상대 경로 계산
        relative_path = txt_file.relative_to(base_dir)
        
        # 월 폴더 이름 추출 (첫 번째 부모 폴더)
        month = relative_path.parts[0] if len(relative_path.parts) > 1 else ""
        file_name = relative_path.parts[-1] if len(relative_path.parts) > 0 else ""
        
        # 정렬을 위한 키 생성
        year_month = parse_month_folder(month)
        file_date = parse_file_date(file_name, month)
        
        # 정렬 키: (year, month, file_date, relative_path)
        # file_date가 없으면 파일 이름으로 정렬
        sort_key = (
            year_month[0],  # year
            year_month[1],  # month
            file_date if file_date else file_name,  # date or filename
            str(relative_path)  # fallback to path
        )
        
        file_infos.append({
            "file_path": txt_file,
            "relative_path": str(relative_path),
            "month": month,
            "sort_key": sort_key
        })
    
    # 날짜 순으로 정렬
    file_infos.sort(key=lambda x: x["sort_key"])
    
    # sort_key 제거 (반환값에는 필요 없음)
    for info in file_infos:
        del info["sort_key"]
    
    return file_infos


# ========================================
# 메인 파이프라인
# ========================================
def ingest_daily_reports_pipeline(api_key: str = None, dry_run: bool = False):
    """
    일일 보고서 전체 Ingestion 파이프라인
    
    Args:
        api_key: OpenAI API 키
        dry_run: True면 Chroma 업로드 없이 통계만 출력
    """
    print("=" * 80)
    print("📊 일일 보고서 Ingestion 파이프라인 시작")
    print("=" * 80)
    print()
    
    # 1. 파일 스캔
    print("⏳ mock_reports 폴더 스캔 중...")
    file_infos = scan_mock_reports(DATA_DIR)
    
    if not file_infos:
        print("❌ txt 파일을 찾을 수 없습니다.")
        return
    
    print(f"✅ 총 {len(file_infos)}개 txt 파일 발견 (날짜 순으로 정렬됨)")
    print()
    
    # 스캔된 파일 목록 출력 (처음 5개, 마지막 5개)
    if len(file_infos) > 0:
        print("📋 스캔된 파일 목록 (처음 5개):")
        for i, file_info in enumerate(file_infos[:5]):
            print(f"   {i+1}. {file_info['relative_path']}")
        if len(file_infos) > 10:
            print("   ...")
            print("📋 스캔된 파일 목록 (마지막 5개):")
            for i, file_info in enumerate(file_infos[-5:], start=len(file_infos)-4):
                print(f"   {i}. {file_info['relative_path']}")
        print()
    
    # 2. ReportProcessingService 초기화 (dry-run에서는 API 키 없이 생성)
    # normalize 함수만 사용하므로 OpenAI 클라이언트는 필요 없음
    if dry_run:
        # API 키 없이 생성 (normalize만 사용)
        service = ReportProcessingService.__new__(ReportProcessingService)
        # normalize 메서드들만 사용할 것이므로 client는 None으로 설정
        service.client = None
    else:
        service = ReportProcessingService(api_key=api_key)
    
    # 3. 전체 청크 리스트 (모든 파일의 청크를 모음)
    all_chunks = []
    stats = {
        "total_files": len(file_infos),
        "total_reports": 0,
        "total_chunks": 0,
        "errors": []
    }
    
    # 4. 각 txt 파일 처리
    current_folder = None
    for idx, file_info in enumerate(file_infos):
        file_path = file_info["file_path"]
        relative_path = file_info["relative_path"]
        month = file_info["month"]
        
        # 폴더가 변경되면 로그 출력
        if month != current_folder:
            current_folder = month
            print("=" * 80)
            print(f"📂 Processing folder: {month}")
            print("=" * 80)
        
        print("-" * 80)
        print(f"📄 Processing file [{idx + 1}/{len(file_infos)}]: {relative_path}")
        print(f"   Folder: {month}")
        print("-" * 80)
        
        try:
            # 4-1. JSON 객체들 파싱
            print("⏳ JSON 파싱 중...")
            json_objects = parse_multi_json_file(file_path)
            
            if not json_objects:
                print(f"⚠️  파싱된 JSON 객체가 없습니다. 건너뜁니다.")
                stats["errors"].append({
                    "file": relative_path,
                    "error": "No JSON objects parsed"
                })
                continue
            
            print(f"✅ {len(json_objects)}개 JSON 객체 파싱 완료")
            stats["total_reports"] += len(json_objects)
            
            # 4-2. 각 JSON 객체를 Canonical로 변환 + 청킹
            for json_idx, raw_json in enumerate(json_objects):
                try:
                    # Normalize (Raw JSON → CanonicalReport)
                    canonical = service.normalize_daily(raw_json)
                    
                    # 날짜 정보 추출 (메타데이터용)
                    date_str = canonical.period_start.isoformat() if canonical.period_start else ""
                    month_str = canonical.period_start.strftime("%Y-%m") if canonical.period_start else ""
                    
                    # Chunking
                    chunks = chunk_report(canonical, include_summary=True)
                    
                    # 각 청크에 추가 메타데이터 추가
                    for chunk in chunks:
                        # 청크 딕셔너리 키 이름 변경 (text → chunk_text)
                        chunk["chunk_text"] = chunk.pop("text")
                        
                        # 추가 메타데이터
                        chunk["metadata"]["date"] = date_str
                        chunk["metadata"]["month"] = month_str
                        chunk["metadata"]["source_file"] = relative_path
                        chunk["metadata"]["task_count"] = len(canonical.tasks)
                        chunk["metadata"]["issue_count"] = len(canonical.issues)
                        chunk["metadata"]["plan_count"] = len(canonical.plans)
                    
                    all_chunks.extend(chunks)
                    print(f"  ✅ 보고서 {json_idx + 1}: {len(chunks)}개 청크 생성 (작성일: {date_str}, 작성자: {canonical.owner})")
                
                except Exception as e:
                    print(f"  ❌ 보고서 {json_idx + 1} 처리 오류: {e}")
                    stats["errors"].append({
                        "file": relative_path,
                        "json_index": json_idx,
                        "error": str(e)
                    })
        
        except Exception as e:
            print(f"❌ 파일 처리 오류: {e}")
            stats["errors"].append({
                "file": relative_path,
                "error": str(e)
            })
    
    stats["total_chunks"] = len(all_chunks)
    
    print()
    print("=" * 80)
    print("📊 파싱 및 청킹 통계")
    print("=" * 80)
    print(f"총 파일 수: {stats['total_files']}")
    print(f"총 보고서 수: {stats['total_reports']}")
    print(f"총 청크 수: {stats['total_chunks']}")
    print(f"오류 수: {len(stats['errors'])}")
    print()
    
    if stats["errors"]:
        print("⚠️  오류 목록:")
        for error in stats["errors"][:10]:  # 최대 10개만 표시
            print(f"  - {error}")
        if len(stats["errors"]) > 10:
            print(f"  ... 외 {len(stats['errors']) - 10}건")
        print()
    
    if not all_chunks:
        print("❌ 생성된 청크가 없습니다. 종료합니다.")
        return
    
    # 청크 통계
    chunk_stats = get_chunk_statistics(all_chunks)
    print("📊 청크 통계:")
    print(f"  - 총 청크 수: {chunk_stats['total_chunks']}")
    print(f"  - 청크 타입별:")
    for chunk_type, count in chunk_stats["chunk_types"].items():
        print(f"    • {chunk_type}: {count}")
    print(f"  - 평균 텍스트 길이: {chunk_stats['avg_text_length']:.1f}자")
    print(f"  - 최대 텍스트 길이: {chunk_stats['max_text_length']}자")
    print(f"  - 최소 텍스트 길이: {chunk_stats['min_text_length']}자")
    print()
    
    if dry_run:
        print("🔍 Dry-run 모드: Chroma 업로드를 건너뜁니다.")
        return
    
    # 5. 임베딩 생성
    print("=" * 80)
    print("⏳ 임베딩 생성 중...")
    print("=" * 80)
    
    ids = [chunk["id"] for chunk in all_chunks]
    texts = [chunk["chunk_text"] for chunk in all_chunks]
    metadatas = [chunk["metadata"] for chunk in all_chunks]
    
    try:
        embeddings = embed_texts(texts, api_key=api_key, batch_size=BATCH_SIZE)
        print(f"✅ {len(embeddings)}개 임베딩 생성 완료")
        print()
    except Exception as e:
        print(f"❌ 임베딩 생성 오류: {e}")
        return
    
    # 6. Chroma Cloud 업로드
    print("=" * 80)
    print("⏳ Chroma Cloud 업로드 중...")
    print("=" * 80)
    
    try:
        # Chroma 클라이언트 가져오기
        chroma_service = get_chroma_service()
        collection = chroma_service.get_or_create_collection(name=COLLECTION_NAME)
        
        print(f"✅ 컬렉션 '{COLLECTION_NAME}' 연결 완료")
        print(f"📦 현재 문서 수: {collection.count()}개")
        print()
        
        # 배치 업로드
        total = len(all_chunks)
        
        for i in range(0, total, BATCH_SIZE):
            batch_end = min(i + BATCH_SIZE, total)
            
            batch_ids = ids[i:batch_end]
            batch_embeddings = embeddings[i:batch_end]
            batch_documents = texts[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            
            print(f"  ⏳ 업로드 중... ({i + 1}-{batch_end}/{total})")
            
            try:
                collection.upsert(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
            except Exception as e:
                print(f"  ❌ 배치 업로드 오류 ({i}-{batch_end}): {e}")
                return
        
        print()
        print("=" * 80)
        print("✅ Ingestion 완료!")
        print("=" * 80)
        print(f"컬렉션: {COLLECTION_NAME}")
        print(f"업로드된 청크: {total}개")
        print(f"컬렉션 총 문서 수: {collection.count()}개")
        print()
        
    except Exception as e:
        print(f"❌ Chroma Cloud 업로드 오류: {e}")
        return


# ========================================
# CLI 진입점
# ========================================
def main():
    """CLI 진입점"""
    parser = argparse.ArgumentParser(
        description="일일 보고서 자동 Ingestion 파이프라인"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API 키 (기본값: 환경변수 OPENAI_API_KEY)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run 모드 (Chroma 업로드 없이 통계만 출력)"
    )
    
    args = parser.parse_args()
    
    # API 키 확인
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key and not args.dry_run:
        print("❌ OpenAI API 키가 필요합니다.")
        print("   --api-key 옵션을 사용하거나 환경변수 OPENAI_API_KEY를 설정하세요.")
        sys.exit(1)
    
    # 파이프라인 실행
    ingest_daily_reports_pipeline(api_key=api_key, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

