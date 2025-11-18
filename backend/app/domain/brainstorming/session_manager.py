"""
세션 관리 모듈

동시성을 고려한 임시 세션(Ephemeral Session) 생성, 조회, 삭제를 관리합니다.
자바의 ConcurrentHashMap과 유사하게 threading.Lock을 사용하여 스레드 안전성을 보장합니다.
"""

import uuid
import threading
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import shutil


class SessionManager:
    """
    세션 관리자 클래스
    
    - UUID 기반 세션 ID 생성
    - 스레드 안전한 세션 딕셔너리 관리
    - 세션별 데이터 디렉토리 관리
    """
    
    _instance = None
    _lock = threading.Lock()  # 클래스 레벨 Lock (싱글톤 생성용)
    
    def __new__(cls):
        """싱글톤 패턴: 전역에서 하나의 SessionManager만 존재"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """초기화 (싱글톤이므로 한 번만 실행됨)"""
        if not hasattr(self, '_initialized'):
            self._sessions: Dict[str, dict] = {}  # {session_id: session_info}
            self._session_lock = threading.Lock()  # 세션 딕셔너리 접근용 Lock
            self._async_lock = asyncio.Lock()  # 비동기 환경용 Lock
            
            # 현재 파일의 디렉토리 기준으로 경로 설정
            current_file = Path(__file__).resolve()
            self.module_dir = current_file.parent
            self.ephemeral_dir = self.module_dir / "data" / "ephemeral"
            
            # ephemeral 디렉토리 생성
            self.ephemeral_dir.mkdir(parents=True, exist_ok=True)
            
            self._initialized = True
            print(f"✅ SessionManager 초기화 완료")
            print(f"   - Ephemeral 디렉토리: {self.ephemeral_dir}")
    
    def create_session(self) -> str:
        """
        새로운 세션 생성 (동기 환경용)
        
        Returns:
            str: 생성된 세션 ID (UUID)
        """
        with self._session_lock:
            session_id = str(uuid.uuid4())
            session_dir = self.ephemeral_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            self._sessions[session_id] = {
                'id': session_id,
                'created_at': datetime.now().isoformat(),
                'directory': str(session_dir),
                'q1_purpose': None,
                'q2_warmup': None,
                'q3_associations': [],
                'ideas': [],
                'chroma_collection': f"ephemeral_session_{session_id.replace('-', '_')}"
            }
            
            print(f"✅ 세션 생성: {session_id}")
            return session_id
    
    async def create_session_async(self) -> str:
        """
        새로운 세션 생성 (비동기 환경용)
        
        Returns:
            str: 생성된 세션 ID (UUID)
        """
        async with self._async_lock:
            session_id = str(uuid.uuid4())
            session_dir = self.ephemeral_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            self._sessions[session_id] = {
                'id': session_id,
                'created_at': datetime.now().isoformat(),
                'directory': str(session_dir),
                'q1_purpose': None,
                'q2_warmup': None,
                'q3_associations': [],
                'ideas': [],
                'chroma_collection': f"ephemeral_session_{session_id.replace('-', '_')}"
            }
            
            print(f"✅ 세션 생성: {session_id}")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """
        세션 정보 조회 (동기 환경용)
        
        Args:
            session_id: 세션 ID
            
        Returns:
            dict: 세션 정보 또는 None
        """
        with self._session_lock:
            return self._sessions.get(session_id)
    
    async def get_session_async(self, session_id: str) -> Optional[dict]:
        """
        세션 정보 조회 (비동기 환경용)
        
        Args:
            session_id: 세션 ID
            
        Returns:
            dict: 세션 정보 또는 None
        """
        async with self._async_lock:
            return self._sessions.get(session_id)
    
    def update_session(self, session_id: str, updates: dict) -> bool:
        """
        세션 정보 업데이트 (동기 환경용)
        
        Args:
            session_id: 세션 ID
            updates: 업데이트할 정보 딕셔너리
            
        Returns:
            bool: 성공 여부
        """
        with self._session_lock:
            if session_id in self._sessions:
                self._sessions[session_id].update(updates)
                return True
            return False
    
    async def update_session_async(self, session_id: str, updates: dict) -> bool:
        """
        세션 정보 업데이트 (비동기 환경용)
        
        Args:
            session_id: 세션 ID
            updates: 업데이트할 정보 딕셔너리
            
        Returns:
            bool: 성공 여부
        """
        async with self._async_lock:
            if session_id in self._sessions:
                self._sessions[session_id].update(updates)
                return True
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (동기 환경용)
        
        메모리에서 세션 정보를 제거하고, 디스크의 세션 디렉토리도 삭제합니다.
        
        Args:
            session_id: 삭제할 세션 ID
            
        Returns:
            bool: 성공 여부
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return False
            
            session = self._sessions[session_id]
            session_dir = Path(session['directory'])
            
            # 디스크에서 세션 디렉토리 삭제
            if session_dir.exists():
                try:
                    shutil.rmtree(session_dir)
                    print(f"✅ 세션 디렉토리 삭제: {session_dir}")
                except Exception as e:
                    print(f"⚠️  세션 디렉토리 삭제 실패: {e}")
            
            # 메모리에서 세션 제거
            del self._sessions[session_id]
            print(f"✅ 세션 삭제: {session_id}")
            return True
    
    async def delete_session_async(self, session_id: str) -> bool:
        """
        세션 삭제 (비동기 환경용)
        
        메모리에서 세션 정보를 제거하고, 디스크의 세션 디렉토리도 삭제합니다.
        
        Args:
            session_id: 삭제할 세션 ID
            
        Returns:
            bool: 성공 여부
        """
        async with self._async_lock:
            if session_id not in self._sessions:
                return False
            
            session = self._sessions[session_id]
            session_dir = Path(session['directory'])
            
            # 디스크에서 세션 디렉토리 삭제
            if session_dir.exists():
                try:
                    shutil.rmtree(session_dir)
                    print(f"✅ 세션 디렉토리 삭제: {session_dir}")
                except Exception as e:
                    print(f"⚠️  세션 디렉토리 삭제 실패: {e}")
            
            # 메모리에서 세션 제거
            del self._sessions[session_id]
            print(f"✅ 세션 삭제: {session_id}")
            return True
    
    def list_sessions(self) -> list:
        """
        모든 활성 세션 목록 조회 (동기 환경용)
        
        Returns:
            list: 세션 ID 목록
        """
        with self._session_lock:
            return list(self._sessions.keys())
    
    async def list_sessions_async(self) -> list:
        """
        모든 활성 세션 목록 조회 (비동기 환경용)
        
        Returns:
            list: 세션 ID 목록
        """
        async with self._async_lock:
            return list(self._sessions.keys())
    
    def get_session_count(self) -> int:
        """
        현재 활성 세션 개수 조회 (동기 환경용)
        
        Returns:
            int: 세션 개수
        """
        with self._session_lock:
            return len(self._sessions)
    
    async def get_session_count_async(self) -> int:
        """
        현재 활성 세션 개수 조회 (비동기 환경용)
        
        Returns:
            int: 세션 개수
        """
        async with self._async_lock:
            return len(self._sessions)


# 테스트 코드
if __name__ == "__main__":
    print("=" * 60)
    print("세션 매니저 테스트")
    print("=" * 60)
    
    # SessionManager 인스턴스 생성 (싱글톤)
    manager = SessionManager()
    
    # 세션 3개 생성
    print("\n[1] 세션 생성 테스트")
    session1 = manager.create_session()
    session2 = manager.create_session()
    session3 = manager.create_session()
    
    # 세션 목록 조회
    print(f"\n[2] 현재 활성 세션: {manager.get_session_count()}개")
    print(f"    세션 ID 목록: {manager.list_sessions()}")
    
    # 세션 정보 조회
    print(f"\n[3] 세션 정보 조회")
    info = manager.get_session(session1)
    print(f"    세션 ID: {info['id']}")
    print(f"    생성 시간: {info['created_at']}")
    print(f"    디렉토리: {info['directory']}")
    print(f"    ChromaDB 컬렉션: {info['chroma_collection']}")
    
    # 세션 업데이트
    print(f"\n[4] 세션 업데이트")
    manager.update_session(session1, {
        'q1_purpose': '모바일 앱 아이디어',
        'q3_associations': ['건강', '운동', '기록']
    })
    updated_info = manager.get_session(session1)
    print(f"    Q1 목적: {updated_info['q1_purpose']}")
    print(f"    Q3 연상: {updated_info['q3_associations']}")
    
    # 세션 삭제
    print(f"\n[5] 세션 삭제")
    manager.delete_session(session1)
    manager.delete_session(session2)
    print(f"    남은 세션: {manager.get_session_count()}개")
    
    # 정리
    print(f"\n[6] 정리")
    manager.delete_session(session3)
    print(f"    최종 세션 개수: {manager.get_session_count()}개")
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료")
    print("=" * 60)

