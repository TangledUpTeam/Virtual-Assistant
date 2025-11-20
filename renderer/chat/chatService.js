/**
 * 채팅 서비스 모듈
 * 백엔드 API 호출을 담당
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

/**
 * 챗봇에게 메시지를 전송하고 응답을 받음
 * @param {string} userText - 사용자 입력 텍스트
 * @returns {Promise<{type: string, data: any}>} 챗봇 응답 (type과 data 포함)
 */
export async function callChatModule(userText) {
  console.log('📨 사용자 메시지:', userText);
  
  // 기본 응답 (추후 일반 챗봇 API 연결 가능)
  return {
    type: 'text',
    data: '안녕하세요! 일반 대화 기능은 준비 중입니다. 😊'
  };
}
