/**
 * 일반 채팅 UI 관리
 * 간단한 대화 및 기타 기능
 */

import { sendChatMessage, initChatbotService } from './chatbotService.js';
import { getTodayPlan, saveSelectedTasks } from '../tasks/taskService.js';

// 세션 스토리지에서 토큰 가져와서 챗봇 서비스 초기화
const accessToken = sessionStorage.getItem('access_token');
console.log('🔍 세션 스토리지 확인:', {
  accessToken: accessToken ? `${accessToken.substring(0, 20)}...` : 'null',
  sessionStorageKeys: Object.keys(sessionStorage)
});

if (accessToken) {
  initChatbotService(accessToken);
  console.log('✅ 세션 스토리지에서 액세스 토큰 로드 완료');
} else {
  console.warn('⚠️ 액세스 토큰이 없습니다. 일부 기능(메일 전송 등)은 로그인이 필요합니다.');
}

let messages = [];
let isPanelVisible = true;
let chatPanel = null;
let messagesContainer = null;
let chatInput = null;
let sendBtn = null;
let isChatPanelInitialized = false;

/**
 * 채팅 패널 초기화
 */
export function initChatPanel() {
  if (isChatPanelInitialized) {
    console.log('⚠️  채팅 패널 이미 초기화됨 - 스킵');
    return;
  }
  
  console.log('💬 채팅 패널 초기화 중...');
  
  chatPanel = document.getElementById('chat-panel');
  messagesContainer = document.getElementById('messages');
  chatInput = document.getElementById('chat-input');
  sendBtn = document.getElementById('send-btn');
  
  if (!chatPanel || !messagesContainer || !chatInput || !sendBtn) {
    console.error('❌ 채팅 패널 요소를 찾을 수 없습니다.');
    return;
  }
  
  // 초기 메시지 추가
  addMessage('assistant', '안녕하세요! 무엇을 도와드릴까요? 😊\n\n💡 Tip: Ctrl+Shift+R을 눌러 보고서 & 업무 관리 패널을 열 수 있습니다!');
  
  // 이벤트 리스너 등록
  sendBtn.addEventListener('click', handleSendMessage);
  chatInput.addEventListener('keydown', handleChatInputKeydown);
  window.addEventListener('keydown', handleGlobalKeydown);
  
  // 드래그 앤 드롭 기능 초기화
  initDragAndDrop();
  
  // 리사이즈 기능 초기화
  initResize();
  
  isChatPanelInitialized = true;
  
  console.log('✅ 채팅 패널 초기화 완료');
}

/**
 * 드래그 앤 드롭 기능 초기화
 */
function initDragAndDrop() {
  const header = chatPanel.querySelector('h2');
  if (!header) return;
  
  let isDragging = false;
  let startX = 0;
  let startY = 0;
  let initialLeft = 0;
  let initialTop = 0;
  
  // 헤더에 드래그 커서 추가
  header.style.cursor = 'move';
  header.style.userSelect = 'none';
  
  header.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX;
    startY = e.clientY;
    
    // 현재 위치 가져오기
    const rect = chatPanel.getBoundingClientRect();
    initialLeft = rect.left;
    initialTop = rect.top;
    
    chatPanel.style.transition = 'none';
    e.preventDefault();
  });
  
  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    
    const deltaX = e.clientX - startX;
    const deltaY = e.clientY - startY;
    
    const newLeft = initialLeft + deltaX;
    const newTop = initialTop + deltaY;
    
    // 화면 밖으로 나가지 않도록 제한
    const maxLeft = window.innerWidth - chatPanel.offsetWidth;
    const maxTop = window.innerHeight - chatPanel.offsetHeight;
    
    chatPanel.style.left = Math.max(0, Math.min(newLeft, maxLeft)) + 'px';
    chatPanel.style.top = Math.max(0, Math.min(newTop, maxTop)) + 'px';
  });
  
  document.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      chatPanel.style.transition = '';
    }
  });
  
  console.log('✅ 드래그 앤 드롭 기능 초기화 완료');
}

/**
 * 리사이즈 기능 초기화
 */
function initResize() {
  // 리사이즈 핸들 생성
  const resizeHandle = document.createElement('div');
  resizeHandle.className = 'resize-handle';
  resizeHandle.innerHTML = '⋰';
  chatPanel.appendChild(resizeHandle);
  
  let isResizing = false;
  let startX = 0;
  let startY = 0;
  let startWidth = 0;
  let startHeight = 0;
  
  resizeHandle.addEventListener('mousedown', (e) => {
    isResizing = true;
    startX = e.clientX;
    startY = e.clientY;
    
    const rect = chatPanel.getBoundingClientRect();
    startWidth = rect.width;
    startHeight = rect.height;
    
    chatPanel.style.transition = 'none';
    e.preventDefault();
    e.stopPropagation();
  });
  
  document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    
    const deltaX = e.clientX - startX;
    const deltaY = e.clientY - startY;
    
    const newWidth = startWidth + deltaX;
    const newHeight = startHeight + deltaY;
    
    // 최소/최대 크기 제한
    const minWidth = 300;
    const maxWidth = 800;
    const minHeight = 400;
    const maxHeight = window.innerHeight - 100;
    
    chatPanel.style.width = Math.max(minWidth, Math.min(newWidth, maxWidth)) + 'px';
    chatPanel.style.height = Math.max(minHeight, Math.min(newHeight, maxHeight)) + 'px';
  });
  
  document.addEventListener('mouseup', () => {
    if (isResizing) {
      isResizing = false;
      chatPanel.style.transition = '';
    }
  });
  
  console.log('✅ 리사이즈 기능 초기화 완료');
}

// 전역으로 export
window.initChatPanel = initChatPanel;
window.addMessage = addMessage;

/**
 * 채팅 입력창 키 이벤트
 */
function handleChatInputKeydown(e) {
  if (e.isComposing || e.keyCode === 229) {
    return;
  }
  
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
}

/**
 * 전역 키 이벤트 (패널 토글 및 캐릭터 토글)
 */
function handleGlobalKeydown(e) {
  // Shift + Ctrl(Cmd) + Enter: 캐릭터 토글
  if (e.shiftKey && (e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault();
    toggleCharacter();
    return;
  }
  
  // Ctrl(Cmd) + Enter: 챗창 토글
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault();
    togglePanel();
  }
}

/**
 * 메시지 전송 처리
 */
async function handleSendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;
  
  // 🧠 브레인스토밍 키워드 감지
  if (text.includes('브레인스토밍') || text.includes('brainstorming')) {
    console.log('🧠 브레인스토밍 키워드 감지!');
    
    // 사용자 메시지 추가
    addMessage('user', text);
    chatInput.value = '';
    
    // 챗봇 응답
    addMessage('assistant', '브레인스토밍을 시작합니다! 🚀');
    
    // 브레인스토밍 팝업 열기
    setTimeout(() => {
      openBrainstormingPopup();
    }, 500);
    
    return;
  }
  
  if (sendBtn.disabled) {
    console.log('⚠️  이미 전송 중...');
    return;
  }
  
  addMessage('user', text);
  
  chatInput.value = '';
  chatInput.blur();
  setTimeout(() => chatInput.focus(), 0);
  
  sendBtn.disabled = true;
  sendBtn.textContent = '...';
  
  try {
    // "오늘 뭐할지 추천" 등의 키워드가 있으면 업무 추천 API 호출
    if (text.includes('오늘') && (text.includes('추천') || text.includes('뭐할'))) {
      const response = await getTodayPlan();
      
      if (response.type === 'task_recommendations') {
        addTaskRecommendations(response.data);
      } else {
        addMessage('assistant', response.data);
      }
    } else {
      // 그 외 모든 메시지는 Chatbot API로 전달
      const assistantMessage = await sendChatMessage(text);
      addMessage('assistant', assistantMessage);
    }
  } catch (error) {
    console.error('❌ 채팅 오류:', error);
    addMessage('assistant', '죄송합니다. 오류가 발생했습니다. 😢');
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = '전송';
  }
}

/**
 * 간단한 응답 처리
 */
async function handleSimpleResponse(text) {
  const lower = text.toLowerCase();
  
  // 보고서/업무 관련 요청은 다른 패널로 안내
  if (lower.includes('보고서') || lower.includes('추천') || lower.includes('업무')) {
    addMessage('assistant', '보고서 및 업무 관리는 **Ctrl+Shift+R**을 눌러\n보고서 & 업무 패널을 열어주세요! 📝');
    return;
  }
  
  // 브레인스토밍 안내
  if (lower.includes('브레인') || lower.includes('아이디어')) {
    addMessage('assistant', '브레인스토밍은 **Ctrl+Shift+B**를 눌러\n브레인스토밍 패널을 열어주세요! 💡');
    return;
  }
  
  // 일반 응답
  addMessage('assistant', `"${text}" - 답변을 준비 중입니다! 😊\n\n사용 가능한 기능:\n• Ctrl+Shift+R - 보고서 & 업무 관리\n• Ctrl+Shift+B - 브레인스토밍`);
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
  
  console.log(`💬 [${role}]: ${text.substring(0, 50)}${text.length > 50 ? '...' : ''}`);
}

/**
 * 패널 토글
 */
function togglePanel() {
  isPanelVisible = !isPanelVisible;
  
  if (isPanelVisible) {
    chatPanel.style.display = 'flex';
    console.log('👁️ 채팅 패널 표시');
  } else {
    chatPanel.style.display = 'none';
    console.log('🙈 채팅 패널 숨김');
  }
}

/**
 * 캐릭터 토글 (Shift + Ctrl/Cmd + Enter)
 */
let isCharacterVisible = true;
function toggleCharacter() {
  const stage = document.getElementById('stage');
  if (!stage) {
    console.warn('⚠️  Live2D stage 요소를 찾을 수 없습니다.');
    return;
  }
  
  isCharacterVisible = !isCharacterVisible;
  
  if (isCharacterVisible) {
    // display 속성을 제거하여 원래대로 복원
    stage.style.display = '';
    console.log('👁️ 캐릭터 표시');
    addMessage('assistant', '안녕하세요! 다시 왔어요! 👋');
  } else {
    stage.style.display = 'none';
    console.log('🙈 캐릭터 숨김');
    addMessage('assistant', '잠시 숨을게요~ Shift + Ctrl/Cmd + Enter로 다시 불러주세요! 👻');
  }
}

/**
 * 브레인스토밍 팝업 열기
 */
function openBrainstormingPopup() {
  console.log('🧠 브레인스토밍 팝업 열기');
  
  // Electron IPC로 메인 프로세스에 팝업 요청
  if (window.require) {
    const { ipcRenderer } = window.require('electron');
    ipcRenderer.send('open-brainstorming-popup');
    
    // 챗봇 패널 숨기기
    chatPanel.style.display = 'none';
    isPanelVisible = false;
    
    // 팝업 종료 이벤트 리스너
    ipcRenderer.once('brainstorming-closed', (event, data) => {
      console.log('🧠 브레인스토밍 완료:', data);
      
      // 챗봇 패널 복구
      chatPanel.style.display = 'flex';
      isPanelVisible = true;
      
      // 완료 메시지 추가
      addMessage('assistant', '브레인스토밍이 종료되었습니다.');
    });
  } else {
    console.error('❌ Electron IPC를 사용할 수 없습니다.');
    addMessage('assistant', '❌ 브레인스토밍 팝업을 열 수 없습니다.');
  }
}
