/**
 * 업무 관련 API 호출 및 Intent Router
 * 
 * Intent 분류:
 * 1. task_recommend - 오늘 추천 업무
 * 2. report_daily - 일일 보고서
 * 3. report_weekly - 주간 보고서
 * 4. report_monthly - 월간 보고서
 * 5. report_yearly - 실적 보고서
 * 6. default - 일반 대화
 */

const API_BASE = 'http://localhost:8000/api/v1';

export function getOwnerFromCookie() {
  try {
    const raw = getCookie('user');
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const name = parsed?.name || parsed?.username || parsed?.id || null;
    if (name) {
      window.currentOwner = name;
    }
    return name;
  } catch (error) {
    console.warn('Failed to parse user cookie for owner:', error);
    return null;
  }
}

// Initialize global owner once on module load
if (typeof window !== 'undefined') {
  window.currentOwner = window.currentOwner || getOwnerFromCookie() || null;
}

/**
 * Intent Router: 사용자 발화를 분석하여 적절한 기능으로 라우팅
 */
export async function callChatModule(userText) {
  console.log('📨 [Intent Router] 사용자 메시지:', userText);
  
  const text = userText.toLowerCase().trim();
  
  // Intent 1: 추천 업무 요청
  if (isTaskRecommendationIntent(text)) {
    console.log('🎯 [Intent] task_recommend');
    return await getTodayPlan();
  }
  
  // Intent 2: 일일 보고서
  if (isDailyReportIntent(text)) {
    console.log('📝 [Intent] report_daily (reportService.js로 위임)');
    return {
      type: 'daily_report_trigger',
      data: '일일 보고서 작성을 시작합니다.'
    };
  }
  
  // Intent 3: 주간 보고서
  if (isWeeklyReportIntent(text)) {
    console.log('📊 [Intent] report_weekly');
    return await generateWeeklyReport();
  }
  
  // Intent 4: 월간 보고서
  if (isMonthlyReportIntent(text)) {
    console.log('📈 [Intent] report_monthly');
    return await generateMonthlyReport();
  }
  
  // Intent 5: 실적(연간) 보고서
  if (isYearlyReportIntent(text)) {
    console.log('📋 [Intent] report_yearly');
    return await generateYearlyReport();
  }
  
  // Intent 6: 일반 대화
  console.log('💬 [Intent] default - 일반 대화');
  return {
    type: 'text',
    data: `"${userText}" - 답변을 준비 중입니다! 😊\n\n도움말:\n• "오늘 뭐할지 추천 좀" - 업무 추천\n• "일일 보고서 작성" - 일일 보고서\n• "주간 보고서" - 주간 보고서\n• "월간 보고서" - 월간 보고서\n• "실적 보고서" - 연간 실적 보고서`
  };
}

/**
 * Intent 감지: 추천 업무
 */
function isTaskRecommendationIntent(text) {
  const keywords = ['추천', '뭐할', '뭐해', '업무', '할일', 'todo', 'task'];
  const triggerWords = ['추천', '뭐할', '계획'];
  
  return keywords.some(kw => text.includes(kw)) && 
         triggerWords.some(tw => text.includes(tw));
}

/**
 * Intent 감지: 일일 보고서
 */
function isDailyReportIntent(text) {
  return (text.includes('일일') || text.includes('데일리') || text.includes('daily')) &&
         (text.includes('보고서') || text.includes('작성') || text.includes('리포트'));
}

/**
 * Intent 감지: 주간 보고서
 */
function isWeeklyReportIntent(text) {
  return (text.includes('주간') || text.includes('위클리') || text.includes('weekly')) &&
         (text.includes('보고서') || text.includes('작성') || text.includes('리포트') || text.includes('생성'));
}

/**
 * Intent 감지: 월간 보고서
 */
function isMonthlyReportIntent(text) {
  return (text.includes('월간') || text.includes('먼슬리') || text.includes('monthly')) &&
         (text.includes('보고서') || text.includes('작성') || text.includes('리포트') || text.includes('생성'));
}

/**
 * Intent 감지: 실적(연간) 보고서
 */
function isYearlyReportIntent(text) {
  return (text.includes('실적') || text.includes('연간') || text.includes('yearly') || text.includes('annual')) &&
         (text.includes('보고서') || text.includes('작성') || text.includes('리포트') || text.includes('생성'));
}

/**
 * 오늘의 추천 업무 가져오기
 * 
 * 우선순위:
 * 1순위: 익일 업무 계획 데이터
 * 2순위: 전날 미종결 업무
 * 3순위: VectorDB에서 최근 1주 업무 참고
 */
export async function getTodayPlan() {
  try {
    console.log('🔄 [API] /plan/today 호출 중...');
    
    const { headers, owner } = buildRequestContext();
    const requestBody = {
      target_date: new Date().toISOString().split('T')[0]
    };
    if (owner) {
      requestBody.owner = owner;
    }
    
    const response = await fetch(`${API_BASE}/plan/today`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('✅ [API] 추천 업무 받음:', data);
    
    return {
      type: 'task_recommendations',
      data: {
        tasks: data.tasks || [],
        summary: data.summary || '오늘의 추천 업무입니다!',
        owner: data.owner || owner || '',
        target_date: data.target_date || requestBody.target_date,
        task_sources: data.task_sources || []
      }
    };
  } catch (error) {
    console.error('❌ [API] 추천 업무 가져오기 실패:', error);
    return {
      type: 'error',
      data: '추천 업무를 가져오는데 실패했습니다. 😢'
    };
  }
}

/**
 * 주간 보고서 생성
 */
async function generateWeeklyReport() {
  try {
    console.log('🔄 [API] /weekly/generate 호출 중...');
    
    const { headers, owner } = buildRequestContext();
    const body = {
      target_date: getMonday(new Date())
    };
    if (owner) {
      body.owner = owner;
    }
    
    const response = await fetch(`${API_BASE}/weekly/generate`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('✅ [API] 주간 보고서 생성 완료');
    
    return {
      type: 'text',
      data: `📊 주간 보고서가 생성되었습니다!\n\n기간: ${data?.period?.start || body.target_date} ~ ${data?.period?.end || ''}`
    };
  } catch (error) {
    console.error('❌ [API] 주간 보고서 생성 실패:', error);
    return {
      type: 'text',
      data: '주간 보고서 생성 중 오류가 발생했습니다. 😢'
    };
  }
}

/**
 * 월간 보고서 생성
 */
async function generateMonthlyReport() {
  try {
    console.log('🔄 [API] /monthly/generate 호출 중...');
    
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    
    const { headers, owner } = buildRequestContext();
    const body = { year, month };
    if (owner) {
      body.owner = owner;
    }
    
    const response = await fetch(`${API_BASE}/monthly/generate`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('✅ [API] 월간 보고서 생성 완료');
    
    return {
      type: 'text',
      data: `📈 월간 보고서가 생성되었습니다!\n\n기간: ${data?.period?.start || `${year}년 ${month}월`} ~ ${data?.period?.end || ''}`
    };
  } catch (error) {
    console.error('❌ [API] 월간 보고서 생성 실패:', error);
    return {
      type: 'text',
      data: '월간 보고서 생성 중 오류가 발생했습니다. 😢'
    };
  }
}

/**
 * 실적(연간) 보고서 생성
 */
async function generateYearlyReport() {
  try {
    console.log('🔄 [API] /performance_report/generate 호출 중...');
    
    const year = new Date().getFullYear();
    
    const { headers, owner } = buildRequestContext();
    const body = { year };
    if (owner) {
      body.owner = owner;
    }
    
    const response = await fetch(`${API_BASE}/performance_report/generate`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('✅ [API] 실적 보고서 생성 완료');
    
    return {
      type: 'text',
      data: `📋 ${year}년 실적 보고서가 생성되었습니다!\n\n총 업무: ${data.total_tasks || 0}개\n총 근무일: ${data.total_days || 0}일`
    };
  } catch (error) {
    console.error('❌ [API] 실적 보고서 생성 실패:', error);
    return {
      type: 'text',
      data: '실적 보고서 생성 중 오류가 발생했습니다. 😢'
    };
  }
}

/**
 * 선택한 업무 저장 (금일 진행 업무로 등록)
 * @param {string} owner - 사용자 이름
 * @param {string} targetDate - 대상 날짜
 * @param {Array} tasks - 저장할 업무 목록
 * @param {boolean} append - 기존 업무에 추가할지 여부 (기본값: false)
 */
export async function saveSelectedTasks(owner, targetDate, tasks, append = false) {
  try {
    console.log('🔄 [API] /daily/select_main_tasks 호출 중...', { append, tasksCount: tasks.length });
    
    const response = await fetch(`${API_BASE}/daily/select_main_tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        owner: owner || window.currentOwner || getOwnerFromCookie(),
        target_date: targetDate,
        main_tasks: tasks,
        append: append
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('✅ [API] 업무 저장 완료:', data);
    
    return {
      success: true,
      saved_count: tasks.length,
      data: data
    };
  } catch (error) {
    console.error('❌ [API] 업무 저장 실패:', error);
    return {
      success: false,
      message: error.message
    };
  }
}

/**
 * 금일 진행 업무 수정
 */
export async function updateMainTasks(owner, targetDate, tasks) {
  try {
    console.log('🔄 [API] /daily/update_main_tasks 호출 중...');
    
    const response = await fetch(`${API_BASE}/daily/update_main_tasks`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        owner: owner || window.currentOwner || getOwnerFromCookie(),
        target_date: targetDate,
        main_tasks: tasks
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('✅ [API] 업무 수정 완료:', data);
    
    return {
      success: true,
      updated_count: tasks.length,
      data: data
    };
  } catch (error) {
    console.error('❌ [API] 업무 수정 실패:', error);
    return {
      success: false,
      message: error.message
    };
  }
}

/**
 * 유틸: 이번 주 월요일 날짜 구하기
 */
function getMonday(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(d.setDate(diff));
  return monday.toISOString().split('T')[0];
}

/**
 * 공통 요청 컨텍스트(헤더, owner) 생성
 */
function buildRequestContext() {
  const headers = { 'Content-Type': 'application/json' };
  const accessToken = getAccessToken();

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const owner = window.currentOwner || getOwnerFromCookie();
  if (owner) {
    window.currentOwner = owner;
  }
  return { headers, owner };
}

function getAccessToken() {
  return sessionStorage.getItem('access_token') || getCookie('access_token');
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return decodeURIComponent(parts.pop().split(';').shift());
  }
  return null;
}
