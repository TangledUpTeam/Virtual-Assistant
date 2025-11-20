"""
Gmail API 구현
메일 보내기, 읽기, 검색, 초안 생성 등
"""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any, List
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


class GmailAPI:
    """Gmail API 래퍼"""

    def __init__(self, credentials: Credentials):
        """
        Args:
            credentials: Google OAuth Credentials
        """
        self.credentials = credentials
        self.service = build('gmail', 'v1', credentials=credentials)

    def _create_message(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_base64: Optional[str] = None,
        attachment_filename: Optional[str] = None
    ) -> Dict[str, str]:
        """
        이메일 메시지 생성
        
        Args:
            to: 수신자 이메일
            subject: 제목
            body: 본문
            attachment_base64: 첨부 파일 (base64)
            attachment_filename: 첨부 파일 이름
            
        Returns:
            {"raw": str} - base64 인코딩된 메시지
        """
        if attachment_base64:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            # 본문 추가
            msg_body = MIMEText(body, 'plain', 'utf-8')
            message.attach(msg_body)
            
            # 첨부 파일 추가
            if attachment_filename:
                attachment_data = base64.b64decode(attachment_base64)
                attachment_part = MIMEBase('application', 'octet-stream')
                attachment_part.set_payload(attachment_data)
                encoders.encode_base64(attachment_part)
                attachment_part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment_filename}"'
                )
                message.attach(attachment_part)
        else:
            message = MIMEText(body, 'plain', 'utf-8')
            message['to'] = to
            message['subject'] = subject
        
        # base64 URL-safe 인코딩
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_base64: Optional[str] = None,
        attachment_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        이메일 보내기
        
        Args:
            to: 수신자 이메일
            subject: 제목
            body: 본문
            attachment_base64: 첨부 파일 (base64)
            attachment_filename: 첨부 파일 이름
            
        Returns:
            {"success": bool, "message_id": str}
        """
        try:
            message = self._create_message(to, subject, body, attachment_base64, attachment_filename)
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            return {
                "success": True,
                "message_id": sent_message.get('id'),
                "thread_id": sent_message.get('threadId')
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def list_messages(
        self,
        query: Optional[str] = None,
        max_results: int = 10,
        label_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        받은 메일 목록 조회
        
        Args:
            query: 검색 쿼리 (예: "from:example@gmail.com", "is:unread")
            max_results: 최대 결과 수
            label_ids: 레이블 ID 목록 (예: ['INBOX', 'UNREAD'])
            
        Returns:
            {"messages": List[dict], "success": bool}
        """
        try:
            params = {
                'userId': 'me',
                'maxResults': max_results
            }
            
            if query:
                params['q'] = query
            
            if label_ids:
                params['labelIds'] = label_ids
            
            results = self.service.users().messages().list(**params).execute()
            messages = results.get('messages', [])
            
            # 각 메시지의 snippet 조회
            message_list = []
            for msg in messages:
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
                
                message_list.append({
                    "id": msg['id'],
                    "thread_id": msg.get('threadId'),
                    "snippet": msg_data.get('snippet', ''),
                    "from": headers.get('From', ''),
                    "subject": headers.get('Subject', ''),
                    "date": headers.get('Date', '')
                })
            
            return {
                "success": True,
                "messages": message_list,
                "count": len(message_list)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        메시지 상세 조회
        
        Args:
            message_id: 메시지 ID
            
        Returns:
            {"id": str, "from": str, "to": str, "subject": str, "body": str, "attachments": List}
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            payload = message.get('payload', {})
            headers = {h['name']: h['value'] for h in payload.get('headers', [])}
            
            # 본문 추출
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        body_data = part['body'].get('data', '')
                        if body_data:
                            body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                            break
            else:
                body_data = payload.get('body', {}).get('data', '')
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
            
            # 첨부 파일 목록
            attachments = []
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('filename'):
                        attachments.append({
                            "filename": part['filename'],
                            "mime_type": part['mimeType'],
                            "size": part['body'].get('size', 0)
                        })
            
            return {
                "success": True,
                "id": message_id,
                "thread_id": message.get('threadId'),
                "from": headers.get('From', ''),
                "to": headers.get('To', ''),
                "subject": headers.get('Subject', ''),
                "date": headers.get('Date', ''),
                "body": body,
                "snippet": message.get('snippet', ''),
                "attachments": attachments
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_base64: Optional[str] = None,
        attachment_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        초안 생성
        
        Args:
            to: 수신자 이메일
            subject: 제목
            body: 본문
            attachment_base64: 첨부 파일 (base64)
            attachment_filename: 첨부 파일 이름
            
        Returns:
            {"draft_id": str, "success": bool}
        """
        try:
            message = self._create_message(to, subject, body, attachment_base64, attachment_filename)
            
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': message}
            ).execute()
            
            return {
                "success": True,
                "draft_id": draft.get('id'),
                "message_id": draft.get('message', {}).get('id')
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delete_message(self, message_id: str) -> Dict[str, Any]:
        """
        메시지 삭제
        
        Args:
            message_id: 메시지 ID
            
        Returns:
            {"success": bool}
        """
        try:
            self.service.users().messages().delete(
                userId='me',
                id=message_id
            ).execute()
            
            return {
                "success": True,
                "message_id": message_id
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        메시지를 읽음으로 표시
        
        Args:
            message_id: 메시지 ID
            
        Returns:
            {"success": bool}
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return {
                "success": True,
                "message_id": message_id
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def mark_as_unread(self, message_id: str) -> Dict[str, Any]:
        """
        메시지를 읽지 않음으로 표시
        
        Args:
            message_id: 메시지 ID
            
        Returns:
            {"success": bool}
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            
            return {
                "success": True,
                "message_id": message_id
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

