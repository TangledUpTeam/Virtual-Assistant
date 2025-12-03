/**
 * HR 패널 UI 및 상태 관리
 * Notion 연동 및 마크다운 렌더링 지원
 */

import { queryHRDocument } from './hrService.js';

// 패널 표시 상태
let isPanelVisible = true;

// 메시지 히스토리
let messages = [];

// DOM 요소 참조
let hrPanel = null;
let hrContent = null;
let hrInput = null;
let hrSubmitBtn = null;

/**
 * HR 패널 초기화
 */
export function initHRPanel() {
  console.log('📚 HR 패널 초기화 중...');
  
  // DOM 요소 가져오기
  hrPanel = document.getElementById('hr-panel');
  hrContent = document.getElementById('hr-content');
  hrInput = document.getElementById('hr-input');
  hrSubmitBtn = document.getElementById('hr-submit-btn');
  
  if (!hrPanel || !hrContent || !hrInput || !hrSubmitBtn) {
    console.error('❌ HR 패널 요소를 찾을 수 없습니다.');
    return;
  }
  
  // 초기 메시지 표시
  showInitialMessage();
  
  // 이벤트 리스너 등록
  setupEventListeners();
  
  console.log('✅ HR 패널 초기화 완료');
}

/**
 * 이벤트 리스너 설정
 */
function setupEventListeners() {
  // 제출 버튼 클릭
  hrSubmitBtn.addEventListener('click', handleSubmit);
  
  // Enter 키로 전송
  hrInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  });
}

/**
 * 초기 메시지 표시
 */
function showInitialMessage() {
  addMessage('assistant', '안녕하세요! HR 도우미입니다. 😊\n\n회사 규정, 복지, 휴가 등에 대해 질문해주세요.\n\nNotion 연동 기능:\n- "노션 페이지 검색: [키워드]"\n- "노션 페이지 불러오기: [페이지ID]"\n- "노션에 저장: [제목]"');
}

/**
 * 제출 핸들러
 */
async function handleSubmit() {
  const text = hrInput.value.trim();
  
  if (!text) return;
  
  // 사용자 메시지 추가
  addMessage('user', text);
  
  // 입력창 초기화
  hrInput.value = '';
  
  // 버튼 비활성화 (응답 대기)
  hrSubmitBtn.disabled = true;
  hrSubmitBtn.textContent = '...';
  
  try {
    // Notion 명령어 파싱
    if (text.startsWith('노션 페이지 검색:')) {
      await handleNotionSearch(text.substring('노션 페이지 검색:'.length).trim());
    } else if (text.startsWith('노션 페이지 불러오기:')) {
      await handleNotionGetPage(text.substring('노션 페이지 불러오기:'.length).trim());
    } else if (text.startsWith('노션에 저장:')) {
      await handleNotionSave(text.substring('노션에 저장:'.length).trim());
    } else {
      // 일반 HR 질문
      await handleHRQuery(text);
    }
  } catch (error) {
    console.error('처리 중 오류:', error);
    addMessage('assistant', `오류가 발생했습니다: ${error.message}`);
  } finally {
    // 버튼 활성화
    hrSubmitBtn.disabled = false;
    hrSubmitBtn.textContent = '전송';
  }
}

/**
 * HR 질문 처리
 */
async function handleHRQuery(query) {
  try {
    const response = await queryHRDocument(query);
    
    if (response.type === 'text') {
      addMessage('assistant', response.data);
    } else if (response.type === 'error') {
      addMessage('assistant', `❌ ${response.data}`);
    } else {
      addMessage('assistant', response.data);
    }
  } catch (error) {
    console.error('HR 질문 처리 오류:', error);
    addMessage('assistant', '죄송합니다. 답변을 생성하는 중 오류가 발생했습니다.');
  }
}

/**
 * Notion 페이지 검색
 */
async function handleNotionSearch(query) {
  try {
    // 쿠키에서 user 정보 가져오기
    const userCookie = getCookie('user');
    if (!userCookie) {
      addMessage('assistant', '❌ 로그인이 필요합니다.');
      return;
    }
    
    const userData = JSON.parse(decodeURIComponent(userCookie));
    const userId = userData.id;
    
    addMessage('assistant', `🔍 "${query}" 검색 중...`);
    
    const response = await fetch('http://localhost:8000/api/tools/notion/search-pages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId.toString(),
        query: query,
        page_size: 10
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      const pages = result.data.pages;
      if (pages.length === 0) {
        addMessage('assistant', '검색 결과가 없습니다.');
      } else {
        let message = `✅ ${pages.length}개의 페이지를 찾았습니다:\n\n`;
        pages.forEach((page, index) => {
          message += `${index + 1}. **${page.title}**\n   ID: \`${page.id}\`\n   URL: ${page.url}\n\n`;
        });
        addMarkdownMessage(message);
      }
    } else {
      addMessage('assistant', `❌ 검색 실패: ${result.error}`);
    }
  } catch (error) {
    console.error('Notion 검색 오류:', error);
    addMessage('assistant', `❌ 검색 중 오류 발생: ${error.message}`);
  }
}

/**
 * Notion 페이지 불러오기
 */
async function handleNotionGetPage(pageId) {
  try {
    // 쿠키에서 user 정보 가져오기
    const userCookie = getCookie('user');
    if (!userCookie) {
      addMessage('assistant', '❌ 로그인이 필요합니다.');
      return;
    }
    
    const userData = JSON.parse(decodeURIComponent(userCookie));
    const userId = userData.id;
    
    addMessage('assistant', `📄 페이지 불러오는 중...`);
    
    const response = await fetch('http://localhost:8000/api/tools/notion/get-page-content', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId.toString(),
        page_id: pageId.trim()
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      const { title, markdown } = result.data;
      addMessage('assistant', `✅ 페이지: **${title}**`);
      addMarkdownMessage(markdown);
    } else {
      addMessage('assistant', `❌ 페이지 불러오기 실패: ${result.error}`);
    }
  } catch (error) {
    console.error('Notion 페이지 불러오기 오류:', error);
    addMessage('assistant', `❌ 페이지 불러오기 중 오류 발생: ${error.message}`);
  }
}

/**
 * Notion에 저장
 */
async function handleNotionSave(title) {
  try {
    // 쿠키에서 user 정보 가져오기
    const userCookie = getCookie('user');
    if (!userCookie) {
      addMessage('assistant', '❌ 로그인이 필요합니다.');
      return;
    }
    
    const userData = JSON.parse(decodeURIComponent(userCookie));
    const userId = userData.id;
    
    // 최근 대화 내용을 마크다운으로 변환
    const conversationMarkdown = messages.map(msg => {
      if (msg.role === 'user') {
        return `**사용자**: ${msg.text}`;
      } else {
        return `**HR 도우미**: ${msg.text}`;
      }
    }).join('\n\n');
    
    addMessage('assistant', `💾 "${title}" 페이지 생성 중...`);
    
    // 부모 페이지 ID는 사용자가 입력하거나 기본값 사용
    // 여기서는 간단히 에러 메시지로 안내
    addMessage('assistant', '⚠️ 부모 페이지 ID가 필요합니다.\n사용법: "노션에 저장: [제목] | [부모페이지ID]"');
    
    // TODO: 실제 저장 로직 구현
  } catch (error) {
    console.error('Notion 저장 오류:', error);
    addMessage('assistant', `❌ 저장 중 오류 발생: ${error.message}`);
  }
}

/**
 * 메시지 추가
 */
function addMessage(type, text) {
  messages.push({ role: type, text: text });
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `hr-message ${type}`;
  
  const bubble = document.createElement('div');
  bubble.className = 'hr-bubble';
  bubble.textContent = text;
  
  messageDiv.appendChild(bubble);
  hrContent.appendChild(messageDiv);
  
  // 스크롤을 최하단으로
  hrContent.scrollTop = hrContent.scrollHeight;
}

/**
 * 마크다운 메시지 추가
 */
function addMarkdownMessage(markdown) {
  messages.push({ role: 'markdown', text: markdown });
  
  const messageDiv = document.createElement('div');
  messageDiv.className = 'hr-message markdown';
  
  const bubble = document.createElement('div');
  bubble.className = 'hr-bubble';
  
  // Marked.js로 마크다운 렌더링
  if (typeof marked !== 'undefined') {
    bubble.innerHTML = marked.parse(markdown);
  } else {
    bubble.textContent = markdown;
  }
  
  messageDiv.appendChild(bubble);
  hrContent.appendChild(messageDiv);
  
  // 스크롤을 최하단으로
  hrContent.scrollTop = hrContent.scrollHeight;
}

/**
 * 쿠키 가져오기
 */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(';').shift();
  }
  return null;
}

/**
 * 패널 토글
 */
export function togglePanel() {
  isPanelVisible = !isPanelVisible;
  
  if (isPanelVisible) {
    hrPanel.style.display = 'flex';
    hrPanel.style.opacity = '1';
    hrPanel.style.transform = 'translateY(0)';
  } else {
    hrPanel.style.opacity = '0';
    hrPanel.style.transform = 'translateY(-20px)';
    setTimeout(() => {
      hrPanel.style.display = 'none';
    }, 300);
  }
}

/**
 * 세션 ID 가져오기 (Electron용)
 */
export function getCurrentSessionId() {
  return null; // HR 패널은 세션 ID 사용 안 함
}

