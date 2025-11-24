/**
 * 채팅 서비스 모듈
 * 백엔드 API 호출을 담당
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

// 세션 ID 및 토큰 저장
let sessionId = null;
let accessToken = null;

/**
 * 액세스 토큰 설정
 * @param {string} token - JWT 액세스 토큰
 */
export function setAccessToken(token) {
  accessToken = token;
  console.log('✅ 액세스 토큰 설정됨');
}

/**
 * 세션 초기화
 */
async function initSession() {
  if (sessionId) return sessionId;
  
  try {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    // 토큰이 있으면 Authorization 헤더 추가
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/chatbot/session`, {
      method: 'POST',
      headers: headers
    });
    
    if (!response.ok) {
      throw new Error(`세션 생성 실패: ${response.status}`);
    }
    
    const result = await response.json();
    sessionId = result.session_id;
    console.log('✅ 챗봇 세션 생성:', sessionId);
    return sessionId;
  } catch (error) {
    console.error('❌ 세션 생성 오류:', error);
    throw error;
  }
}

/**
 * 심리 상담 관련 키워드 확인
 * @param {string} text - 사용자 입력 텍스트
 * @returns {boolean} 심리 상담 관련 여부
 */
function isTherapyRelated(text) {
  const therapyKeywords = [
    '힘들어', '상담', '짜증', '우울', '불안', '스트레스',
    '고민', '걱정', '슬프', '외로', '화나', '답답',
    '아들러', 'adler', 'counseling', 'therapy', 'help',
    'depressed', 'anxious', '심리'
  ];
  
  const lowerText = text.toLowerCase();
  return therapyKeywords.some(keyword => lowerText.includes(keyword));
}

/**
 * 챗봇에게 메시지를 전송하고 응답을 받음
 * @param {string} userText - 사용자 입력 텍스트
 * @returns {Promise<{type: string, data: any}>} 챗봇 응답 (type과 data 포함)
 */
export async function callChatModule(userText) {
  console.log('📨 사용자 메시지:', userText);
  
  // 심리 상담 관련 키워드가 있으면 Therapy API 호출
  if (isTherapyRelated(userText)) {
    console.log('🎭 심리 상담 모드 감지');
    return await sendTherapyMessage(userText);
  }
  
  // "오늘 뭐할지 추천" 등의 키워드가 있으면 TodayPlan API 호출
  if (userText.includes('오늘') && (userText.includes('추천') || userText.includes('뭐할'))) {
    return await getTodayPlan();
  }
  
  // 챗봇 API 호출
  return await sendChatbotMessage(userText);
}

/**
 * 심리 상담 메시지 전송
 * @param {string} userText - 사용자 입력 텍스트
 * @returns {Promise<{type: string, data: any}>}
 */
async function sendTherapyMessage(userText) {
  try {
    const response = await fetch(`${API_BASE_URL}/therapy/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: userText
      })
    });
    
    if (!response.ok) {
      throw new Error(`심리 상담 API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('🎭 아들러 상담사 응답:', result);
    
    return {
      type: 'therapy',
      data: result.answer,
      mode: result.mode,
      used_chunks: result.used_chunks
    };
  } catch (error) {
    console.error('❌ 심리 상담 API 오류:', error);
    return {
      type: 'error',
      data: '심리 상담 시스템에 연결할 수 없습니다. 백엔드 서버를 확인해주세요.'
    };
  }
}

/**
 * 챗봇 메시지 전송
 * @param {string} userText - 사용자 입력 텍스트
 * @returns {Promise<{type: string, data: any}>}
 */
async function sendChatbotMessage(userText) {
  try {
    // 세션 초기화
    await initSession();
    
    const headers = {
      'Content-Type': 'application/json',
    };
    
    // 토큰이 있으면 Authorization 헤더 추가
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/chatbot/message`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        session_id: sessionId,
        message: userText
      })
    });
    
    if (!response.ok) {
      throw new Error(`챗봇 API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('🤖 챗봇 응답:', result);
    
    return {
      type: 'text',
      data: result.assistant_message
    };
  } catch (error) {
    console.error('❌ 챗봇 API 오류:', error);
    return {
      type: 'error',
      data: '챗봇 응답을 가져오는 중 오류가 발생했습니다. 로그인이 필요할 수 있습니다.'
    };
  }
}

/**
 * 오늘의 추천 업무 가져오기
 * @returns {Promise<{type: string, data: any}>}
 */
async function getTodayPlan() {
  try {
    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    const owner = '김보험'; // 현재는 하드코딩 (추후 로그인 정보 사용)
    
    const response = await fetch(`${API_BASE_URL}/plan/today`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        owner: owner,
        target_date: today
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('🎯 추천 업무:', result);
    
    return {
      type: 'task_recommendations',
      data: {
        tasks: result.tasks || [],
        summary: result.summary || '',
        owner: owner,
        target_date: today
      }
    };
  } catch (error) {
    console.error('❌ API 호출 오류:', error);
    return {
      type: 'error',
      data: '추천 업무를 가져오는 중 오류가 발생했습니다. 백엔드 서버가 실행 중인지 확인해주세요.'
    };
  }
}

/**
 * 선택된 업무 저장하기
 * @param {string} owner - 작성자
 * @param {string} targetDate - 대상 날짜
 * @param {Array} mainTasks - 선택된 업무 리스트
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function saveSelectedTasks(owner, targetDate, mainTasks) {
  try {
    const response = await fetch(`${API_BASE_URL}/daily/select_main_tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        owner: owner,
        target_date: targetDate,
        main_tasks: mainTasks
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ 업무 저장 완료:', result);
    
    return {
      success: true,
      message: result.message || '업무가 저장되었습니다.',
      saved_count: result.saved_count || 0
    };
  } catch (error) {
    console.error('❌ 업무 저장 오류:', error);
    return {
      success: false,
      message: '업무 저장에 실패했습니다.'
    };
  }
}

