/**
 * 보고서 & 업무 플래닝 통합 패널
 * 팝업 전용 버전
 */

const API_BASE = 'http://localhost:8000/api/v1';

let messages = [];
let reportPanel = null;
let messagesContainer = null;
let reportInput = null;
let sendBtn = null;
let isInitialized = false;

// FSM 상태
let chatMode = 'normal'; // 'normal' 또는 'daily_fsm'
let dailySessionId = null;
let dailyOwner = '김보험';

// 업무 플래닝 선택 상태
let selectedTasks = new Set();
let currentRecommendation = null;

// 날짜 설정
let dateSettingsPanel = null;
let currentReportType = null;
let customDates = {
  daily: null,
  weekly: null,
  monthly: { year: null, month: null }
};

/**
 * 보고서 패널 초기화
 */
export function initReportPanel() {
  if (isInitialized) return;
  
  reportPanel = document.getElementById('report-panel');
  messagesContainer = document.getElementById('report-messages');
  reportInput = document.getElementById('report-input');
  sendBtn = document.getElementById('report-send-btn');
  dateSettingsPanel = document.getElementById('date-settings-panel');
  
  if (!reportPanel || !messagesContainer || !reportInput || !sendBtn) {
    console.error('보고서 패널 요소를 찾을 수 없습니다.');
    return;
  }
  
  // 초기 메시지
  addMessage('assistant', '📝 보고서 & 업무 관리를 도와드립니다!\n\n• "오늘 업무 플래닝" - 업무 추천\n• "일일 보고서" - 일일 보고서 작성\n• "주간 보고서" - 주간 보고서 생성\n• "월간 보고서" - 월간 보고서 생성\n• "날짜 설정" - 과거 기간 보고서\n\n💬 자연어로 질문하면 일일보고서를 검색해 답변합니다!');
  
  // 이벤트 리스너
  sendBtn.addEventListener('click', handleSendMessage);
  reportInput.addEventListener('keydown', handleInputKeydown);
  
  // 날짜 설정 버튼
  const applyDateBtn = document.getElementById('apply-date-btn');
  const closeDateBtn = document.getElementById('close-date-btn');
  
  if (applyDateBtn) applyDateBtn.addEventListener('click', handleApplyDate);
  if (closeDateBtn) closeDateBtn.addEventListener('click', () => {
    dateSettingsPanel.style.display = 'none';
  });
  
  isInitialized = true;
  console.log('✅ 보고서 패널 초기화 완료');
}

/**
 * 메시지 추가
 */
function addMessage(role, content) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;
  
  // 구조화된 메시지 처리 (보고서 링크)
  if (typeof content === 'object' && content.type) {
    messageDiv.innerHTML = formatStructuredMessage(content);
  } else {
    messageDiv.textContent = content;
  }
  
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  messages.push({ role, content });
}

/**
 * 구조화된 메시지 포맷팅 (보고서 링크)
 */
function formatStructuredMessage(data) {
  const { type, message, period, report_data } = data;
  
  let html = `<div class="report-message">`;
  html += `<div class="report-text">${message}</div>`;
  
  if (period) {
    html += `<div class="report-period">📅 ${period.start || ''} ~ ${period.end || ''}</div>`;
  }
  
  if (report_data && report_data.html_url) {
    html += `<div class="report-link">`;
    html += `<a href="${report_data.html_url}" target="_blank" class="report-btn">`;
    html += `📄 ${report_data.file_name || '보고서 보기'}`;
    html += `</a>`;
    html += `</div>`;
  }
  
  html += `</div>`;
  return html;
}

/**
 * 입력 키 이벤트
 */
function handleInputKeydown(e) {
  if (e.isComposing || e.keyCode === 229) return;
  
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
}

/**
 * 메시지 전송
 */
async function handleSendMessage() {
  const text = reportInput.value.trim();
  if (!text || sendBtn.disabled) return;
  
  addMessage('user', text);
  reportInput.value = '';
  
  sendBtn.disabled = true;
  sendBtn.textContent = '...';
  
  try {
    if (chatMode === 'daily_fsm') {
      await handleDailyAnswer(text);
    } else {
      await handleReportIntent(text);
    }
  } catch (error) {
    console.error('메시지 처리 오류:', error);
    addMessage('assistant', '오류가 발생했습니다. 😢');
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = '전송';
  }
}

/**
 * Intent 처리
 */
async function handleReportIntent(text) {
  const lower = text.toLowerCase().trim();
  
  // 날짜 설정
  if (lower.includes('날짜') && lower.includes('설정')) {
    showDateSettings();
    return;
  }
  
  // 업무 플래닝
  if (lower.includes('플래닝') || lower.includes('추천') || lower.includes('할일')) {
    await getTodayPlan();
    return;
  }
  
  // 일일 보고서
  if (lower.includes('일일') && lower.includes('보고서')) {
    await startDailyReport();
    return;
  }
  
  // 주간 보고서
  if (lower.includes('주간') && lower.includes('보고서')) {
    await generateWeeklyReport();
    return;
  }
  
  // 월간 보고서
  if (lower.includes('월간') && lower.includes('보고서')) {
    await generateMonthlyReport();
    return;
  }
  
  // RAG 챗봇
  await handleRAGChat(text);
}

/**
 * 업무 플래닝
 */
async function getTodayPlan() {
  try {
    addMessage('assistant', '📋 오늘의 업무 플래닝을 생성 중입니다...');
    
    const response = await fetch(`${API_BASE}/plan/today`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: dailyOwner,
        target_date: new Date().toISOString().split('T')[0]
      })
    });
    
    if (!response.ok) throw new Error(`API 오류: ${response.status}`);
    
    const data = await response.json();
    
    // 요약 메시지
    addMessage('assistant', data.summary || '오늘의 업무 플래닝입니다!');
    
    // 업무 카드 표시
    if (data.tasks && data.tasks.length > 0) {
      displayTaskCards(data.tasks, data.owner, data.target_date);
    }
  } catch (error) {
    console.error('업무 플래닝 오류:', error);
    addMessage('assistant', '업무 플래닝 생성 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 업무 카드 표시
 */
function displayTaskCards(tasks, owner, targetDate) {
  currentRecommendation = { owner, target_date: targetDate, tasks };
  
  const container = document.createElement('div');
  container.className = 'task-recommendations-container';
  
  tasks.forEach((task, index) => {
    const card = document.createElement('div');
    card.className = 'task-card';
    card.innerHTML = `
      <div class="task-header">
        <span class="priority-badge priority-${task.priority}">${getPriorityText(task.priority)}</span>
        <span class="task-category">${task.category || '기타'}</span>
      </div>
      <div class="task-title">${task.title}</div>
      <div class="task-desc">${task.description}</div>
      <div class="task-time">${task.expected_time}</div>
      <button class="task-select-btn" data-index="${index}">선택</button>
    `;
    
    const selectBtn = card.querySelector('.task-select-btn');
    selectBtn.addEventListener('click', () => toggleTaskSelection(index, selectBtn));
    
    container.appendChild(card);
  });
  
  // 완료 버튼
  const saveBtn = document.createElement('button');
  saveBtn.className = 'task-save-button';
  saveBtn.textContent = '선택 완료';
  saveBtn.disabled = true;
  saveBtn.addEventListener('click', handleSaveTasks);
  container.appendChild(saveBtn);
  
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant no-bubble';
  messageDiv.appendChild(container);
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function getPriorityText(priority) {
  return { high: '높음', medium: '보통', low: '낮음' }[priority] || '보통';
}

function toggleTaskSelection(index, btn) {
  if (selectedTasks.has(index)) {
    selectedTasks.delete(index);
    btn.classList.remove('selected');
    btn.textContent = '선택';
  } else {
    selectedTasks.add(index);
    btn.classList.add('selected');
    btn.textContent = '✓ 선택됨';
  }
  
  // 완료 버튼 활성화
  const saveBtn = btn.closest('.task-recommendations-container').querySelector('.task-save-button');
  if (saveBtn) {
    saveBtn.disabled = selectedTasks.size === 0;
  }
}

async function handleSaveTasks() {
  if (!currentRecommendation) return;
  
  const selected = Array.from(selectedTasks).map(i => currentRecommendation.tasks[i]);
  
  try {
    const response = await fetch(`${API_BASE}/daily/select_main_tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: currentRecommendation.owner,
        target_date: currentRecommendation.target_date,
        selected_tasks: selected
      })
    });
    
    if (!response.ok) throw new Error('저장 실패');
    
    addMessage('assistant', `✅ ${selected.length}개 업무가 금일 계획으로 저장되었습니다!`);
    selectedTasks.clear();
  } catch (error) {
    addMessage('assistant', '업무 저장 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 일일 보고서 시작
 */
async function startDailyReport() {
  try {
    const targetDate = customDates.daily || new Date().toISOString().split('T')[0];
    
    const response = await fetch(`${API_BASE}/daily/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner: dailyOwner, target_date: targetDate })
    });
    
    if (!response.ok) {
      const error = await response.json();
      if (error.detail && error.detail.includes('금일 업무 계획')) {
        addMessage('assistant', '⚠️ 금일 업무 계획이 없습니다. 먼저 "오늘 업무 플래닝"을 해주세요!');
        return;
      }
      throw new Error('API 오류');
    }
    
    const result = await response.json();
    chatMode = 'daily_fsm';
    dailySessionId = result.session_id;
    reportInput.placeholder = '업무 내용을 입력하세요...';
    addMessage('assistant', result.question);
  } catch (error) {
    addMessage('assistant', '일일 보고서 시작 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 일일 보고서 답변
 */
async function handleDailyAnswer(answer) {
  try {
    const response = await fetch(`${API_BASE}/daily/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: dailySessionId, answer })
    });
    
    if (!response.ok) throw new Error('API 오류');
    
    const result = await response.json();
    
    if (result.status === 'finished') {
      addMessage('assistant', result.message || '일일 보고서가 완료되었습니다! 🙌');
      
      // 보고서 링크 표시
      if (result.report_data) {
        addMessage('assistant', {
          type: 'daily_report',
          message: '보고서가 생성되었습니다!',
          period: result.period,
          report_data: result.report_data
        });
      }
      
      chatMode = 'normal';
      dailySessionId = null;
      reportInput.placeholder = '메시지를 입력하세요...';
    } else {
      addMessage('assistant', result.question);
    }
  } catch (error) {
    addMessage('assistant', '답변 처리 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 주간 보고서 생성
 */
async function generateWeeklyReport() {
  try {
    addMessage('assistant', '📊 주간 보고서를 생성 중입니다...');
    
    const targetDate = customDates.weekly || new Date().toISOString().split('T')[0];
    
    const response = await fetch(`${API_BASE}/weekly/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner: dailyOwner, target_date: targetDate })
    });
    
    if (!response.ok) throw new Error('API 오류');
    
    const data = await response.json();
    
    addMessage('assistant', {
      type: 'weekly_report',
      message: data.message || '주간 보고서가 생성되었습니다!',
      period: data.period,
      report_data: data.report_data
    });
  } catch (error) {
    addMessage('assistant', '주간 보고서 생성 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 월간 보고서 생성
 */
async function generateMonthlyReport() {
  try {
    addMessage('assistant', '📈 월간 보고서를 생성 중입니다...');
    
    const now = new Date();
    const year = customDates.monthly.year || now.getFullYear();
    const month = customDates.monthly.month || (now.getMonth() + 1);
    
    const response = await fetch(`${API_BASE}/monthly/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner: dailyOwner, year, month })
    });
    
    if (!response.ok) throw new Error('API 오류');
    
    const data = await response.json();
    
    addMessage('assistant', {
      type: 'monthly_report',
      message: data.message || '월간 보고서가 생성되었습니다!',
      period: data.period,
      report_data: data.report_data
    });
  } catch (error) {
    addMessage('assistant', '월간 보고서 생성 중 오류가 발생했습니다. 😢');
  }
}

/**
 * RAG 챗봇
 */
async function handleRAGChat(query) {
  try {
    addMessage('assistant', '🔍 일일보고서를 검색 중입니다...');
    
    const response = await fetch(`${API_BASE}/report-chat/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner: dailyOwner, query })
    });
    
    if (!response.ok) throw new Error('API 오류');
    
    const data = await response.json();
    
    // 마지막 메시지 제거 (검색 중...)
    if (messagesContainer.lastChild) {
      messagesContainer.removeChild(messagesContainer.lastChild);
      messages.pop();
    }
    
    addMessage('assistant', data.answer);
  } catch (error) {
    addMessage('assistant', '검색 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 날짜 설정 패널 표시
 */
function showDateSettings() {
  if (!dateSettingsPanel) return;
  
  // 모든 날짜 입력 숨기기
  document.querySelectorAll('.date-input-group').forEach(el => el.style.display = 'none');
  
  addMessage('assistant', '어떤 보고서의 날짜를 설정하시겠습니까?\n\n• 일일 보고서\n• 주간 보고서\n• 월간 보고서');
  
  // 다음 메시지에서 보고서 타입 감지
}

function handleApplyDate() {
  const dailyDate = document.getElementById('daily-target-date')?.value;
  const weeklyDate = document.getElementById('weekly-target-date')?.value;
  const monthlyYear = document.getElementById('monthly-year')?.value;
  const monthlyMonth = document.getElementById('monthly-month')?.value;
  
  if (dailyDate) customDates.daily = dailyDate;
  if (weeklyDate) customDates.weekly = weeklyDate;
  if (monthlyYear && monthlyMonth) {
    customDates.monthly = { year: parseInt(monthlyYear), month: parseInt(monthlyMonth) };
  }
  
  dateSettingsPanel.style.display = 'none';
  addMessage('assistant', '✅ 날짜가 설정되었습니다!');
}

/**
 * 세션 데이터 가져오기 (Electron에서 호출)
 */
export function getReportSessionData() {
  return {
    chatMode,
    dailySessionId,
    dailyOwner,
    messages: messages.slice(-10) // 최근 10개만
  };
}

