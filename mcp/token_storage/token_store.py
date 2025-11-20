"""
OAuth 토큰 저장/불러오기 모듈
user_id 기반으로 토큰을 파일 시스템에 저장
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class TokenStore:
    """사용자별 OAuth 토큰 저장소"""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Args:
            storage_dir: 토큰 저장 디렉토리 (기본값: ./mcp/token_storage/tokens/)
        """
        if storage_dir is None:
            storage_dir = os.path.join(
                os.path.dirname(__file__), "tokens"
            )
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_token_path(self, user_id: str, service: str) -> Path:
        """
        토큰 파일 경로 생성
        
        Args:
            user_id: 사용자 ID
            service: 서비스 이름 (예: 'google_drive', 'gmail')
            
        Returns:
            토큰 파일 경로
        """
        filename = f"{user_id}_{service}_token.json"
        return self.storage_dir / filename

    def save_token(self, user_id: str, service: str, token_data: Dict[str, Any]) -> bool:
        """
        OAuth 토큰 저장
        
        Args:
            user_id: 사용자 ID
            service: 서비스 이름
            token_data: 토큰 데이터 (access_token, refresh_token, expiry 등)
            
        Returns:
            저장 성공 여부
        """
        try:
            token_path = self._get_token_path(user_id, service)
            with open(token_path, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2)
            return True
        except Exception as e:
            print(f"토큰 저장 실패: {e}")
            return False

    def load_token(self, user_id: str, service: str) -> Optional[Dict[str, Any]]:
        """
        OAuth 토큰 불러오기
        
        Args:
            user_id: 사용자 ID
            service: 서비스 이름
            
        Returns:
            토큰 데이터 또는 None
        """
        try:
            token_path = self._get_token_path(user_id, service)
            if not token_path.exists():
                return None
            
            with open(token_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"토큰 불러오기 실패: {e}")
            return None

    def delete_token(self, user_id: str, service: str) -> bool:
        """
        OAuth 토큰 삭제
        
        Args:
            user_id: 사용자 ID
            service: 서비스 이름
            
        Returns:
            삭제 성공 여부
        """
        try:
            token_path = self._get_token_path(user_id, service)
            if token_path.exists():
                token_path.unlink()
            return True
        except Exception as e:
            print(f"토큰 삭제 실패: {e}")
            return False

    def token_exists(self, user_id: str, service: str) -> bool:
        """
        토큰 존재 여부 확인
        
        Args:
            user_id: 사용자 ID
            service: 서비스 이름
            
        Returns:
            토큰 존재 여부
        """
        token_path = self._get_token_path(user_id, service)
        return token_path.exists()

