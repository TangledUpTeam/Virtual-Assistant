const API_BASE = 'http://localhost:8000/api/v1';

export async function getUserFromCookie() {
  try {
    // Electron 환경에서 IPC를 통해 쿠키 가져오기 시도
    let userCookieValue = null;
    
    // Electron 환경 확인
    if (typeof require !== 'undefined') {
      try {
        const { ipcRenderer } = require('electron');
        const cookies = await ipcRenderer.invoke('get-main-cookies');
        console.log('[DEBUG] getUserFromCookie - IPC 쿠키:', cookies);
        
        if (cookies && cookies.user) {
          userCookieValue = cookies.user;
        }
      } catch (ipcError) {
        console.warn('[DEBUG] getUserFromCookie - IPC 실패, document.cookie 시도:', ipcError);
      }
    }
    
    // IPC 실패 시 document.cookie에서 직접 파싱
    if (!userCookieValue) {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith('user=')) {
          userCookieValue = cookie.substring(5); // 'user=' 제거
          break;
        }
      }
    }
    
    console.log('[DEBUG] getUserFromCookie - 쿠키 파싱:', {
      all_cookies: document.cookie,
      user_cookie_found: !!userCookieValue,
      user_cookie_length: userCookieValue?.length
    });
    
    if (!userCookieValue) {
      console.warn('[DEBUG] getUserFromCookie - user 쿠키가 없습니다');
      return null;
    }
    
    // URL 디코딩
    const decoded = decodeURIComponent(userCookieValue);
    console.log('[DEBUG] getUserFromCookie - 디코딩 후:', decoded);
    
    const parsed = JSON.parse(decoded);
    console.log('[DEBUG] getUserFromCookie - 파싱 후:', parsed);
    
    if (typeof parsed?.id === 'undefined') {
      console.warn('[DEBUG] getUserFromCookie - parsed.id가 없습니다');
      return null;
    }

    if (typeof window !== 'undefined' && parsed.id) {
      window.currentUserId = window.currentUserId || parsed.id;
    }

    const result = {
      id: parsed.id,
      name: parsed.name || '',
      email: parsed.email || ''
    };
    
    console.log('[DEBUG] getUserFromCookie - 최종 결과:', result);
    return result;
  } catch (error) {
    console.error('[DEBUG] getUserFromCookie - 에러:', error);
    console.warn('Failed to parse user cookie:', error);
    return null;
  }
}

if (typeof window !== 'undefined') {
  const user = getUserFromCookie();
  window.currentUserId = window.currentUserId || user?.id || null;
}

export async function buildRequestContext() {
  const headers = { 'Content-Type': 'application/json' };
  const accessToken = getAccessToken();

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const user = await getUserFromCookie();  // ✅ async로 변경
  const ownerId = window.currentUserId || user?.id || null;
  const owner = user?.name || null;  // ✅ user 쿠키에서 이름 가져오기

  if (typeof window !== 'undefined' && ownerId) {
    window.currentUserId = ownerId;
  }

  return { 
    headers, 
    owner_id: ownerId,
    owner: owner  // ✅ owner (사용자 이름) 반환
  };
}

export async function callChatModule(userText) {
  console.log('🔎 [Intent Router] message:', userText);

  const text = userText.toLowerCase().trim();

  if (isTaskRecommendationIntent(text)) {
    return await getTodayPlan();
  }

  if (isDailyReportIntent(text)) {
    return {
      type: 'daily_report_trigger',
      data: '일일 보고서를 작성할게요.'
    };
  }

  if (isWeeklyReportIntent(text)) {
    return await generateWeeklyReport();
  }

  if (isMonthlyReportIntent(text)) {
    return await generateMonthlyReport();
  }

  if (isYearlyReportIntent(text)) {
    return await generateYearlyReport();
  }

  return {
    type: 'text',
    data: `"${userText}" - 아직 학습 중입니다! 😊\n\n예시 질문\n- "오늘 뭐할지 추천해줘"\n- "일일 보고서 작성"\n- "주간 보고서"\n- "월간 보고서"\n- "연간 보고서"`
  };
}

export async function getTodayPlan() {
  try {
    console.log('📌 [API] /plan/today 호출 시작...');

    const { headers, owner_id } = await buildRequestContext();
    const requestBody = {
      target_date: new Date().toISOString().split('T')[0]
    };
    if (owner_id) {
      requestBody.owner_id = owner_id;
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
    console.log('✅ [API] 추천 업무 응답:', data);

    return {
      type: 'task_recommendations',
      data: {
        tasks: data.tasks || [],
        summary: data.summary || '오늘의 추천 업무입니다.',
        owner_id: data.owner_id || owner_id || null,
        target_date: data.target_date || requestBody.target_date,
        task_sources: data.task_sources || []
      }
    };
  } catch (error) {
    console.error('❌ [API] 추천 업무 호출 실패:', error);
    return {
      type: 'error',
      data: '추천 업무를 불러오는 데 실패했습니다.'
    };
  }
}

async function generateWeeklyReport() {
  try {
    console.log('📌 [API] /weekly/generate 호출 시작...');

    const { headers, owner_id } = await buildRequestContext();
    const body = {
      target_date: getMonday(new Date())
    };
    if (owner_id) {
      body.owner_id = owner_id;
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
      data: `주간 보고서가 생성되었습니다.\n\n기간: ${data?.period?.start || body.target_date} ~ ${data?.period?.end || ''}`
    };
  } catch (error) {
    console.error('❌ [API] 주간 보고서 생성 실패:', error);
    return {
      type: 'text',
      data: '주간 보고서 생성 중 오류가 발생했습니다.'
    };
  }
}

async function generateMonthlyReport() {
  try {
    console.log('📌 [API] /monthly/generate 호출 시작...');

    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;

    const { headers, owner_id } = await buildRequestContext();
    const body = { year, month };
    if (owner_id) {
      body.owner_id = owner_id;
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
      data: `월간 보고서가 생성되었습니다.\n\n기간: ${data?.period?.start || `${year}년 ${month}월`} ~ ${data?.period?.end || ''}`
    };
  } catch (error) {
    console.error('❌ [API] 월간 보고서 생성 실패:', error);
    return {
      type: 'text',
      data: '월간 보고서 생성 중 오류가 발생했습니다.'
    };
  }
}

async function generateYearlyReport() {
  try {
    console.log('📌 [API] /performance_report/generate 호출 시작...');

    const year = new Date().getFullYear();

    const { headers, owner_id } = await buildRequestContext();
    const body = { year };
    if (owner_id) {
      body.owner_id = owner_id;
    }

    const response = await fetch(`${API_BASE}/performance_report/generate`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });

    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }

    await response.json();
    console.log('✅ [API] 연간 보고서 생성 완료');

    return {
      type: 'text',
      data: `${year}년 연간 보고서가 생성되었습니다.`
    };
  } catch (error) {
    console.error('❌ [API] 연간 보고서 생성 실패:', error);
    return {
      type: 'text',
      data: '연간 보고서 생성 중 오류가 발생했습니다.'
    };
  }
}

export async function saveSelectedTasks(ownerId, targetDate, tasks, append = false) {
  try {
    console.log('📌 [API] /daily/select_main_tasks 호출 시작...', { append, tasksCount: tasks.length });

    const { headers, owner_id } = await buildRequestContext();
    const response = await fetch(`${API_BASE}/daily/select_main_tasks`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        owner_id: ownerId || owner_id,
        target_date: targetDate,
        main_tasks: tasks,
        append: append
      })
    });

    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }

    const data = await response.json();
    console.log('✅ [API] 업무 저장 응답:', data);

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

export async function updateMainTasks(ownerId, targetDate, tasks) {
  try {
    console.log('📌 [API] /daily/update_main_tasks 호출 시작...');

    const { headers, owner_id } = await buildRequestContext();
    const response = await fetch(`${API_BASE}/daily/update_main_tasks`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({
        owner_id: ownerId || owner_id,
        target_date: targetDate,
        main_tasks: tasks
      })
    });

    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }

    const data = await response.json();
    console.log('✅ [API] 업무 수정 응답:', data);

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

function isTaskRecommendationIntent(text) {
  const keywords = ['추천', '뭐할', '뭐해', '업무', '오늘', 'todo', 'task'];
  const triggerWords = ['추천', '뭐할', '계획'];

  return keywords.some(kw => text.includes(kw)) &&
         triggerWords.some(tw => text.includes(tw));
}

function isDailyReportIntent(text) {
  return (text.includes('일일') || text.includes('daily')) &&
         (text.includes('보고') || text.includes('작성') || text.includes('리포트'));
}

function isWeeklyReportIntent(text) {
  return (text.includes('주간') || text.includes('weekly')) &&
         (text.includes('보고') || text.includes('작성') || text.includes('리포트'));
}

function isMonthlyReportIntent(text) {
  return (text.includes('월간') || text.includes('monthly')) &&
         (text.includes('보고') || text.includes('작성') || text.includes('리포트'));
}

function isYearlyReportIntent(text) {
  return (text.includes('연간') || text.includes('연도') || text.includes('yearly') || text.includes('annual')) &&
         (text.includes('보고') || text.includes('작성') || text.includes('리포트'));
}

function getMonday(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(d.setDate(diff));
  return monday.toISOString().split('T')[0];
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
