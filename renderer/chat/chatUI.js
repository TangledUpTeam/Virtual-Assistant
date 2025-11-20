/**
 * 채팅 UI 관리
 * 채팅 패널의 상태와 UI 인터랙션 처리
 */

import { sendChatMessage } from './chatbotService.js';
import { getTodayPlan, saveSelectedTasks } from '../tasks/taskService.js';

let messages = [];
let isPanelVisible = true;
let chatPanel = null;
let messagesContainer = null;
let chatInput = null;
let sendBtn = null;
let isChatPanelInitialized = false; // 🔥 중복 초기화 방지

// 추천 업무 선택 상태
let selectedTasks = new Set();
let currentRecommendation = null; // { owner, target_date, tasks }

/**
 * 채팅 패널 초기화
 */
export function initChatPanel() {
  // 🔥 이미 초기화되었으면 무시
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
  addMessage('assistant', '안녕하세요! 무엇을 도와드릴까요? 😊');
  
  // 🔥 이벤트 리스너 등록
  sendBtn.addEventListener('click', handleSendMessage);
  chatInput.addEventListener('keydown', handleChatInputKeydown);
  window.addEventListener('keydown', handleGlobalKeydown);
  
  isChatPanelInitialized = true; // 🔥 초기화 완료 플래그
  
  console.log('✅ 채팅 패널 초기화 완료');
}

// 🔥 전역으로 export (init()에서 호출, Activity Monitor에서 사용)
window.initChatPanel = initChatPanel;
window.addMessage = addMessage;

/**
 * 채팅 입력창 키 이벤트
 */
function handleChatInputKeydown(e) {
  // 한글 입력 중(composing)이면 무시
  if (e.isComposing || e.keyCode === 229) {
    return;
  }
  
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
}

/**
 * 전역 키 이벤트 (패널 토글)
 */
function handleGlobalKeydown(e) {
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
  
  // 🔥 전송 중이면 무시 (중복 전송 방지)
  if (sendBtn.disabled) {
    console.log('⚠️  이미 전송 중...');
    return;
  }
  
  addMessage('user', text);
  
  // 🔥 입력창 초기화 (IME 문제 해결)
  chatInput.value = '';
  chatInput.blur(); // 포커스 제거
  setTimeout(() => {
    chatInput.focus(); // 다시 포커스
  }, 0);
  
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
  
  console.log(`💬 [${role}]: ${text}`);
}

/**
 * 추천 업무 카드 추가
 */
function addTaskRecommendations(data) {
  const { tasks, summary, owner, target_date } = data;
  
  currentRecommendation = { owner, target_date, tasks };
  selectedTasks.clear();
  
  messages.push({ role: 'assistant', type: 'task_recommendations', data });
  
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant';
  
  const container = document.createElement('div');
  container.className = 'task-recommendations-container';
  
  const summaryDiv = document.createElement('div');
  summaryDiv.className = 'bubble';
  summaryDiv.textContent = summary || '오늘의 추천 업무입니다!';
  container.appendChild(summaryDiv);
  
  const guideDiv = document.createElement('div');
  guideDiv.className = 'task-guide';
  guideDiv.textContent = '📌 수행할 업무를 선택해주세요 (2~4개 권장)';
  container.appendChild(guideDiv);
  
  const cardsContainer = document.createElement('div');
  cardsContainer.className = 'task-cards';
  
  tasks.forEach((task, index) => {
    const card = createTaskCard(task, index);
    cardsContainer.appendChild(card);
  });
  
  container.appendChild(cardsContainer);
  
  const saveButton = document.createElement('button');
  saveButton.className = 'task-save-button';
  saveButton.textContent = '선택 완료';
  saveButton.disabled = true;
  saveButton.addEventListener('click', handleSaveSelectedTasks);
  container.appendChild(saveButton);
  
  messageDiv.appendChild(container);
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  console.log(`🎯 추천 업무 ${tasks.length}개 표시`);
}

/**
 * 업무 카드 생성
 */
function createTaskCard(task, index) {
  const card = document.createElement('div');
  card.className = 'task-card';
  card.dataset.index = index;
  
  const priorityBadge = document.createElement('span');
  priorityBadge.className = `priority-badge priority-${task.priority}`;
  priorityBadge.textContent = {
    'high': '높음',
    'medium': '보통',
    'low': '낮음'
  }[task.priority] || '보통';
  
  const title = document.createElement('div');
  title.className = 'task-title';
  title.textContent = task.title;
  
  const description = document.createElement('div');
  description.className = 'task-description';
  description.textContent = task.description;
  
  const meta = document.createElement('div');
  meta.className = 'task-meta';
  meta.innerHTML = `
    <span class="task-category">📁 ${task.category}</span>
    <span class="task-time">⏰ ${task.expected_time}</span>
  `;
  
  card.appendChild(priorityBadge);
  card.appendChild(title);
  card.appendChild(description);
  card.appendChild(meta);
  
  card.addEventListener('click', () => {
    toggleTaskSelection(card, index);
  });
  
  return card;
}

/**
 * 업무 선택 토글
 */
function toggleTaskSelection(card, index) {
  if (selectedTasks.has(index)) {
    selectedTasks.delete(index);
    card.classList.remove('selected');
  } else {
    selectedTasks.add(index);
    card.classList.add('selected');
  }
  
  const saveButton = card.closest('.task-recommendations-container').querySelector('.task-save-button');
  saveButton.disabled = selectedTasks.size === 0;
  
  console.log(`✅ 선택된 업무: ${selectedTasks.size}개`);
}

/**
 * 선택한 업무 저장
 */
async function handleSaveSelectedTasks(event) {
  if (!currentRecommendation || selectedTasks.size === 0) {
    return;
  }
  
  const { owner, target_date, tasks } = currentRecommendation;
  const selectedTasksList = Array.from(selectedTasks).map(index => tasks[index]);
  
  const saveButton = event.target;
  saveButton.disabled = true;
  saveButton.textContent = '저장 중...';
  
  try {
    const result = await saveSelectedTasks(owner, target_date, selectedTasksList);
    
    if (result.success) {
      addMessage('assistant', `✅ ${result.saved_count}개의 업무가 저장되었습니다! 금일 진행 업무 선택이 완료되었습니다.`);
      
      selectedTasks.clear();
      currentRecommendation = null;
      
      saveButton.closest('.task-recommendations-container').style.opacity = '0.5';
      saveButton.textContent = '저장 완료';
    } else {
      addMessage('assistant', `❌ 저장 실패: ${result.message}`);
      saveButton.disabled = false;
      saveButton.textContent = '선택 완료';
    }
  } catch (error) {
    console.error('❌ 저장 오류:', error);
    addMessage('assistant', '❌ 업무 저장 중 오류가 발생했습니다.');
    saveButton.disabled = false;
    saveButton.textContent = '선택 완료';
  }
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

