/**
 * 채팅 패널 UI 및 상태 관리
 * Cmd/Ctrl + Enter로 토글 가능
 */

import { callChatModule } from './chatService.js';

// 메시지 상태 (메모리)
let messages = [];

// 패널 표시 상태
let isPanelVisible = true;

// DOM 요소 참조
let chatPanel = null;
let messagesContainer = null;
let chatInput = null;
let sendBtn = null;

/**
 * 채팅 패널 초기화
 */
export function initChatPanel() {
  console.log('💬 채팅 패널 초기화 중...');
  
  // DOM 요소 가져오기
  chatPanel = document.getElementById('chat-panel');
  messagesContainer = document.getElementById('messages');
  chatInput = document.getElementById('chat-input');
  sendBtn = document.getElementById('send-btn');
  
  if (!chatPanel || !messagesContainer || !chatInput || !sendBtn) {
    console.error('❌ 채팅 패널 요소를 찾을 수 없습니다.');
    return;
  }
  
  // 초기 메시지 추가
  addMessage('assistant', '안녕하세요! 무엇을 도와드릴까요? 😊');
  
  // 이벤트 리스너 등록
  setupEventListeners();
  
  console.log('✅ 채팅 패널 초기화 완료');
}

/**
 * 이벤트 리스너 설정
 */
function setupEventListeners() {
  // 전송 버튼 클릭
  sendBtn.addEventListener('click', handleSendMessage);
  
  // Enter 키로 전송
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });
  
  // Cmd/Ctrl + Enter로 패널 토글
  window.addEventListener('keydown', (e) => {
    // Cmd (Mac) 또는 Ctrl (Windows/Linux)
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      togglePanel();
    }
  });
}

/**
 * 메시지 전송 핸들러
 */
async function handleSendMessage() {
  const text = chatInput.value.trim();
  
  if (!text) return;
  
  // 사용자 메시지 추가
  addMessage('user', text);
  
  // 입력창 초기화
  chatInput.value = '';
  
  // 버튼 비활성화 (응답 대기)
  sendBtn.disabled = true;
  sendBtn.textContent = '...';
  
  try {
    // AI 응답 받기
    const response = await callChatModule(text);
    
    // AI 응답 추가
    addMessage('assistant', response);
  } catch (error) {
    console.error('❌ 채팅 오류:', error);
    addMessage('assistant', '죄송합니다. 오류가 발생했습니다. 😢');
  } finally {
    // 버튼 다시 활성화
    sendBtn.disabled = false;
    sendBtn.textContent = '전송';
  }
}

/**
 * 메시지 추가
 * @param {'user' | 'assistant'} role - 메시지 역할
 * @param {string} text - 메시지 내용
 */
function addMessage(role, text) {
  // 상태에 저장
  messages.push({ role, text });
  
  // DOM에 추가
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;
  
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  
  messageDiv.appendChild(bubble);
  messagesContainer.appendChild(messageDiv);
  
  // 스크롤을 맨 아래로
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  console.log(`💬 [${role}]: ${text}`);
}

/**
 * 채팅 패널 토글 (Cmd/Ctrl + Enter)
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
 * 메시지 상태 가져오기 (외부에서 접근 가능)
 */
export function getMessages() {
  return [...messages];
}

/**
 * 메시지 초기화 (외부에서 접근 가능)
 */
export function clearMessages() {
  messages = [];
  messagesContainer.innerHTML = '';
  console.log('🗑️ 메시지 초기화');
}

