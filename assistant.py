#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Virtual Desk Assistant - Backend 실행 파일
루트 디렉토리에서 실행: python assistant.py
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리
ROOT_DIR = Path(__file__).parent
BACKEND_DIR = ROOT_DIR / "backend"

# Python path에 backend 추가
sys.path.insert(0, str(BACKEND_DIR))

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Virtual Desk Assistant Backend...")
    print(f"📂 Root Directory: {ROOT_DIR}")
    print(f"📂 Backend Directory: {BACKEND_DIR}")
    print(f"🌐 Server: http://localhost:8000")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print("-" * 50)
    
    # 현재 디렉토리를 backend로 변경
    os.chdir(BACKEND_DIR)
    
    # Uvicorn 서버 실행
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(BACKEND_DIR)],
        log_config=None,  # 기본 로그 설정 사용 (색상 코드 제거)
        use_colors=False  # Windows 호환성: 색상 출력 끄기
    )
