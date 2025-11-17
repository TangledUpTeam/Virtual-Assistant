/**
 * 채팅 서비스 모듈
 * 실제 백엔드 API나 GPT/RAG 모듈 호출을 담당
 * 현재는 더미 응답 반환
 */

/**
 * 챗봇에게 메시지를 전송하고 응답을 받음
 * @param {string} userText - 사용자 입력 텍스트
 * @returns {Promise<string>} 챗봇 응답
 */
export async function callChatModule(userText) {
  // 더미 응답: 실제로는 여기서 백엔드 API 호출
  // 예: await fetch('http://localhost:8000/api/chat', { method: 'POST', body: JSON.stringify({ message: userText }) })
  
  console.log('📨 사용자 메시지:', userText);
  
  // 1-2초 딜레이 시뮬레이션
  await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1000));
  
  // 더미 응답 목록
  const dummyResponses = [
    '안녕하세요! 무엇을 도와드릴까요? 😊',
    '네, 알겠습니다. 제가 도와드리겠습니다!',
    '흥미로운 질문이네요! 조금만 기다려주세요.',
    '좋은 생각이에요! 그렇게 해보시는 건 어떨까요?',
    '더 자세히 설명해주시면 더 정확하게 답변드릴 수 있을 것 같아요.',
    '제가 이해한 바로는... 맞나요?',
    '음, 그 부분은 조금 더 생각해봐야 할 것 같아요! 🤔',
  ];
  
  // 랜덤 응답 반환
  const response = dummyResponses[Math.floor(Math.random() * dummyResponses.length)];
  
  console.log('🤖 AI 응답:', response);
  
  return response;
}

