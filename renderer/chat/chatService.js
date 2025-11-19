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
  
  // "오늘 뭐할지 추천" 등의 키워드가 있으면 TodayPlan API 호출
  if (userText.includes('오늘') && (userText.includes('추천') || userText.includes('뭐할'))) {
    return await getTodayPlan();
  }
  
  // 기본 응답 (추후 확장 가능)
  return {
    type: 'text',
    data: '안녕하세요! "오늘 뭐할지 추천 좀"이라고 말씀해주시면 업무를 추천해드립니다. 😊'
  };
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

