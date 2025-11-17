"""
RAG 시스템 간단 테스트 스크립트

이 스크립트로 RAG 시스템의 각 모듈을 개별적으로 테스트할 수 있습니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel

console = Console()


def test_imports():
    """모듈 import 테스트"""
    console.print(Panel("[bold cyan]1. 모듈 Import 테스트[/bold cyan]"))
    
    try:
        from app.domain.rag.config import rag_config
        console.print("✓ config 모듈 import 성공")
        
        from app.domain.rag.schemas import (
            QueryRequest, QueryResponse, DocumentChunk
        )
        console.print("✓ schemas 모듈 import 성공")
        
        from app.domain.rag.pdf_processor import PDFProcessor
        console.print("✓ pdf_processor 모듈 import 성공")
        
        from app.domain.rag.document_converter import DocumentConverter
        console.print("✓ document_converter 모듈 import 성공")
        
        from app.domain.rag.vector_store import VectorStore
        console.print("✓ vector_store 모듈 import 성공")
        
        from app.domain.rag.retriever import RAGRetriever
        console.print("✓ retriever 모듈 import 성공")
        
        console.print("\n[green]모든 모듈 import 성공![/green]\n")
        return True
        
    except Exception as e:
        console.print(f"[red]Import 오류: {e}[/red]")
        return False


def test_config():
    """설정 테스트"""
    console.print(Panel("[bold cyan]2. 설정 테스트[/bold cyan]"))
    
    try:
        from app.domain.rag.config import rag_config
        
        console.print(f"청크 크기: {rag_config.RAG_CHUNK_SIZE}")
        console.print(f"Top-K: {rag_config.RAG_TOP_K}")
        console.print(f"임베딩 모델: {rag_config.KOREAN_EMBEDDING_MODEL}")
        console.print(f"LLM 모델: {rag_config.OPENAI_MODEL}")
        console.print(f"데이터 디렉토리: {rag_config.DATA_DIR}")
        
        # 디렉토리 존재 확인
        if rag_config.UPLOAD_DIR.exists():
            console.print(f"✓ 업로드 디렉토리 존재: {rag_config.UPLOAD_DIR}")
        else:
            console.print(f"[yellow]업로드 디렉토리 없음: {rag_config.UPLOAD_DIR}[/yellow]")
        
        if rag_config.PROCESSED_DIR.exists():
            console.print(f"✓ 처리 디렉토리 존재: {rag_config.PROCESSED_DIR}")
        else:
            console.print(f"[yellow]처리 디렉토리 없음: {rag_config.PROCESSED_DIR}[/yellow]")
        
        # OPENAI_API_KEY 확인
        if rag_config.OPENAI_API_KEY and rag_config.OPENAI_API_KEY != "":
            console.print("✓ OPENAI_API_KEY 설정됨")
        else:
            console.print("[yellow]⚠ OPENAI_API_KEY가 설정되지 않았습니다![/yellow]")
        
        console.print("\n[green]설정 테스트 완료![/green]\n")
        return True
        
    except Exception as e:
        console.print(f"[red]설정 오류: {e}[/red]")
        return False


def test_vector_store():
    """벡터 저장소 테스트"""
    console.print(Panel("[bold cyan]3. 벡터 저장소 테스트[/bold cyan]"))
    
    try:
        from app.domain.rag.vector_store import VectorStore
        
        console.print("VectorStore 초기화 중...")
        vector_store = VectorStore()
        
        # 문서 수 확인
        count = vector_store.count_documents()
        console.print(f"저장된 문서 청크: {count}개")
        
        if count > 0:
            console.print("[green]✓ 문서가 저장되어 있습니다![/green]")
            
            # 테스트 검색
            console.print("\n테스트 검색 수행...")
            results = vector_store.search("테스트", top_k=1)
            if results and results['documents'] and results['documents'][0]:
                console.print(f"✓ 검색 성공! {len(results['documents'][0])}개 결과")
            else:
                console.print("[yellow]검색 결과 없음[/yellow]")
        else:
            console.print("[yellow]저장된 문서가 없습니다. PDF를 업로드하세요.[/yellow]")
        
        console.print("\n[green]벡터 저장소 테스트 완료![/green]\n")
        return True
        
    except Exception as e:
        console.print(f"[red]벡터 저장소 오류: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return False


def test_embedding():
    """임베딩 모델 테스트"""
    console.print(Panel("[bold cyan]4. 임베딩 모델 테스트[/bold cyan]"))
    
    try:
        from app.domain.rag.vector_store import VectorStore
        
        console.print("임베딩 모델 로드 중... (첫 실행 시 시간이 걸릴 수 있습니다)")
        vector_store = VectorStore()
        
        # 테스트 텍스트 임베딩
        test_text = "안녕하세요. 이것은 테스트 텍스트입니다."
        console.print(f"테스트 텍스트: '{test_text}'")
        
        embedding = vector_store.embed_text(test_text)
        console.print(f"✓ 임베딩 생성 성공!")
        console.print(f"  - 벡터 차원: {len(embedding)}")
        console.print(f"  - 샘플 값: {embedding[:5]}")
        
        console.print("\n[green]임베딩 모델 테스트 완료![/green]\n")
        return True
        
    except Exception as e:
        console.print(f"[red]임베딩 오류: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return False


def main():
    """메인 테스트"""
    console.print("\n" + "="*60)
    console.print(Panel.fit(
        "[bold cyan]RAG 시스템 테스트[/bold cyan]",
        border_style="cyan"
    ))
    console.print("="*60 + "\n")
    
    results = []
    
    # 1. Import 테스트
    results.append(("Import", test_imports()))
    
    # 2. 설정 테스트
    results.append(("설정", test_config()))
    
    # 3. 임베딩 테스트
    results.append(("임베딩", test_embedding()))
    
    # 4. 벡터 저장소 테스트
    results.append(("벡터 저장소", test_vector_store()))
    
    # 결과 요약
    console.print("="*60)
    console.print(Panel.fit(
        "[bold cyan]테스트 결과 요약[/bold cyan]",
        border_style="cyan"
    ))
    console.print("="*60 + "\n")
    
    for name, result in results:
        status = "[green]✓ 성공[/green]" if result else "[red]✗ 실패[/red]"
        console.print(f"{name}: {status}")
    
    success_count = sum(1 for _, r in results if r)
    total_count = len(results)
    
    console.print(f"\n총 {success_count}/{total_count} 테스트 통과\n")
    
    if success_count == total_count:
        console.print(Panel.fit(
            "[bold green]모든 테스트 통과! RAG 시스템이 정상 작동합니다.[/bold green]",
            border_style="green"
        ))
        console.print("\n다음 명령어로 PDF를 업로드하고 질의응답을 시작하세요:")
        console.print("[cyan]python -m app.domain.rag.cli upload <pdf_path>[/cyan]")
        console.print("[cyan]python -m app.domain.rag.cli query[/cyan]\n")
    else:
        console.print(Panel.fit(
            "[bold yellow]일부 테스트 실패. 위의 오류 메시지를 확인하세요.[/bold yellow]",
            border_style="yellow"
        ))


if __name__ == "__main__":
    main()

