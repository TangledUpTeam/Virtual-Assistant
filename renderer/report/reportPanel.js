/**
 * 보고서 & 추천 업무 통합 UI
 * 일일/주간/월간/실적 보고서 + 추천 업무
 * 
 * 단축키: Ctrl+Shift+R
 */

import { getTodayPlan as getTodayPlanFromService } from './taskService.js';
import { addTaskRecommendations as addTaskRecommendationsFromUI, showCustomTaskInput as showCustomTaskInputFromUI } from './taskUI.js';

const API_BASE = 'http://localhost:8000/api/v1';

let messages = [];
let isPanelVisible = false;
let reportPanel = null;
let messagesContainer = null;
let reportInput = null;
let sendBtn = null;
let isReportPanelInitialized = false;

// FSM 상태
let chatMode = 'normal'; // 'normal' 또는 'daily_fsm'
let dailySessionId = null;
let dailyOwner = '김보험';

// 🔥 금일 업무 저장 여부 추적 (첫 저장 이후는 append)
let hasMainTasksSaved = false;

// 🔥 날짜 설정
let dateSettingsPanel = null;
let currentReportType = null; // 'daily', 'weekly', 'monthly', 'yearly'
let customDates = {
  daily: null,
  weekly: null,
  monthly: { year: null, month: null },
  yearly: null
};

/**
 * 보고서 패널 초기화
 */
export function initReportPanel() {
  if (isReportPanelInitialized) {
    console.log('⚠️  보고서 패널 이미 초기화됨 - 스킵');
    return;
  }
  
  console.log('📝 보고서 패널 초기화 중...');
  
  reportPanel = document.getElementById('report-panel');
  messagesContainer = document.getElementById('report-messages');
  reportInput = document.getElementById('report-input');
  sendBtn = document.getElementById('report-send-btn');
  
  if (!reportPanel || !messagesContainer || !reportInput || !sendBtn) {
    console.error('❌ 보고서 패널 요소를 찾을 수 없습니다.');
    console.error('reportPanel:', reportPanel);
    console.error('messagesContainer:', messagesContainer);
    console.error('reportInput:', reportInput);
    console.error('sendBtn:', sendBtn);
    return;
  }
  
  // 🔥 강제로 스타일 적용 (최우선)
  reportPanel.style.setProperty('pointer-events', 'auto', 'important');
  reportPanel.style.setProperty('z-index', '9998', 'important');
  reportInput.style.setProperty('pointer-events', 'auto', 'important');
  reportInput.style.setProperty('cursor', 'text', 'important');
  sendBtn.style.setProperty('pointer-events', 'auto', 'important');
  sendBtn.style.setProperty('cursor', 'pointer', 'important');
  
  // 입력 영역도 강제 적용
  const inputArea = document.getElementById('report-input-area');
  if (inputArea) {
    inputArea.style.setProperty('pointer-events', 'auto', 'important');
  }
  
  console.log('🎨 reportPanel 스타일:', {
    pointerEvents: window.getComputedStyle(reportPanel).pointerEvents,
    zIndex: window.getComputedStyle(reportPanel).zIndex,
    display: window.getComputedStyle(reportPanel).display
  });
  
  console.log('🎨 reportInput 스타일:', {
    pointerEvents: window.getComputedStyle(reportInput).pointerEvents,
    cursor: window.getComputedStyle(reportInput).cursor
  });
  
  // 날짜 설정 패널 요소 가져오기
  dateSettingsPanel = document.getElementById('date-settings-panel');
  const applyDateBtn = document.getElementById('apply-date-btn');
  const closeDateBtn = document.getElementById('close-date-btn');
  
  if (applyDateBtn) {
    applyDateBtn.addEventListener('click', handleApplyDate);
  }
  if (closeDateBtn) {
    closeDateBtn.addEventListener('click', () => {
      dateSettingsPanel.style.display = 'none';
    });
  }
  
  // 초기 메시지 추가
  addMessage('assistant', '📝 보고서 & 업무 관리를 도와드립니다!\n\n• "오늘 추천 업무" - 업무 추천\n• "일일 보고서" - 일일 보고서 작성\n• "주간 보고서" - 주간 보고서 생성\n• "월간 보고서" - 월간 보고서 생성\n• "실적 보고서" - 연간 실적 보고서 생성\n• "날짜 설정" - 과거 기간 보고서 작성');
  
  // 이벤트 리스너 등록
  sendBtn.addEventListener('click', () => {
    console.log('🖱️ 전송 버튼 클릭됨!');
    handleSendMessage();
  });
  reportInput.addEventListener('keydown', handleReportInputKeydown);
  reportInput.addEventListener('click', () => {
    console.log('🖱️ 입력창 클릭됨!');
  });
  reportInput.addEventListener('focus', () => {
    console.log('✨ 입력창 포커스됨!');
  });
  window.addEventListener('keydown', handleReportGlobalKeydown);
  
  isReportPanelInitialized = true;
  
  console.log('✅ 보고서 패널 초기화 완료');
}

// 전역으로 export
window.initReportPanel = initReportPanel;
window.addReportMessage = addMessage;

/**
 * 입력창 키 이벤트
 */
function handleReportInputKeydown(e) {
  if (e.isComposing || e.keyCode === 229) {
    return;
  }
  
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
}

/**
 * 전역 키 이벤트 (Ctrl+Shift+R로 토글)
 */
function handleReportGlobalKeydown(e) {
  // Ctrl+Shift+R (대소문자 모두 처리)
  if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'R' || e.key === 'r')) {
    // 메인 창에서만 작동하도록 (DevTools 새로고침 방지)
    if (e.target.ownerDocument === document) {
      e.preventDefault();
      e.stopPropagation();
      console.log('🔑 Ctrl+Shift+R 감지 → 보고서 패널 토글');
      togglePanel();
    }
  }
}

/**
 * 메시지 전송 처리
 */
async function handleSendMessage() {
  const text = reportInput.value.trim();
  if (!text) return;
  
  if (sendBtn.disabled) {
    console.log('⚠️  이미 전송 중...');
    return;
  }
  
  addMessage('user', text);
  
  reportInput.value = '';
  reportInput.blur();
  setTimeout(() => reportInput.focus(), 0);
  
  sendBtn.disabled = true;
  sendBtn.textContent = '...';
  
  try {
    // FSM 모드 체크
    if (chatMode === 'daily_fsm') {
      // 일일 보고서 FSM 답변 처리
      await handleDailyAnswer(text);
    } else {
      // 일반 모드 - Intent 분석
      await handleReportIntent(text);
    }
  } catch (error) {
    console.error('❌ 보고서 오류:', error);
    addMessage('assistant', '죄송합니다. 오류가 발생했습니다. 😢');
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = '전송';
  }
}

/**
 * 보고서 & 업무 Intent 처리
 */
async function handleReportIntent(text) {
  const lower = text.toLowerCase().trim();
  
  // 🔥 날짜 설정 요청
  if (lower.includes('날짜') && (lower.includes('설정') || lower.includes('변경'))) {
    showDateSettings();
    return;
  }
  
  // 추천 업무
  if (isTaskRecommendationIntent(lower)) {
    await handleTaskRecommendation();
    return;
  }
  
  // 일일 보고서
  if (isDailyReportTrigger(lower)) {
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
  
  // 실적 보고서
  if ((lower.includes('실적') || lower.includes('연간')) && lower.includes('보고서')) {
    await generateYearlyReport();
    return;
  }
  
  // 일반 응답
  addMessage('assistant', '무엇을 도와드릴까요?\n\n• "오늘 추천 업무"\n• "일일 보고서"\n• "주간 보고서"\n• "월간 보고서"\n• "실적 보고서"\n• "날짜 설정"');
}

/**
 * 추천 업무 Intent 감지
 */
function isTaskRecommendationIntent(text) {
  const keywords = ['추천', '뭐할', '뭐해', '업무', '할일', 'todo', 'task'];
  const triggerWords = ['추천', '뭐할', '계획'];
  
  return keywords.some(kw => text.includes(kw)) && 
         triggerWords.some(tw => text.includes(tw));
}

/**
 * 일일 보고서 트리거 감지
 */
function isDailyReportTrigger(text) {
  return (text.includes('일일') || text.includes('데일리') || text.includes('daily')) &&
         (text.includes('보고서') || text.includes('작성') || text.includes('리포트'));
}

/**
 * 일일 보고서 FSM 시작
 */
async function startDailyReport() {
  console.log('📝 일일 보고서 FSM 시작...');
  
  try {
    // 🔥 사용자 지정 날짜 또는 오늘 날짜
    const targetDate = customDates.daily || new Date().toISOString().split('T')[0];
    
    // 🔥 일일 보고서 시작 시 상태 초기화 (새로운 날 시작)
    hasMainTasksSaved = false;
    
    const response = await fetch(`${API_BASE}/daily/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: dailyOwner,
        target_date: targetDate
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ FSM 시작 완료:', result);
    
    // FSM 모드로 전환
    chatMode = 'daily_fsm';
    dailySessionId = result.session_id;
    
    // Placeholder 변경
    if (reportInput) {
      reportInput.placeholder = '해당 시간대에 했던 업무를 자유롭게 적어주세요...';
    }
    
    // 첫 질문 출력
    addMessage('assistant', result.question);
    
  } catch (error) {
    console.error('❌ FSM 시작 오류:', error);
    addMessage('assistant', '일일 보고서를 시작하는 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 일일 보고서 FSM 답변 처리
 */
async function handleDailyAnswer(answer) {
  console.log('📝 FSM 답변 전송:', answer);
  
  try {
    const response = await fetch(`${API_BASE}/daily/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: dailySessionId,
        answer: answer
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ FSM 답변 처리 완료:', result);
    
    if (result.status === 'finished') {
      // 완료 처리
      addMessage('assistant', result.message || '일일 보고서 작성이 완료되었습니다! 🙌');
      
      // 보고서 요약 출력
      if (result.report && result.report.tasks) {
        addReportSummary(result.report);
      }
      
      // PDF 저장 안내
      const reportDate = result.report?.period_start || new Date().toISOString().split('T')[0];
      addMessage('assistant', `📄 PDF 파일이 output/report_result/daily/${dailyOwner}_${reportDate}_일일보고서.pdf 에 저장되었습니다!`);
      
      // 모드 초기화
      chatMode = 'normal';
      dailySessionId = null;
      hasMainTasksSaved = false; // 🔥 다음 날을 위해 초기화
      if (reportInput) {
        reportInput.placeholder = '메시지를 입력하세요...';
      }
      
    } else {
      // 다음 질문 출력
      addMessage('assistant', result.question);
    }
    
  } catch (error) {
    console.error('❌ FSM 답변 오류:', error);
    addMessage('assistant', '답변 처리 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 보고서 요약 출력
 */
function addReportSummary(report) {
  const summaryLines = [];
  
  // 📋 예정 업무
  if (report.plans && report.plans.length > 0) {
    summaryLines.push('📋 오늘 예정했던 업무:');
    report.plans.forEach((plan, index) => {
      summaryLines.push(`  ${index + 1}. ${plan}`);
    });
    summaryLines.push('');
  }
  
  // ✅ 실제 완료 업무
  if (report.tasks && report.tasks.length > 0) {
    summaryLines.push('✅ 실제 완료한 업무:');
    const tasks = report.tasks.slice(0, 5);
    tasks.forEach((task, index) => {
      const timeInfo = task.time_start && task.time_end ? ` (${task.time_start}~${task.time_end})` : '';
      summaryLines.push(`  ${index + 1}. ${task.title}${timeInfo}`);
    });
    if (report.tasks.length > 5) {
      summaryLines.push(`  ... 외 ${report.tasks.length - 5}개 업무`);
    }
    summaryLines.push('');
  }
  
  // ⚠️ 미종결 업무
  if (report.issues && report.issues.length > 0) {
    summaryLines.push('⚠️ 미종결 업무:');
    report.issues.forEach((issue, index) => {
      summaryLines.push(`  ${index + 1}. ${issue}`);
    });
    summaryLines.push('');
  }
  
  // 📈 완료율
  const metadata = report.metadata || {};
  if (metadata.completion_rate) {
    summaryLines.push(`📈 예정 업무 완료율: ${metadata.completion_rate}`);
  }
  
  const summaryText = summaryLines.join('\n');
  addMessage('assistant', summaryText);
}

/**
 * 주간 보고서 생성
 */
async function generateWeeklyReport() {
  try {
    addMessage('assistant', '📊 주간 보고서를 생성 중입니다...');
    
    // 🔥 사용자 지정 날짜 또는 이번 주 월요일
    const targetDate = customDates.weekly || getMonday(new Date());
    
    const response = await fetch(`${API_BASE}/weekly/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: dailyOwner,
        target_date: targetDate
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    const report = data.report || {};
    const startDate = report.period_start || 'N/A';
    const endDate = report.period_end || 'N/A';
    const totalTasks = report.tasks?.length || 0;
    
    addMessage('assistant', `✅ 주간 보고서가 생성되었습니다!\n\n기간: ${startDate} ~ ${endDate}\n완료 업무: ${totalTasks}개\n\n📄 PDF 파일이 output/report_result/weekly/ 에 저장되었습니다!`);
  } catch (error) {
    console.error('❌ 주간 보고서 생성 실패:', error);
    addMessage('assistant', '주간 보고서 생성 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 월간 보고서 생성
 */
async function generateMonthlyReport() {
  try {
    addMessage('assistant', '📈 월간 보고서를 생성 중입니다...');
    
    // 🔥 사용자 지정 년월 또는 현재 년월
    const now = new Date();
    const year = customDates.monthly.year || now.getFullYear();
    const month = customDates.monthly.month || (now.getMonth() + 1);
    
    const response = await fetch(`${API_BASE}/monthly/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: dailyOwner,
        year: year,
        month: month
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    const report = data.report || {};
    const totalTasks = report.tasks?.length || 0;
    
    addMessage('assistant', `✅ 월간 보고서가 생성되었습니다!\n\n기간: ${year}년 ${month}월\n완료 업무: ${totalTasks}개\n\n📄 PDF 파일이 output/report_result/monthly/ 에 저장되었습니다!`);
  } catch (error) {
    console.error('❌ 월간 보고서 생성 실패:', error);
    addMessage('assistant', '월간 보고서 생성 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 실적 보고서 생성
 */
async function generateYearlyReport() {
  try {
    addMessage('assistant', '📋 실적 보고서를 생성 중입니다...');
    
    // 🔥 사용자 지정 연도 또는 올해
    const year = customDates.yearly || new Date().getFullYear();
    
    const response = await fetch(`${API_BASE}/performance/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: dailyOwner,
        year: year
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    const report = data.report || {};
    const totalTasks = report.tasks?.length || 0;
    
    addMessage('assistant', `✅ ${year}년 실적 보고서가 생성되었습니다!\n\n총 업무: ${totalTasks}개\n\n📄 PDF 파일이 output/report_result/performance/ 에 저장되었습니다!`);
  } catch (error) {
    console.error('❌ 실적 보고서 생성 실패:', error);
    addMessage('assistant', '실적 보고서 생성 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 메시지 추가
 */
function addMessage(role, text) {
  messages.push({ role, text });
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;
  
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  
  messageDiv.appendChild(bubble);
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  console.log(`📝 [${role}]: ${text.substring(0, 50)}${text.length > 50 ? '...' : ''}`);
}

/**
 * 패널 토글
 */
function togglePanel() {
  isPanelVisible = !isPanelVisible;
  
  if (isPanelVisible) {
    reportPanel.style.display = 'flex';
    reportPanel.style.setProperty('pointer-events', 'auto', 'important');
    reportPanel.style.setProperty('z-index', '9998', 'important');
    reportInput.style.setProperty('pointer-events', 'auto', 'important');
    sendBtn.style.setProperty('pointer-events', 'auto', 'important');
    reportPanel.classList.add('visible');
    document.body.classList.add('report-panel-active');
    console.log('👁️ 보고서 패널 표시');
    
    console.log('🔍 패널 열린 후 스타일:', {
      display: window.getComputedStyle(reportPanel).display,
      pointerEvents: window.getComputedStyle(reportPanel).pointerEvents,
      zIndex: window.getComputedStyle(reportPanel).zIndex,
      position: window.getComputedStyle(reportPanel).position
    });
    
    console.log('🔍 입력창 스타일:', {
      pointerEvents: window.getComputedStyle(reportInput).pointerEvents,
      cursor: window.getComputedStyle(reportInput).cursor,
      display: window.getComputedStyle(reportInput).display
    });
    
    // 입력창에 포커스
    setTimeout(() => {
      if (reportInput) {
        reportInput.focus();
        console.log('⌨️ 입력창 포커스 시도 완료');
      }
    }, 100);
  } else {
    reportPanel.style.display = 'none';
    reportPanel.classList.remove('visible');
    document.body.classList.remove('report-panel-active'); // 🔥 body에서 클래스 제거
    console.log('🙈 보고서 패널 숨김');
  }
}

/**
 * 오늘의 추천 업무 가져오기 (taskService.js 사용)
 */
async function handleTaskRecommendation() {
  try {
    addMessage('assistant', '📋 오늘의 추천 업무를 가져오는 중입니다...');
    
    // 🔥 사용자 지정 날짜 또는 오늘 날짜
    const targetDate = customDates.daily || new Date().toISOString().split('T')[0];
    
    // taskService.js의 getTodayPlan 사용
    const result = await getTodayPlanFromService();
    
    if (result.type === 'error') {
      addMessage('assistant', result.data);
      return;
    }
    
    if (result.type === 'task_recommendations') {
      const { tasks, summary, owner, target_date } = result.data;
      
      if (tasks.length === 0) {
        addMessage('assistant', '추천할 업무가 없습니다. "직접 작성하기"를 이용해주세요! 😊');
      }
      
      // taskUI.js의 addTaskRecommendations 사용
      addTaskRecommendationsFromUI({
        tasks: tasks,
        summary: summary,
        owner: owner,
        target_date: target_date
      }, addMessage, messagesContainer);
    }
  } catch (error) {
    console.error('❌ 추천 업무 가져오기 실패:', error);
    addMessage('assistant', '추천 업무를 가져오는데 실패했습니다. 😢');
  }
}

/**
 * 직접 작성하기 모달 표시 (보고서 패널 전용 - taskUI.js 래핑)
 */
function showCustomTaskInput(owner, targetDate) {
  // taskUI.js의 함수를 사용하되, 보고서 패널의 addMessage 전달
  showCustomTaskInputFromUI(owner, targetDate, addMessage);
  
  // 저장 후 추가 기능 처리 (showSavedTasksConfirmation)는
  // taskUI.js 내부에서 처리되므로 여기서는 호출만 함
}

/**
 * 저장된 업무 확인 UI 표시
 */
async function showSavedTasksConfirmation(owner, targetDate) {
  try {
    // 저장된 업무 조회
    const response = await fetch(`${API_BASE}/daily/get_main_tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: owner,
        target_date: targetDate
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }
    
    const data = await response.json();
    const tasks = data.main_tasks || [];
    
    if (tasks.length === 0) {
      return;
    }
    
    // 확인 메시지 생성
    let confirmMessage = '📋 **금일 진행 업무 확인**\n\n';
    tasks.forEach((task, index) => {
      confirmMessage += `${index + 1}. ${task.title}\n`;
    });
    confirmMessage += `\n총 ${tasks.length}개의 업무가 등록되었습니다.\n맞으신가요?`;
    
    // 확인 UI 추가
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.style.whiteSpace = 'pre-wrap';
    bubble.textContent = confirmMessage;
    
    messageDiv.appendChild(bubble);
    
    // 버튼 컨테이너
    const btnContainer = document.createElement('div');
    btnContainer.style.cssText = 'display: flex; gap: 8px; margin-top: 12px; justify-content: center;';
    
    // "네, 맞습니다" 버튼
    const confirmBtn = document.createElement('button');
    confirmBtn.textContent = '✅ 네, 맞습니다';
    confirmBtn.style.cssText = `
      padding: 10px 20px;
      border: none;
      border-radius: 8px;
      background: linear-gradient(135deg, rgba(100, 200, 100, 0.9), rgba(80, 180, 80, 0.9));
      color: white;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    `;
    confirmBtn.addEventListener('click', () => {
      addMessage('assistant', '✅ 확인되었습니다! 일일 보고서 작성 시 이 업무들을 기준으로 진행됩니다.');
      btnContainer.remove();
    });
    
    // "추가 입력" 버튼
    const addMoreBtn = document.createElement('button');
    addMoreBtn.textContent = '➕ 업무 추가';
    addMoreBtn.style.cssText = `
      padding: 10px 20px;
      border: 2px solid rgba(100, 150, 255, 0.6);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.95);
      color: rgba(100, 150, 255, 0.9);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    `;
    addMoreBtn.addEventListener('click', () => {
      showCustomTaskInput(owner, targetDate);
      btnContainer.remove();
    });
    
    // "수정" 버튼
    const editBtn = document.createElement('button');
    editBtn.textContent = '✏️ 수정';
    editBtn.style.cssText = `
      padding: 10px 20px;
      border: 2px solid rgba(255, 150, 100, 0.6);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.95);
      color: rgba(255, 150, 100, 0.9);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    `;
    editBtn.addEventListener('click', () => {
      showEditMainTasksUI(owner, targetDate, tasks);
      btnContainer.remove();
    });
    
    btnContainer.appendChild(confirmBtn);
    btnContainer.appendChild(addMoreBtn);
    btnContainer.appendChild(editBtn);
    
    messageDiv.appendChild(btnContainer);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
  } catch (error) {
    console.error('❌ 업무 확인 오류:', error);
  }
}

/**
 * 금일 진행 업무 수정 UI 표시
 */
async function showEditMainTasksUI(owner, targetDate, currentTasks) {
  try {
    addMessage('assistant', '✏️ **업무 수정 모드**\n\n각 업무를 수정하거나 삭제할 수 있습니다.');
    
    // 수정 UI 컨테이너
    const editContainer = document.createElement('div');
    editContainer.className = 'message assistant';
    editContainer.style.cssText = 'width: 100%;';
    
    const editBubble = document.createElement('div');
    editBubble.className = 'bubble';
    editBubble.style.cssText = 'padding: 20px; background: rgba(255, 255, 255, 0.98);';
    
    // 업무 목록 (수정 가능)
    const tasksContainer = document.createElement('div');
    tasksContainer.style.cssText = 'display: flex; flex-direction: column; gap: 12px;';
    
    // 각 업무에 대한 입력 필드
    currentTasks.forEach((task, index) => {
      const taskRow = document.createElement('div');
      taskRow.style.cssText = `
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px;
        background: rgba(240, 240, 250, 0.5);
        border-radius: 8px;
      `;
      taskRow.dataset.taskIndex = index;
      
      // 번호
      const numberSpan = document.createElement('span');
      numberSpan.textContent = `${index + 1}.`;
      numberSpan.style.cssText = 'font-weight: 600; color: #666; min-width: 25px;';
      
      // 입력 필드
      const input = document.createElement('input');
      input.type = 'text';
      input.value = task.title;
      input.style.cssText = `
        flex: 1;
        padding: 8px 12px;
        border: 2px solid rgba(100, 150, 255, 0.3);
        border-radius: 6px;
        font-size: 14px;
        background: white;
      `;
      input.placeholder = '업무 내용을 입력하세요';
      
      // 삭제 버튼
      const deleteBtn = document.createElement('button');
      deleteBtn.textContent = '🗑️';
      deleteBtn.style.cssText = `
        padding: 8px 12px;
        border: none;
        border-radius: 6px;
        background: rgba(255, 100, 100, 0.1);
        color: rgba(255, 100, 100, 0.9);
        cursor: pointer;
        font-size: 16px;
      `;
      deleteBtn.addEventListener('click', () => {
        taskRow.remove();
      });
      
      taskRow.appendChild(numberSpan);
      taskRow.appendChild(input);
      taskRow.appendChild(deleteBtn);
      tasksContainer.appendChild(taskRow);
    });
    
    editBubble.appendChild(tasksContainer);
    
    // 버튼 컨테이너
    const btnContainer = document.createElement('div');
    btnContainer.style.cssText = 'display: flex; gap: 8px; margin-top: 16px; justify-content: center;';
    
    // 저장 버튼
    const saveBtn = document.createElement('button');
    saveBtn.textContent = '💾 저장';
    saveBtn.style.cssText = `
      padding: 10px 20px;
      border: none;
      border-radius: 8px;
      background: linear-gradient(135deg, rgba(100, 200, 100, 0.9), rgba(80, 180, 80, 0.9));
      color: white;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    `;
    saveBtn.addEventListener('click', async () => {
      // 모든 입력 필드에서 값 수집
      const updatedTasks = [];
      const inputs = tasksContainer.querySelectorAll('input');
      
      inputs.forEach((input) => {
        const value = input.value.trim();
        if (value) {
          updatedTasks.push({ title: value });
        }
      });
      
      if (updatedTasks.length === 0) {
        addMessage('assistant', '❌ 최소 1개 이상의 업무가 필요합니다!');
        return;
      }
      
      // 백엔드 업데이트 호출
      addMessage('user', '수정된 업무를 저장합니다...');
      
      try {
        const response = await fetch(`${API_BASE}/daily/update_main_tasks`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            owner: owner,
            target_date: targetDate,
            main_tasks: updatedTasks
          })
        });
        
        if (!response.ok) {
          throw new Error(`API 오류: ${response.status}`);
        }
        
        const data = await response.json();
        addMessage('assistant', `✅ ${updatedTasks.length}개의 업무가 수정되었습니다!`);
        editContainer.remove();
        
        // 수정된 업무 다시 확인
        await showSavedTasksConfirmation(owner, targetDate);
        
      } catch (error) {
        console.error('❌ 업무 수정 실패:', error);
        addMessage('assistant', `❌ 업무 수정 실패: ${error.message}`);
      }
    });
    
    // 취소 버튼
    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = '❌ 취소';
    cancelBtn.style.cssText = `
      padding: 10px 20px;
      border: 2px solid rgba(150, 150, 150, 0.6);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.95);
      color: rgba(150, 150, 150, 0.9);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    `;
    cancelBtn.addEventListener('click', () => {
      editContainer.remove();
      addMessage('assistant', '업무 수정이 취소되었습니다.');
    });
    
    btnContainer.appendChild(saveBtn);
    btnContainer.appendChild(cancelBtn);
    editBubble.appendChild(btnContainer);
    
    editContainer.appendChild(editBubble);
    messagesContainer.appendChild(editContainer);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
  } catch (error) {
    console.error('❌ 업무 수정 UI 오류:', error);
    addMessage('assistant', '❌ 업무 수정 UI 표시 중 오류가 발생했습니다.');
  }
}

/**
 * 날짜 설정 UI 표시
 */
function showDateSettings() {
  addMessage('assistant', '📅 날짜 설정 패널을 열었습니다!\n\n원하는 보고서 유형을 선택하고 날짜를 설정해주세요.');
  
  // 날짜 설정 패널 표시
  if (dateSettingsPanel) {
    dateSettingsPanel.style.display = 'block';
    
    // 오늘 날짜로 초기화
    const today = new Date().toISOString().split('T')[0];
    const now = new Date();
    
    const dailyDateInput = document.getElementById('daily-target-date');
    const weeklyDateInput = document.getElementById('weekly-target-date');
    const monthlyYear = document.getElementById('monthly-year');
    const monthlyMonth = document.getElementById('monthly-month');
    const yearlyYear = document.getElementById('yearly-year');
    
    if (dailyDateInput) dailyDateInput.value = today;
    if (weeklyDateInput) weeklyDateInput.value = today;
    if (monthlyYear) monthlyYear.value = now.getFullYear();
    if (monthlyMonth) monthlyMonth.value = now.getMonth() + 1;
    if (yearlyYear) yearlyYear.value = now.getFullYear();
    
    // 모든 입력 그룹 표시
    document.querySelectorAll('.date-input-group').forEach(group => {
      group.style.display = 'block';
    });
  }
}

/**
 * 날짜 설정 적용
 */
function handleApplyDate() {
  const dailyDate = document.getElementById('daily-target-date')?.value;
  const weeklyDate = document.getElementById('weekly-target-date')?.value;
  const monthlyYear = document.getElementById('monthly-year')?.value;
  const monthlyMonth = document.getElementById('monthly-month')?.value;
  const yearlyYear = document.getElementById('yearly-year')?.value;
  
  // 날짜 저장
  if (dailyDate) customDates.daily = dailyDate;
  if (weeklyDate) customDates.weekly = weeklyDate;
  if (monthlyYear && monthlyMonth) {
    customDates.monthly = { year: parseInt(monthlyYear), month: parseInt(monthlyMonth) };
  }
  if (yearlyYear) customDates.yearly = parseInt(yearlyYear);
  
  dateSettingsPanel.style.display = 'none';
  
  addMessage('assistant', `✅ 날짜 설정이 완료되었습니다!\n\n• 일일: ${customDates.daily || '오늘'}\n• 주간: ${customDates.weekly || '이번 주'}\n• 월간: ${customDates.monthly.year}년 ${customDates.monthly.month}월\n• 실적: ${customDates.yearly || '올해'}년\n\n이제 보고서를 작성하시면 설정된 날짜로 생성됩니다!`);
}

/**
 * 유틸: 이번 주 월요일 날짜
 */
function getMonday(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(d.setDate(diff));
  return monday.toISOString().split('T')[0];
}

