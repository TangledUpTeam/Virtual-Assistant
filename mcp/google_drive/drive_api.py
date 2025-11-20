"""
Google Drive API 구현
파일 업로드, 다운로드, 검색, 폴더 생성 등
"""

import base64
import io
from typing import Optional, Dict, Any, List
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials


class DriveAPI:
    """Google Drive API 래퍼"""

    def __init__(self, credentials: Credentials):
        """
        Args:
            credentials: Google OAuth Credentials
        """
        self.credentials = credentials
        self.service = build('drive', 'v3', credentials=credentials)

    def create_folder(self, name: str, parent_folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        폴더 생성
        
        Args:
            name: 폴더 이름
            parent_folder_id: 부모 폴더 ID (없으면 루트)
            
        Returns:
            {"folder_id": str, "name": str, "success": bool}
        """
        try:
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, name'
            ).execute()
            
            return {
                "success": True,
                "folder_id": folder.get('id'),
                "name": folder.get('name')
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def upload_file(
        self,
        local_path: str,
        folder_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        파일 업로드
        
        Args:
            local_path: 로컬 파일 경로
            folder_id: 업로드할 폴더 ID (없으면 루트)
            filename: 드라이브에 저장할 파일명 (없으면 원본 이름)
            
        Returns:
            {"file_id": str, "name": str, "success": bool}
        """
        try:
            import os
            
            if not filename:
                filename = os.path.basename(local_path)
            
            file_metadata = {'name': filename}
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(local_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType'
            ).execute()
            
            return {
                "success": True,
                "file_id": file.get('id'),
                "name": file.get('name'),
                "mime_type": file.get('mimeType')
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def download_file(self, file_id: str) -> Dict[str, Any]:
        """
        파일 다운로드 (base64 인코딩)
        
        Args:
            file_id: 다운로드할 파일 ID
            
        Returns:
            {"filename": str, "data": str (base64), "success": bool}
        """
        try:
            # 파일 메타데이터 조회
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='name, mimeType'
            ).execute()
            
            # 파일 다운로드
            request = self.service.files().get_media(fileId=file_id)
            file_data = io.BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_data.seek(0)
            file_bytes = file_data.read()
            
            # base64 인코딩
            encoded_data = base64.b64encode(file_bytes).decode('utf-8')
            
            return {
                "success": True,
                "filename": file_metadata.get('name'),
                "mime_type": file_metadata.get('mimeType'),
                "data": encoded_data,
                "size_bytes": len(file_bytes)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def read_file(self, file_id: str) -> Dict[str, Any]:
        """
        파일 읽기 (바이너리, base64 인코딩)
        
        Args:
            file_id: 읽을 파일 ID
            
        Returns:
            {"data": str (base64), "mime_type": str, "success": bool}
        """
        # download_file과 동일한 동작
        return self.download_file(file_id)

    def search_files(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        파일 검색
        
        Args:
            query: 검색 쿼리 (예: "name contains 'report'")
            max_results: 최대 결과 수
            
        Returns:
            {"files": List[dict], "success": bool}
        """
        try:
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, size)"
            ).execute()
            
            files = results.get('files', [])
            
            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def list_files(
        self,
        folder_id: Optional[str] = None,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        파일 목록 조회
        
        Args:
            folder_id: 폴더 ID (없으면 루트)
            max_results: 최대 결과 수
            
        Returns:
            {"files": List[dict], "success": bool}
        """
        try:
            query = f"'{folder_id}' in parents" if folder_id else None
            
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, size)"
            ).execute()
            
            files = results.get('files', [])
            
            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        파일 삭제
        
        Args:
            file_id: 삭제할 파일 ID
            
        Returns:
            {"success": bool}
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            
            return {
                "success": True,
                "file_id": file_id
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

