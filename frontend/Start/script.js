// 세션 스토리지 키 (앱 종료 시 자동 삭제)
const STORAGE_KEYS = {
    ACCESS_TOKEN: 'access_token',
    REFRESH_TOKEN: 'refresh_token',
    USER: 'user'
};

// localStorage 대신 sessionStorage 사용
const storage = sessionStorage;

/**
 * 로그인 여부 확인
 */
function isLoggedIn() {
    return !!storage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
}

/**
 * 사용자 정보 가져오기
 */
function getUserInfo() {
    const userJson = storage.getItem(STORAGE_KEYS.USER);
    return userJson ? JSON.parse(userJson) : null;
}

/**
 * 로그아웃
 */
function logout() {
    if (confirm('정말 로그아웃하시겠습니까?')) {
        console.log('🚪 로그아웃 - 세션 스토리지 삭제');
        
        // 세션 스토리지에서 토큰 및 사용자 정보 삭제
        storage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
        storage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
        storage.removeItem(STORAGE_KEYS.USER);
        
        // 로그인 페이지로 이동 (같은 창에서)
        console.log('🔐 로그인 페이지로 이동');
        window.location.href = '/login?logout=true';
    }
}

/**
 * 시작하기 버튼 클릭
 */
function startAssistant() {
    console.log('시작하기 버튼 클릭!');
    
    // Electron인지 확인
    if (typeof window.require !== 'undefined') {
        try {
            // Electron에서는 IPC로 캐릭터 창 열기
            const { ipcRenderer } = window.require('electron');
            console.log('IPC 메시지 전송: va:start-character');
            ipcRenderer.send('va:start-character');
        } catch (err) {
            console.error('IPC 전송 실패:', err);
            alert('캐릭터 창을 열 수 없습니다.');
        }
    } else {
        // 브라우저에서는 메인 페이지로 이동
        console.log('브라우저 모드 - /main으로 이동');
        window.location.href = '/main';
    }
}

/**
 * 페이지 로드 시 실행
 */
window.addEventListener('DOMContentLoaded', () => {
    // URL에서 토큰 확인 (OAuth 콜백에서 넘어온 경우)
    const urlParams = new URLSearchParams(window.location.search);
    const accessToken = urlParams.get('access_token');
    const refreshToken = urlParams.get('refresh_token');
    const userName = urlParams.get('name');
    const userEmail = urlParams.get('user');
    
    // 토큰이 URL에 있으면 저장
    if (accessToken && refreshToken) {
        console.log('✅ OAuth 로그인 성공 - 토큰 저장 (세션)');
        storage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
        storage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
        
        const user = {
            email: userEmail,
            name: userName
        };
        storage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
        
        // URL에서 토큰 제거 (보안)
        window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    // 로그인 확인
    if (!isLoggedIn()) {
        // 로그인 안 되어있으면 로그인 페이지로
        window.location.href = '/login';
        return;
    }

    // 사용자 정보 표시
    const user = getUserInfo();
    if (user) {
        const userNameEl = document.getElementById('userName');
        if (userNameEl) {
            userNameEl.textContent = user.name || user.email || '사용자님';
        }
    }

    // 시작하기 버튼 이벤트
    const startBtn = document.getElementById('startBtn');
    if (startBtn) {
        startBtn.addEventListener('click', startAssistant);
    }
});

