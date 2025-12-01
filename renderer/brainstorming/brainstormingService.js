/**
 * 브레인스토밍 서비스
 * brainstorming.py API 연동
 */

const API_BASE = 'http://localhost:8000/api/v1/brainstorming';

// 🔥 전역으로 export (init()에서 호출)
window.initBrainstormingPanel = null;

// 세션 ID를 외부에서 접근 가능하도록 export
export function getCurrentSessionId() {
  return currentSessionId;
}

// 세션 삭제 함수 export
export async function deleteCurrentSession() {
  if (!currentSessionId) {
    console.log('⚠️  삭제할 세션이 없습니다.');
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE}/session/${currentSessionId}`, {
      method: 'DELETE'
    });
    
    if (response.ok) {
      console.log('✅ 세션 삭제 완료:', currentSessionId);
      currentSessionId = null;
    } else {
      console.error('❌ 세션 삭제 실패:', response.status);
    }
  } catch (error) {
    console.error('❌ 세션 삭제 오류:', error);
  }
}

// 패널 표시 상태
let isBsPanelVisible = false;

// 현재 세션 ID
let currentSessionId = null;

// 현재 단계
let currentStep = 'initial'; // initial, q1, q2, q3, ideas, complete

// Q3 누적 키워드 저장
let accumulatedKeywords = [];

// Q3 동적 메시지 요소 (고정 위치에 갱신)
let dynamicMessageElement = null;

// Q3 생성 버튼 요소
let generateButtonElement = null;

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
  
  // 🔥 팝업 창에서는 Cmd+Shift+B 토글 비활성화 (메인 창에서만 사용)
  // 팝업은 항상 보이는 상태이므로 토글 불필요
}

/**
 * 초기 메시지 표시
 */
function showInitialBsMessage() {
  addBsMessage('system', '안녕하세요! 어디에 쓸 아이디어가 필요하신가요? 🤔');
  addBsMessage('system', '(예: 모바일 앱, 마케팅 캠페인, 신제품 기획 등)');
  
  // 🔥 세션 자동 생성
  createSession();
  
  currentStep = 'q1'; // 바로 Q1으로 시작
}

/**
 * 세션 자동 생성
 */
async function createSession() {
  try {
    const response = await fetch(`${API_BASE}/session`, { method: 'POST' });
    const data = await response.json();
    
    currentSessionId = data.session_id;
    console.log('✅ 세션 생성:', currentSessionId);
  } catch (error) {
    console.error('❌ 세션 생성 실패:', error);
    addBsMessage('system', '세션 생성에 실패했습니다. 새로고침 후 다시 시도하세요.');
  }
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
  
  // 🔥 Q3 단계에서는 채팅창에 표시하지 않음 (키워드 태그로만 표시)
  if (currentStep !== 'q3') {
    addBsMessage('user', text);
  }
  
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
        addBsMessage('system', '알 수 없는 단계입니다. 창을 닫고 다시 시작하세요.');
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
 * Q1 처리
 */
async function handleBsQ1(text) {
  if (!currentSessionId) {
    addBsMessage('system', '세션이 없습니다. 창을 닫고 다시 시작하세요.');
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
    
    // 질문들을 굵고 중앙 정렬로 표시
    warmupData.questions.forEach((q) => {
      addBsMessage('warmup', q);
    });
    
    // 🔥 안내 메시지를 하나의 예쁜 박스로 표시
    const instructionBox = document.createElement('div');
    instructionBox.style.cssText = `
      background: rgba(156, 175, 136, 0.08);
      border: 2px solid rgba(156, 175, 136, 0.3);
      border-radius: 16px;
      padding: 24px;
      margin: 30px auto;
      max-width: 85%;
      text-align: center;
      line-height: 1.8;
      color: #2c3e50;
      font-size: 15px;
    `;
    
    instructionBox.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 15px; font-size: 16px;">
        잠시 후 자유롭게 문장, 단어들을 입력하세요.
      </div>
      <div style="font-size: 14px; color: #666; margin: 10px 0;">
        예시) 단어, 단어, 문장 ⏎<br>
        예시) 단어 ⏎
      </div>
      <div style="font-weight: 500; margin-top: 15px; color: #7A8C6F;">
        아래 입력창에 아무거나 입력하면 시작됩니다.
      </div>
    `;
    
    bsContent.appendChild(instructionBox);
  }, 1000); // 1초 후 클리어
  
  currentStep = 'q2';
}

/**
 * Q2 처리 (아무 키나 누르면 Q3로)
 */
async function handleBsQ2(text) {
  // 아무 키나 입력되면 Q3로 진행
  const response = await fetch(`${API_BASE}/confirm/${currentSessionId}`, { method: 'POST' });
  const data = await response.json();
  
  // 🔥 화면 클리어 후 Q3 표시
  setTimeout(() => {
    bsContent.innerHTML = '';
    
    // 🔥 동적 메시지 표시 영역 생성 (고정 타이틀 + 동적 메시지)
    createDynamicMessageArea();
    
    // 초기 메시지 표시
    updateDynamicMessage();
  }, 1000); // 1초 후 클리어
  
  // Q3 누적 키워드 초기화
  accumulatedKeywords = [];
  currentStep = 'q3';
}

/**
 * 🔥 동적 메시지 영역 생성 (페이지 상단 고정)
 */
function createDynamicMessageArea() {
  // 기존 요소 제거
  if (dynamicMessageElement) {
    dynamicMessageElement.remove();
  }
  if (generateButtonElement) {
    generateButtonElement.remove();
  }
  
  // 🔥 고정 타이틀 생성
  const fixedTitle = document.createElement('div');
  fixedTitle.style.cssText = `
    text-align: center;
    font-size: 18px;
    font-weight: 600;
    color: #2c3e50;
    margin: 20px 0 10px 0;
    padding: 15px;
  `;
  fixedTitle.textContent = ' 지금부터 떠오르는 무엇이든 자유롭게 많이 적어주세요.';
  
  // 동적 메시지 div 생성
  dynamicMessageElement = document.createElement('div');
  dynamicMessageElement.id = 'dynamic-message';
  dynamicMessageElement.style.cssText = `
    text-align: center;
    font-size: 18px;
    font-weight: 500;
    color: #2c3e50;
    margin: 10px 0 30px 0;
    padding: 20px;
    background: rgba(156, 175, 136, 0.1);
    border-radius: 12px;
    min-height: 60px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 15px;
  `;
  
  bsContent.appendChild(fixedTitle);
  bsContent.appendChild(dynamicMessageElement);
}

/**
 * 🔥 동적 메시지 갱신 (입력 개수에 따라)
 */
function updateDynamicMessage() {
  if (!dynamicMessageElement) return;
  
  const count = accumulatedKeywords.length;
  let message = '';
  let showButton = false;
  
  if (count < 5) {
    message = '💭 떠오르는 것을 자유롭게 입력해주세요';
  } else if (count >= 5 && count <= 9) {
    message = '😊 좋아요! 조금만 더 입력해볼까요?';
  } else if (count >= 10 && count <= 14) {
    message = '🎉 많이 입력했네요~! 더 있으면 입력하고, 없으면 \'생성\'을 눌러주세요';
    showButton = true;
  } else if (count >= 15 && count < 25) {
    message = '🚀 와! 많이 입력하셨네요! 준비되셨으면 \'생성\' 버튼을 눌러주세요';
    showButton = true;
  } else {
    // 25개 도달
    message = '✅ 25개 입력 완료! 이제 아이디어를 생성해주세요 🎨';
    showButton = true;
  }
  
  // 메시지 텍스트만 업데이트 (버튼은 별도)
  const messageText = dynamicMessageElement.querySelector('.dynamic-text') || document.createElement('div');
  messageText.className = 'dynamic-text';
  messageText.textContent = message;
  
  // 기존 내용 지우고 메시지만 추가
  dynamicMessageElement.innerHTML = '';
  dynamicMessageElement.appendChild(messageText);
  
  // 버튼 표시 (10개 이상)
  if (showButton) {
    if (!generateButtonElement) {
      generateButtonElement = document.createElement('button');
      generateButtonElement.textContent = '🎨 아이디어 생성하기';
      generateButtonElement.style.cssText = `
        background: linear-gradient(135deg, #9CAF88 0%, #7A8C6F 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        font-size: 16px;
        font-weight: bold;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(156, 175, 136, 0.3);
      `;
      
      // 호버 효과
      generateButtonElement.addEventListener('mouseenter', () => {
        generateButtonElement.style.transform = 'translateY(-2px)';
        generateButtonElement.style.boxShadow = '0 6px 20px rgba(156, 175, 136, 0.4)';
      });
      generateButtonElement.addEventListener('mouseleave', () => {
        generateButtonElement.style.transform = 'translateY(0)';
        generateButtonElement.style.boxShadow = '0 4px 15px rgba(156, 175, 136, 0.3)';
      });
      
      // 클릭 시 아이디어 생성
      generateButtonElement.addEventListener('click', async () => {
        generateButtonElement.disabled = true;
        generateButtonElement.textContent = '생성 중...';
        await generateIdeas();
      });
    }
    
    dynamicMessageElement.appendChild(generateButtonElement);
  } else {
    // 10개 미만이면 버튼 제거
    if (generateButtonElement) {
      generateButtonElement.remove();
      generateButtonElement = null;
    }
  }
}

/**
 * Q3 처리
 */
async function handleBsQ3(text) {
  const lowerText = text.toLowerCase();
  
  // "생성" 입력 시 아이디어 생성
  if (lowerText === '생성' || lowerText === 'done') {
    if (accumulatedKeywords.length < 10) {
      addBsMessage('system', `⚠️ 최소 10개 이상 입력해주세요. (현재: ${accumulatedKeywords.length}개)`);
      return;
    }
    
    await generateIdeas();
    return;
  }
  
  // 🔥 25개 제한 체크
  if (accumulatedKeywords.length >= 25) {
    addBsMessage('system', '⚠️ 최대 25개까지만 입력 가능합니다. 이제 아이디어를 생성해주세요!');
    return;
  }
  
  // 키워드 입력 처리 (쉼표로 구분 또는 단일 입력)
  const newKeywords = text.split(',').map(s => s.trim()).filter(s => s);
  
  // 🔥 25개 초과 방지 (입력 중 초과되는 경우)
  const availableSlots = 25 - accumulatedKeywords.length;
  const keywordsToAdd = newKeywords.slice(0, availableSlots);
  const exceededKeywords = newKeywords.slice(availableSlots);
  
  if (keywordsToAdd.length > 0) {
    accumulatedKeywords.push(...keywordsToAdd);
    
    // 🔥 입력값을 동적 메시지 아래에 표시
    keywordsToAdd.forEach(keyword => {
      const keywordDiv = document.createElement('div');
      keywordDiv.style.cssText = `
        background: rgba(156, 175, 136, 0.2);
        padding: 8px 15px;
        margin: 5px;
        border-radius: 20px;
        display: inline-block;
        font-size: 14px;
        color: #2c3e50;
      `;
      keywordDiv.textContent = keyword;
      
      // dynamicMessageElement 바로 다음에 삽입
      if (dynamicMessageElement && dynamicMessageElement.nextSibling) {
        bsContent.insertBefore(keywordDiv, dynamicMessageElement.nextSibling);
      } else {
        bsContent.appendChild(keywordDiv);
      }
    });
  }
  
  // 🔥 25개 도달 시 메시지
  if (accumulatedKeywords.length >= 25) {
    addBsMessage('system', '✅ 25개 입력 완료! 이제 "생성" 버튼을 눌러주세요 🎨');
  }
  
  // 🔥 초과된 키워드 알림
  if (exceededKeywords.length > 0) {
    addBsMessage('system', `⚠️ ${exceededKeywords.length}개는 25개 제한으로 추가되지 않았습니다.`);
  }
  
  // 🔥 동적 메시지 갱신
  updateDynamicMessage();
}

/**
 * 🔥 아이디어 생성 함수 (버튼 클릭 or "생성" 입력 시)
 */
async function generateIdeas() {
  // 연관어 저장 API 호출
  const response = await fetch(`${API_BASE}/associations/${currentSessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: currentSessionId, associations: accumulatedKeywords })
  });
  const data = await response.json();
  
  addBsMessage('system', `✅ ${data.message} (${data.count}개)`);
  
  // 🔥 화면 클리어 후 로딩 스피너 표시
  setTimeout(() => {
    bsContent.innerHTML = '';
    
    // 로딩 컨테이너 생성
    const loadingContainer = document.createElement('div');
    loadingContainer.style.cssText = `
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px 20px;
      text-align: center;
    `;
    
    // 🔄 스피너 생성
    const spinner = document.createElement('div');
    spinner.style.cssText = `
      width: 60px;
      height: 60px;
      border: 5px solid rgba(156, 175, 136, 0.2);
      border-top-color: #9CAF88;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 25px;
    `;
    
    // 메시지 텍스트
    const messageText = document.createElement('div');
    messageText.style.cssText = `
      font-size: 18px;
      font-weight: 600;
      color: #2c3e50;
      margin-bottom: 10px;
    `;
    messageText.textContent = '💡 아이디어를 생성하고 있습니다...';
    
    const subText = document.createElement('div');
    subText.style.cssText = `
      font-size: 14px;
      color: #7A8C6F;
    `;
    subText.textContent = '(약 30초 소요)';
    
    loadingContainer.appendChild(spinner);
    loadingContainer.appendChild(messageText);
    loadingContainer.appendChild(subText);
    bsContent.appendChild(loadingContainer);
    
    // 🔥 CSS 애니메이션 추가 (한 번만 실행)
    if (!document.getElementById('spinner-animation')) {
      const style = document.createElement('style');
      style.id = 'spinner-animation';
      style.textContent = `
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `;
      document.head.appendChild(style);
    }
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
    
    // 🔥 로딩 스피너 제거 후 결과 표시
    bsContent.innerHTML = '';
    
    addBsMessage('system', '\n🎉 아이디어가 생성되었습니다!\n');
    
    // 🔥 안전한 배열 체크
    if (ideasData && ideasData.ideas && Array.isArray(ideasData.ideas)) {
      if (ideasData.ideas.length === 0) {
        addBsMessage('system', '⚠️ 생성된 아이디어가 없습니다.');
      } else {
        ideasData.ideas.forEach((idea, i) => {
          // 🔥 SWOT 분석이 이미 description에 포함되어 있으면 중복 방지
          const fullContent = idea.analysis 
            ? `\n📌 아이디어 ${i + 1}: ${idea.title}\n\n${idea.description}\n\n${idea.analysis}`
            : `\n📌 아이디어 ${i + 1}: ${idea.title}\n\n${idea.description}`;
          
          addBsMessage('idea', fullContent);
        });
      }
    } else {
      console.error('⚠️ 잘못된 응답 형식:', ideasData);
      addBsMessage('system', '⚠️ 아이디어 형식 오류. 콘솔을 확인하세요.');
    }
    
    addBsMessage('system', '\n✅ 브레인스토밍이 완료되었습니다!');
    addBsMessage('system', '종료하려면 아무 키나 누르세요. (세션이 자동으로 삭제됩니다)');
  } catch (error) {
    console.error('❌ 아이디어 생성 중 오류:', error);
    addBsMessage('system', `❌ 오류 발생: ${error.message}`);
    return;
  }
  
  currentStep = 'delete_confirm';
}

/**
 * 삭제 확인 처리 (아무 키나 누르면 삭제 후 종료)
 */
async function handleBsDeleteConfirm(text) {
  // 아무 키나 눌렀으면 세션 삭제
  addBsMessage('system', '세션을 삭제하는 중...');
  
  try {
    const response = await fetch(`${API_BASE}/session/${currentSessionId}`, { method: 'DELETE' });
    const data = await response.json();
    
    addBsMessage('system', `✅ ${data.message}`);
    
    currentSessionId = null;
    
    // 창 닫기 (IPC로 메인 프로세스에 알림)
    if (window.require) {
      const { ipcRenderer } = window.require('electron');
      setTimeout(() => {
        ipcRenderer.send('close-brainstorming-window');
      }, 1000); // 1초 후 자동 닫기
    }
  } catch (error) {
    console.error('❌ 세션 삭제 실패:', error);
    addBsMessage('system', '❌ 세션 삭제에 실패했습니다. 창을 직접 닫아주세요.');
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
