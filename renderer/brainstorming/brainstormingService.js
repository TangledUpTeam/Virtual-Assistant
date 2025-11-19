/**
 * 브레인스토밍 서비스
 * brainstorming.py API 연동
 */

const API_BASE = 'http://localhost:8000/api/v1/brainstorming';

// 🔥 전역으로 export (init()에서 호출)
window.initBrainstormingPanel = null;

// 패널 표시 상태
let isBsPanelVisible = false;

// 현재 세션 ID
let currentSessionId = null;

// 현재 단계
let currentStep = 'initial'; // initial, q1, q2, q3, ideas, complete

// Q3 누적 키워드 저장
let accumulatedKeywords = [];

// DOM 요소 참조
let bsPanel = null;
let bsContent = null;
let bsInput = null;
let bsSubmitBtn = null;

/**
 * 브레인스토밍 패널 초기화
 */
export function initBrainstormingPanel() {
  console.log('💡 브레인스토밍 패널 초기화 중...');
  
  bsPanel = document.getElementById('brainstorming-panel');
  bsContent = document.getElementById('bs-content');
  bsInput = document.getElementById('bs-input');
  bsSubmitBtn = document.getElementById('bs-submit-btn');
  
  if (!bsPanel || !bsContent || !bsInput || !bsSubmitBtn) {
    console.error('❌ 브레인스토밍 패널 요소를 찾을 수 없습니다.');
    return;
  }
  
  // 🔥 기존 내용 초기화
  bsContent.innerHTML = '';
  
  // 초기 메시지 표시
  showInitialBsMessage();
  
  // 이벤트 리스너 등록
  setupBsEventListeners();
  
  console.log('✅ 브레인스토밍 패널 초기화 완료');
}

// 🔥 전역으로 export
window.initBrainstormingPanel = initBrainstormingPanel;

/**
 * 이벤트 리스너 설정
 */
function setupBsEventListeners() {
  // 제출 버튼 클릭
  bsSubmitBtn.addEventListener('click', handleBsSubmit);
  
  // Enter 키로 전송 (한글 입력 중 방지)
  bsInput.addEventListener('keydown', (e) => {
    // 🔥 한글 입력 중(composing)이면 무시
    if (e.isComposing || e.keyCode === 229) {
      return;
    }
    
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleBsSubmit();
    }
  });
  
  // Cmd/Ctrl + Shift + B로 패널 토글
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'b') {
      e.preventDefault();
      toggleBsPanel();
    }
  });
}

/**
 * 초기 메시지 표시
 */
function showInitialBsMessage() {
  addBsMessage('system', '안녕하세요! 브레인스토밍을 시작하시겠습니까?');
  addBsMessage('system', '시작하려면 "시작" 또는 "start"를 입력하세요.');
  currentStep = 'initial';
}

/**
 * 제출 처리
 */
async function handleBsSubmit() {
  const text = bsInput.value.trim();
  
  if (!text) return;
  
  // 🔥 전송 중이면 무시 (중복 전송 방지)
  if (bsSubmitBtn.disabled) {
    console.log('⚠️  이미 전송 중...');
    return;
  }
  
  addBsMessage('user', text);
  
  // 🔥 입력창 초기화 (IME 문제 해결)
  bsInput.value = '';
  bsInput.blur(); // 포커스 제거
  setTimeout(() => {
    bsInput.focus(); // 다시 포커스
  }, 0);
  
  bsSubmitBtn.disabled = true;
  bsSubmitBtn.textContent = '...';
  
  try {
    switch (currentStep) {
      case 'initial':
        await handleBsInitial(text);
        break;
      case 'q1':
        await handleBsQ1(text);
        break;
      case 'q2':
        await handleBsQ2(text);
        break;
      case 'q3':
        await handleBsQ3(text);
        break;
      case 'delete_confirm':
        await handleBsDeleteConfirm(text);
        break;
      default:
        addBsMessage('system', '알 수 없는 단계입니다. "시작"을 입력하여 다시 시작하세요.');
    }
  } catch (error) {
    console.error('처리 중 오류:', error);
    addBsMessage('system', `오류가 발생했습니다: ${error.message}`);
  } finally {
    bsSubmitBtn.disabled = false;
    bsSubmitBtn.textContent = '전송';
  }
}

/**
 * 초기 단계 처리
 */
async function handleBsInitial(text) {
  const lowerText = text.toLowerCase();
  
  if (lowerText === '시작' || lowerText === 'start') {
    const response = await fetch(`${API_BASE}/session`, { method: 'POST' });
    const data = await response.json();
    
    currentSessionId = data.session_id;
    
    addBsMessage('system', data.message);
    addBsMessage('system', 'Q1: 어디에 쓸 아이디어가 필요하신가요?');
    addBsMessage('system', '(예: 모바일 앱, 마케팅 캠페인, 신제품 기획 등)');
    
    currentStep = 'q1';
  } else {
    addBsMessage('system', '"시작" 또는 "start"를 입력하여 브레인스토밍을 시작하세요.');
  }
}

/**
 * Q1 처리
 */
async function handleBsQ1(text) {
  if (!currentSessionId) {
    addBsMessage('system', '세션이 없습니다. "시작"을 입력하여 다시 시작하세요.');
    currentStep = 'initial';
    return;
  }
  
  const response = await fetch(`${API_BASE}/purpose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: currentSessionId, purpose: text })
  });
  const data = await response.json();
  
  addBsMessage('system', `✅ ${data.message}`);
  addBsMessage('system', '🤔 워밍업 질문을 생성하고 있습니다...');
  
  const warmupResponse = await fetch(`${API_BASE}/warmup/${currentSessionId}`);
  const warmupData = await warmupResponse.json();
  
  // 🔥 화면 클리어 후 Q2 표시
  setTimeout(() => {
    bsContent.innerHTML = '';
    addBsMessage('system', 'Q2: 브레인스토밍 워밍업');
    warmupData.questions.forEach((q, i) => {
      addBsMessage('system', `${i + 1}. ${q}`);
    });
    addBsMessage('system', '\n준비되셨으면 "네" 또는 "yes"를 입력하세요.');
  }, 1000); // 1초 후 클리어
  
  currentStep = 'q2';
}

/**
 * Q2 처리
 */
async function handleBsQ2(text) {
  const lowerText = text.toLowerCase();
  
  if (lowerText === '네' || lowerText === 'yes') {
    const response = await fetch(`${API_BASE}/confirm/${currentSessionId}`, { method: 'POST' });
    const data = await response.json();
    
    addBsMessage('system', data.message);
    
    // 🔥 화면 클리어 후 Q3 표시
    setTimeout(() => {
      bsContent.innerHTML = '';
      addBsMessage('system', 'Q3: 지금부터 떠오르는 무엇이든 자유롭게 많이 적어주세요.');
      addBsMessage('system', '💡 한 번에 입력 또는 여러 번 나눠 입력 가능합니다.');
      addBsMessage('system', '(쉼표로 구분: "아이디어1, 아이디어2" 또는 하나씩 입력)');
      addBsMessage('system', '\n최소 10개 이상 입력해주세요.');
    }, 1000); // 1초 후 클리어
    
    // Q3 누적 키워드 초기화
    accumulatedKeywords = [];
    currentStep = 'q3';
  } else {
    addBsMessage('system', '"네" 또는 "yes"를 입력하여 다음 단계로 진행하세요.');
  }
}

/**
 * Q3 처리
 */
async function handleBsQ3(text) {
  const lowerText = text.toLowerCase();
  
  // "완료" 또는 "생성" 입력 시 아이디어 생성
  if (lowerText === '완료' || lowerText === '생성' || lowerText === 'done') {
    if (accumulatedKeywords.length < 10) {
      addBsMessage('system', `⚠️ 최소 10개 이상 입력해주세요. (현재: ${accumulatedKeywords.length}개)`);
      addBsMessage('system', '더 입력하거나 "완료"를 입력하여 진행하세요.');
      return;
    }
    
    // 아이디어 생성 시작
    const response = await fetch(`${API_BASE}/associations/${currentSessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSessionId, associations: accumulatedKeywords })
    });
    const data = await response.json();
    
    addBsMessage('system', `✅ ${data.message} (${data.count}개)`);
    
    // 🔥 화면 클리어 후 아이디어 생성 표시
    setTimeout(() => {
      bsContent.innerHTML = '';
      addBsMessage('system', '💡 아이디어를 생성하고 있습니다...');
      addBsMessage('system', '(약 30초 소요)');
    }, 1000); // 1초 후 클리어
    
    // 🔥 아이디어 생성 API 호출을 2초 후에 시작 (클리어 후)
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    try {
      const ideasResponse = await fetch(`${API_BASE}/ideas/${currentSessionId}`);
      
      console.log('🔍 API 응답 상태:', ideasResponse.status);
      
      if (!ideasResponse.ok) {
        const errorText = await ideasResponse.text();
        console.error('❌ API 오류:', errorText);
        
        try {
          const errorData = JSON.parse(errorText);
          addBsMessage('system', `❌ 오류: ${errorData.detail || '아이디어 생성 실패'}`);
        } catch {
          addBsMessage('system', `❌ 오류: ${errorText}`);
        }
        return;
      }
      
      const ideasData = await ideasResponse.json();
      console.log('🔍 받은 데이터:', ideasData);
      
      addBsMessage('system', '\n🎉 아이디어가 생성되었습니다!\n');
      
      // 🔥 안전한 배열 체크
      if (ideasData && ideasData.ideas && Array.isArray(ideasData.ideas)) {
        if (ideasData.ideas.length === 0) {
          addBsMessage('system', '⚠️ 생성된 아이디어가 없습니다.');
        } else {
          ideasData.ideas.forEach((idea, i) => {
            addBsMessage('idea', `\n📌 아이디어 ${i + 1}: ${idea.title}\n\n${idea.description}\n\n📊 SWOT 분석:\n${idea.analysis}`);
          });
        }
      } else {
        console.error('⚠️ 잘못된 응답 형식:', ideasData);
        addBsMessage('system', '⚠️ 아이디어 형식 오류. 콘솔을 확인하세요.');
      }
      
      addBsMessage('system', '\n모든 데이터를 삭제하시겠습니까? (네/아니오)');
    } catch (error) {
      console.error('❌ 아이디어 생성 중 오류:', error);
      addBsMessage('system', `❌ 오류 발생: ${error.message}`);
      return;
    }
    
    currentStep = 'delete_confirm';
    return;
  }
  
  // 키워드 입력 처리 (쉼표로 구분 또는 단일 입력)
  const newKeywords = text.split(',').map(s => s.trim()).filter(s => s);
  accumulatedKeywords.push(...newKeywords);
  
  addBsMessage('system', `✅ +${newKeywords.length}개 추가됨 (총 ${accumulatedKeywords.length}개)`);
  
  if (accumulatedKeywords.length >= 10) {
    addBsMessage('system', '✨ 10개 이상 입력 완료! "완료" 또는 "생성"을 입력하여 아이디어를 생성하세요.');
    addBsMessage('system', '(더 추가하려면 계속 입력하세요)');
  } else {
    const remaining = 10 - accumulatedKeywords.length;
    addBsMessage('system', `⏳ ${remaining}개 더 필요합니다.`);
  }
}

/**
 * 삭제 확인 처리
 */
async function handleBsDeleteConfirm(text) {
  const lowerText = text.toLowerCase();
  
  if (lowerText === '네' || lowerText === 'yes') {
    const response = await fetch(`${API_BASE}/session/${currentSessionId}`, { method: 'DELETE' });
    const data = await response.json();
    
    addBsMessage('system', `✅ ${data.message}`);
    
    currentSessionId = null;
    currentStep = 'initial';
    
    addBsMessage('system', '\n다시 시작하려면 "시작"을 입력하세요.');
  } else {
    addBsMessage('system', '세션이 유지됩니다. 종료하려면 창을 닫으세요.');
    currentStep = 'initial';
  }
}

/**
 * 메시지 추가
 */
function addBsMessage(type, text) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `bs-message ${type}`;
  
  const bubble = document.createElement('div');
  bubble.className = 'bs-bubble';
  bubble.textContent = text;
  
  messageDiv.appendChild(bubble);
  bsContent.appendChild(messageDiv);
  
  bsContent.scrollTop = bsContent.scrollHeight;
}

/**
 * 패널 토글
 */
function toggleBsPanel() {
  isBsPanelVisible = !isBsPanelVisible;
  
  if (isBsPanelVisible) {
    bsPanel.style.display = 'flex';
    bsPanel.style.opacity = '1';
    bsPanel.style.transform = 'translate(-50%, -50%)'; // 🔥 중앙 배치 유지
    console.log('👁️ 브레인스토밍 패널 표시');
  } else {
    bsPanel.style.opacity = '0';
    bsPanel.style.transform = 'translate(-50%, -50%) scale(0.95)'; // 🔥 중앙 배치 유지 + 축소 효과
    setTimeout(() => {
      bsPanel.style.display = 'none';
    }, 300);
    console.log('🙈 브레인스토밍 패널 숨김');
  }
}
