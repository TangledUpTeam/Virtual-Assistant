"""
Insurance RAG CLI 모듈 진입점

이 파일이 있으면 다음 명령어로 실행 가능:
  python -m app.domain.rag.Insurance process internal_insurance/uploads
  python -m app.domain.rag.Insurance query "상해요인 정의"
"""
from .cli import main

if __name__ == "__main__":
    main()


