"""
Insurance RAG CLI 인터페이스

단일 명령어로 전체 파이프라인 실행:
  # 방법 1: __main__.py 사용 (권장)
  python -m app.domain.rag.Insurance process internal_insurance/uploads
  python -m app.domain.rag.Insurance query "상해요인 정의"
  
  # 방법 2: cli.py 직접 실행
  python -m app.domain.rag.Insurance.cli process internal_insurance/uploads
  python -m app.domain.rag.Insurance.cli query "상해요인 정의"
  
  # 방법 3: 절대 경로 사용
  python -m app.domain.rag.Insurance process app/domain/rag/Insurance/internal_insurance/uploads
"""

import sys
from pathlib import Path
import argparse

from .config import insurance_config
from .extractor.extract_pdf import extract_pdf
from .chunker import chunk_json
from .embedder import embed_chunks
from .vector_store import VectorStore
from .retriever import InsuranceRetriever
from .schemas import QueryRequest
from .utils import get_logger
from .performance import get_performance_monitor

logger = get_logger(__name__)


def main():
    """Insurance RAG CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description="Insurance RAG 파이프라인 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # PDF 처리 (Extract → Chunk → Embed)
  python -m app.domain.rag.Insurance.cli process app/domain/rag/Insurance/internal_insurance/uploads
  python -m app.domain.rag.Insurance.cli process app/domain/rag/Insurance/internal_insurance/uploads/file.pdf
  
  # 질의응답
  python -m app.domain.rag.Insurance.cli query "상해요인 정의"
  python -m app.domain.rag.Insurance.cli query  # 대화형 모드
  
  # 통계
  python -m app.domain.rag.Insurance.cli stats
  
  # 컬렉션 초기화
  python -m app.domain.rag.Insurance.cli reset
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")
    
    # process 명령어
    process_parser = subparsers.add_parser("process", help="PDF 파일 처리 (Extract → Chunk → Embed)")
    process_parser.add_argument("input_path", help="PDF 파일 또는 디렉토리 경로")
    
    # upload 명령어 (process의 별칭)
    upload_parser = subparsers.add_parser("upload", help="PDF 파일 업로드 및 처리 (process와 동일)")
    upload_parser.add_argument("input_path", help="PDF 파일 또는 디렉토리 경로")
    
    # query 명령어
    query_parser = subparsers.add_parser("query", help="질의응답")
    query_parser.add_argument("question", nargs="?", help="질문 (없으면 대화형 모드)")
    query_parser.add_argument("--top-k", type=int, help="반환할 최대 결과 수")
    
    # stats 명령어
    subparsers.add_parser("stats", help="Insurance RAG 시스템 통계")
    
    # reset 명령어
    subparsers.add_parser("reset", help="Insurance 벡터 저장소 초기화")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 명령어 실행
    if args.command == "process":
        process_command(args.input_path)
    elif args.command == "upload":
        # upload는 process의 별칭
        process_command(args.input_path)
    elif args.command == "query":
        query_command(args.question, args.top_k)
    elif args.command == "stats":
        stats_command()
    elif args.command == "reset":
        reset_command()
    else:
        parser.print_help()
        sys.exit(1)


def process_command(input_path: str):
    """PDF 처리 명령어 (Extract → Chunk → Embed)"""
    input_path = Path(input_path)
    
    # 경로 자동 보정: internal_docs → internal_insurance
    if "internal_docs" in str(input_path):
        corrected_path = str(input_path).replace("internal_docs", "internal_insurance")
        print(f"⚠️  경로 자동 보정: {input_path} → {corrected_path}")
        logger.info(f"경로 자동 보정: {input_path} → {corrected_path}")
        input_path = Path(corrected_path)
    
    # 상대 경로인 경우 Insurance 모듈 기준으로 변환
    if not input_path.is_absolute():
        # internal_insurance로 시작하는 경우 Insurance 폴더 기준으로 변환
        if str(input_path).startswith("internal_insurance"):
            insurance_dir = Path(__file__).parent
            input_path = insurance_dir / input_path
    
    if not input_path.exists():
        print(f"❌ 오류: 경로를 찾을 수 없습니다: {input_path}")
        print(f"💡 팁: Insurance RAG는 'app/domain/rag/Insurance/internal_insurance/uploads' 디렉토리를 사용합니다.")
        logger.error(f"경로를 찾을 수 없습니다: {input_path}")
        sys.exit(1)
    
    # PDF 파일 목록 수집
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            print(f"❌ 오류: PDF 파일이 아닙니다: {input_path}")
            logger.error(f"PDF 파일이 아닙니다: {input_path}")
            sys.exit(1)
        pdf_files = [input_path]
    else:
        pdf_files = [p for p in input_path.iterdir() if p.suffix.lower() == ".pdf"]
    
    if not pdf_files:
        print(f"❌ 오류: PDF 파일을 찾을 수 없습니다: {input_path}")
        logger.error(f"PDF 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)
    
    logger.info(f"처리할 PDF 파일: {len(pdf_files)}개")
    print(f"📄 처리할 PDF 파일: {len(pdf_files)}개\n")
    
    # 각 PDF 파일 처리
    success_count = 0
    fail_count = 0
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        try:
            print(f"{'='*60}")
            print(f"[{idx}/{len(pdf_files)}] Processing: {pdf_path.name}")
            print(f"{'='*60}")
            
            # 1) Extract
            logger.info(f"1단계: PDF 추출 시작 - {pdf_path.name}")
            print("1️⃣  PDF 추출 중...")
            json_path = extract_pdf(str(pdf_path))
            logger.info(f"추출 완료: {json_path}")
            print(f"   ✓ 추출 완료: {json_path.name}")
            
            # 2) Chunk
            logger.info(f"2단계: 청킹 시작 - {json_path.name}")
            print("2️⃣  청킹 중...")
            chunk_path = chunk_json(json_path)
            logger.info(f"청킹 완료: {chunk_path}")
            print(f"   ✓ 청킹 완료: {chunk_path.name}")
            
            # 3) Embed
            logger.info(f"3단계: 임베딩 시작 - {chunk_path.name}")
            print("3️⃣  임베딩 중...")
            embed_chunks(chunk_path)
            logger.info(f"임베딩 완료")
            print(f"   ✓ 임베딩 완료 (ChromaDB 저장됨)")
            
            success_count += 1
            print(f"✅ {pdf_path.name} 처리 완료!\n")
            
        except Exception as e:
            fail_count += 1
            logger.exception(f"{pdf_path.name} 처리 중 오류 발생: {e}")
            print(f"❌ 오류 발생: {pdf_path.name}", file=sys.stderr)
            print(f"   {str(e)}", file=sys.stderr)
            print()
            continue
    
    # 최종 결과
    print(f"{'='*60}")
    print(f"📊 처리 결과: 성공 {success_count}개 / 실패 {fail_count}개")
    print(f"{'='*60}")
    
    if success_count > 0:
        print(f"✅ 전체 파이프라인 완료!")
        logger.info(f"파이프라인 완료: 성공 {success_count}개 / 실패 {fail_count}개")
        
        # 성능 리포트 출력
        monitor = get_performance_monitor()
        monitor.report()
    
    if fail_count > 0:
        sys.exit(1)


def query_command(question: str = None, top_k: int = None):
    """질의응답 명령어"""
    retriever = InsuranceRetriever()
    
    if question:
        # 단일 질문
        request = QueryRequest(query=question, top_k=top_k or insurance_config.RAG_TOP_K)
        response = retriever.query(request)
        
        print(f"\n{'='*60}")
        print(f"질문: {question}")
        print(f"{'='*60}")
        print(f"\n답변:\n{response.answer}\n")
        
        if response.retrieved_chunks:
            print(f"참고 문서 ({len(response.retrieved_chunks)}개):")
            for i, chunk in enumerate(response.retrieved_chunks, 1):
                filename = chunk.metadata.get('filename', chunk.metadata.get('source', 'Unknown'))
                page_num = chunk.metadata.get('page_number', chunk.metadata.get('page', '?'))
                print(f"  {i}. {filename} (페이지: {page_num}, 유사도: {chunk.score:.4f})")
        else:
            print("⚠️  검색된 문서가 없습니다.")
        
        print(f"\n처리 시간: {response.processing_time:.2f}초")
        print(f"{'='*60}\n")
    else:
        # 대화형 모드
        print("=" * 60)
        print("Insurance RAG 질의응답 (대화형 모드)")
        print("종료하려면 'exit' 또는 'quit'를 입력하세요")
        print("=" * 60)
        
        while True:
            try:
                question = input("\n질문> ").strip()
                if question.lower() in ['exit', 'quit', '종료']:
                    break
                
                if not question:
                    continue
                
                request = QueryRequest(query=question, top_k=top_k or insurance_config.RAG_TOP_K)
                response = retriever.query(request)
                
                print(f"\n답변:\n{response.answer}\n")
                
                if response.retrieved_chunks:
                    print(f"참고 문서 ({len(response.retrieved_chunks)}개):")
                    for i, chunk in enumerate(response.retrieved_chunks, 1):
                        filename = chunk.metadata.get('filename', chunk.metadata.get('source', 'Unknown'))
                        page_num = chunk.metadata.get('page_number', chunk.metadata.get('page', '?'))
                        print(f"  {i}. {filename} (페이지: {page_num}, 유사도: {chunk.score:.4f})")
                
            except KeyboardInterrupt:
                print("\n\n종료합니다.")
                break
            except Exception as e:
                logger.exception(f"질의응답 중 오류: {e}")
                print(f"❌ 오류 발생: {e}")


def stats_command():
    """통계 명령어"""
    vector_store = VectorStore()
    count = vector_store.count_documents()
    
    print("=" * 60)
    print("Insurance RAG 시스템 통계")
    print("=" * 60)
    print(f"저장된 총 청크 수: {count}")
    print(f"컬렉션 이름: {insurance_config.CHROMA_COLLECTION_NAME}")
    print(f"임베딩 모델: {insurance_config.EMBEDDING_MODEL}")
    print(f"번역 모델: {insurance_config.TRANSLATION_MODEL}")
    print(f"LLM 모델: {insurance_config.OPENAI_MODEL}")
    print(f"Top-K: {insurance_config.RAG_TOP_K}")
    print(f"Threshold 범위: {insurance_config.RAG_MIN_SIMILARITY_THRESHOLD} ~ {insurance_config.RAG_MAX_SIMILARITY_THRESHOLD}")
    print(f"청크 크기: {insurance_config.RAG_CHUNK_SIZE}")
    print(f"청크 오버랩: {insurance_config.RAG_CHUNK_OVERLAP}")
    print(f"처리된 파일 디렉토리: {insurance_config.PROCESSED_DIR}")
    print("=" * 60)


def reset_command():
    """컬렉션 초기화 명령어"""
    confirm = input("⚠️  Insurance 컬렉션을 초기화하시겠습니까? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    try:
        vector_store = VectorStore()
        vector_store.reset_collection()
        print("✅ Insurance 컬렉션 초기화 완료!")
        logger.info("Insurance 컬렉션 초기화 완료")
    except Exception as e:
        logger.exception(f"컬렉션 초기화 중 오류: {e}")
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
