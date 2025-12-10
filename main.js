const { app, BrowserWindow, screen, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let loginWin = null;
let characterWin = null;
let backendProcess = null;
let loginWindowBounds = null; // 로그인 창의 위치 저장

/**
 * 랜딩/시작 창 생성 (첫 화면)
 */
function createLandingWindow() {
  console.log('🏠 랜딩 페이지 생성');

  loginWin = new BrowserWindow({
    width: 800,
    height: 600,
    center: true,
    resizable: false,
    frame: true,
    backgroundColor: '#ffffff',
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: true
      // partition을 설정하지 않으면 앱 종료 시 세션 삭제됨
    }
  });

  // 랜딩 페이지 로드 (시작하기, 사용설명서, 로그인 버튼)
  loginWin.loadURL('http://localhost:8000/landing');

  // OAuth 페이지에서 다시 랜딩 페이지로 돌아올 때 크기 복원
  loginWin.webContents.on('did-navigate', (event, url) => {
    if (url.includes('/landing')) {
      // 랜딩 페이지로 돌아오면 원래 크기로 복원
      loginWin.setSize(800, 600);
      loginWin.center();
      console.log('🔄 랜딩 페이지 크기 복원: 800x600');
    }
  });

  // F12 단축키로 개발자 도구 열기
  loginWin.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'F12' || (input.control && input.shift && input.key === 'I')) {
      if (loginWin.webContents.isDevToolsOpened()) {
        loginWin.webContents.closeDevTools();
        console.log('🛠️ 개발자 도구 닫힘 (랜딩 창)');
      } else {
        loginWin.webContents.openDevTools({ mode: 'detach' });
        console.log('🛠️ 개발자 도구 열림 (랜딩 창)');
      }
    }
  });

  loginWin.on('closed', () => {
    console.log('🔐 로그인 창 닫힘');
    loginWin = null;
  });

  // 로그인 창의 위치를 저장 (캐릭터 창을 같은 위치에 띄우기 위해)
  loginWin.on('ready-to-show', () => {
    loginWindowBounds = loginWin.getBounds();
    console.log('📍 로그인 창 위치 저장:', loginWindowBounds);
  });

  // 로그인 창을 이동할 때마다 위치 업데이트
  loginWin.on('move', () => {
    loginWindowBounds = loginWin.getBounds();
  });
}

/**
 * 캐릭터 투명 창 생성
 */
function createCharacterWindow() {
  console.log('🎭 투명 전체화면 캐릭터 창 생성');

  // 로그인 창이 있던 디스플레이 찾기
  let targetDisplay = screen.getPrimaryDisplay();

  if (loginWindowBounds) {
    // 로그인 창의 중앙 위치 계산
    const loginCenterX = loginWindowBounds.x + loginWindowBounds.width / 2;
    const loginCenterY = loginWindowBounds.y + loginWindowBounds.height / 2;

    // 로그인 창이 있던 디스플레이 찾기
    const displays = screen.getAllDisplays();
    for (const display of displays) {
      const { x, y, width, height } = display.bounds;
      if (loginCenterX >= x && loginCenterX < x + width &&
        loginCenterY >= y && loginCenterY < y + height) {
        targetDisplay = display;
        console.log('📍 로그인 창이 있던 디스플레이 찾음:', display.id);
        break;
      }
    }
  }

  const { x, y, width, height } = targetDisplay.workArea;
  console.log(`📐 캐릭터 창 크기: ${width}x${height}, 위치: (${x}, ${y})`);

  // 전체 화면 투명 창 (클릭-스루 가능)
  characterWin = new BrowserWindow({
    width: width,
    height: height,
    x: x,
    y: y,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    hasShadow: false,
    skipTaskbar: true,
    backgroundColor: '#00000000',
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: true
    }
  });

  // 개발 모드: 캐시 + localStorage 완전 삭제
  characterWin.webContents.session.clearCache().then(() => {
    console.log('🔄 캐시 삭제 완료');
  });

  characterWin.webContents.session.clearStorageData({
    storages: ['localstorage']
  }).then(() => {
    console.log('🗑️  localStorage 삭제 완료');
  });

  // 메인 페이지 로드 (캐릭터 화면)
  characterWin.loadURL('http://localhost:8000/main');

  console.log('📦 캐릭터 로딩 중...');

  // 🔥 개발자 도구 자동 열기 (detach 모드) - 배포 시 비활성화
  // characterWin.webContents.openDevTools({ mode: 'detach' });
  // console.log('🛠️ 개발자 도구 열림 (detach 모드)');

  // 단축키 (F12, Ctrl+Shift+I: 개발자 도구 토글)
  characterWin.webContents.on('before-input-event', (event, input) => {
    // F12로 개발자 도구 (별도 창으로 열기)
    if (input.key === 'F12' || (input.control && input.shift && input.key === 'I')) {
      if (characterWin.webContents.isDevToolsOpened()) {
        characterWin.webContents.closeDevTools();
      } else {
        characterWin.webContents.openDevTools({ mode: 'detach' });
      }
    }
  });

  characterWin.webContents.on('did-finish-load', () => {
    console.log('✅ 캐릭터 로드 완료!');

    // 페이지 로드 완료 후 마우스 이벤트 활성화
    // (렌더러에서 동적으로 클릭-스루 영역 제어)
    // 초기에는 마우스 이벤트를 받아서 렌더러에서 처리할 수 있도록 함
    setTimeout(() => {
      if (characterWin && !characterWin.isDestroyed()) {
        characterWin.setIgnoreMouseEvents(false);
        console.log('✅ 마우스 이벤트 활성화');
      }
    }, 1500); // 페이지 초기화 대기 (더 길게)
  });

  // 브라우저 콘솔 메시지를 터미널로 출력 (에러만)
  characterWin.webContents.on('console-message', (event, level, message, line, sourceId) => {
    if (level >= 2) { // 2 = warning, 3 = error
      console.log(`[Browser] ${message}`);
    }
  });

  characterWin.on('closed', () => {
    console.log('🎭 캐릭터 창 닫힘');
    characterWin = null;
  });

  // 개발자 도구 (디버깅용)
  // characterWin.webContents.openDevTools();
}

// 렌더러에서 클릭-스루 영역 정보 받기
ipcMain.on('va:set-ignore-mouse', (_e, ignore) => {
  if (characterWin && !characterWin.isDestroyed()) {
    try {
      characterWin.setIgnoreMouseEvents(ignore, { forward: true });
      // 마우스 이벤트 상태 변경: ignore
    } catch (error) {
      console.error('❌ setIgnoreMouseEvents 오류:', error);
    }
  }
});

// 보고서 패널 열릴 때 alwaysOnTop 제어
ipcMain.on('va:report-panel-toggle', (_e, isOpen) => {
  if (characterWin && !characterWin.isDestroyed()) {
    try {
      if (isOpen) {
        // 보고서 패널 열릴 때: alwaysOnTop 끄기
        characterWin.setAlwaysOnTop(false);
        console.log('📝 보고서 패널 열림 → alwaysOnTop: false');
      } else {
        // 보고서 패널 닫힐 때: alwaysOnTop 켜기
        characterWin.setAlwaysOnTop(true);
        console.log('📝 보고서 패널 닫힘 → alwaysOnTop: true');
      }
    } catch (error) {
      console.error('❌ setAlwaysOnTop 오류:', error);
    }
  }
});

// 시작하기 버튼 클릭 시 캐릭터 창 생성
ipcMain.on('va:start-character', () => {
  console.log('✨ 캐릭터 시작!');

  // 캐릭터 창이 없으면 생성
  if (!characterWin) {
    createCharacterWindow();
  }

  // 로그인 창 닫기
  if (loginWin && !loginWin.isDestroyed()) {
    loginWin.close();
  }
});

// 로그아웃 시 랜딩 페이지로 돌아가기
ipcMain.on('va:logout', () => {
  console.log('👋 로그아웃');

  // 캐릭터 창 닫기
  if (characterWin && !characterWin.isDestroyed()) {
    characterWin.close();
  }

  // 랜딩 창 생성
  if (!loginWin) {
    createLandingWindow();
  }
});

// 페이지 이동 (랜딩 페이지 내에서)
ipcMain.on('va:navigate', (_e, path) => {
  console.log(`🔄 페이지 이동: ${path}`);

  if (loginWin && !loginWin.isDestroyed()) {
    loginWin.loadURL(`http://localhost:8000${path}`);
  }
});

// 종료 요청 (다이얼로그에서 확인 후)
ipcMain.on('va:request-quit', () => {
  console.log('✅ 사용자가 종료를 확인함');
  app.quit();
});

// 브레인스토밍 팝업 열기
let brainstormingWin = null;


function openBrainstormingPopup() {
  console.log('🧠 브레인스토밍 팝업 생성');

  // 이미 팝업이 열려있으면 포커스만
  if (brainstormingWin && !brainstormingWin.isDestroyed()) {
    brainstormingWin.focus();
    return;
  }

  // 브레인스토밍 팝업 창 생성
  brainstormingWin = new BrowserWindow({
    width: 700,
    height: 732, // 700 + 32 (타이틀바)
    center: true,
    resizable: true,
    frame: false, // 툴바 제거
    backgroundColor: '#f5f5f5',
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: true
    },
    parent: characterWin, // 부모 창 설정
    modal: false,
    alwaysOnTop: true, // 항상 위에 표시
    titleBarStyle: 'customButtonsOnHover', // macOS 버튼 완전 숨김
    trafficLightPosition: { x: -100, y: -100 } // 버튼을 화면 밖으로
  });

  // 브레인스토밍 전용 페이지 로드
  brainstormingWin.loadFile('brainstorming-popup.html');

  // 개발자 도구 (F12)
  brainstormingWin.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'F12') {
      if (brainstormingWin.webContents.isDevToolsOpened()) {
        brainstormingWin.webContents.closeDevTools();
      } else {
        brainstormingWin.webContents.openDevTools({ mode: 'detach' });
      }
    }
  });

  // 팝업 로드 완료
  brainstormingWin.webContents.on('did-finish-load', () => {
    console.log('🧠 브레인스토밍 팝업 로드 완료');
  });

  // 팝업 종료 시 세션 자동 삭제 및 챗봇에 알림
  brainstormingWin.on('close', async (e) => {
    console.log('🧠 브레인스토밍 팝업 닫기 시작');

    // 렌더러에서 세션 ID 가져오기
    try {
      const sessionId = await brainstormingWin.webContents.executeJavaScript('getCurrentSessionId()');

      if (sessionId) {
        console.log('🗑️ 세션 자동 삭제 시작:', sessionId);

        // 세션 삭제 API 호출
        const http = require('http');
        const options = {
          hostname: 'localhost',
          port: 8000,
          path: `/api/v1/brainstorming/session/${sessionId}`,
          method: 'DELETE'
        };

        const req = http.request(options, (res) => {
          console.log('✅ 세션 삭제 완료:', sessionId);
        });

        req.on('error', (error) => {
          console.error('❌ 세션 삭제 실패:', error);
        });

        req.end();
      }
    } catch (error) {
      console.error('❌ 세션 ID 가져오기 실패:', error);
    }
  });

  brainstormingWin.on('closed', () => {
    console.log('🧠 브레인스토밍 팝업 닫힘');

    // 챗봇에 종료 이벤트 전송
    if (characterWin && !characterWin.isDestroyed()) {
      characterWin.webContents.send('brainstorming-closed', {
        // ideasCount 제거 - 단순히 종료만 알림
      });
    }

    brainstormingWin = null;
  });

  console.log('✅ 브레인스토밍 팝업 생성 완료');
}

// IPC: 챗봇에서 브레인스토밍 팝업 열기
ipcMain.on('open-brainstorming-popup', (event) => {
  console.log('🧠 브레인스토밍 팝업 생성 요청 (챗봇)');
  openBrainstormingPopup();
});

// 브레인스토밍 창 최대화 토글
ipcMain.on('toggle-brainstorming-maximize', () => {
  if (brainstormingWin && !brainstormingWin.isDestroyed()) {
    if (brainstormingWin.isMaximized()) {
      brainstormingWin.unmaximize();
    } else {
      brainstormingWin.maximize();
    }
  }
});

// 브레인스토밍 창 닫기 (렌더러에서 요청)
ipcMain.on('close-brainstorming-window', () => {
  console.log('🧠 브레인스토밍 창 닫기 요청 (세션 삭제 완료)');
  if (brainstormingWin && !brainstormingWin.isDestroyed()) {
    brainstormingWin.close();
  }
});


// Notion OAuth 창 열기
let notionOAuthWin = null;

ipcMain.on('open-notion-oauth', async (event, authUrl) => {
  console.log('🔗 Notion OAuth 창 열기:', authUrl);
  
  // 이미 창이 열려있으면 포커스
  if (notionOAuthWin && !notionOAuthWin.isDestroyed()) {
    notionOAuthWin.focus();
    return;
  }
  
  // OAuth 전용 창 생성 (세션 공유)
  notionOAuthWin = new BrowserWindow({
    width: 800,
    height: 700,
    center: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
      // partition 제거 - 기본 세션 사용하여 로그인 상태 유지
    }
  });
  
  // Notion 쿠키만 삭제 (로그인 세션은 유지)
  const { session } = require('electron');
  try {
    console.log('🗑️ Notion 쿠키 삭제 중...');
    const cookies = await session.defaultSession.cookies.get({ domain: '.notion.so' });
    for (const cookie of cookies) {
      await session.defaultSession.cookies.remove(`https://${cookie.domain}${cookie.path}`, cookie.name);
      console.log(`   삭제: ${cookie.name}`);
    }
    console.log('✅ Notion 쿠키 삭제 완료');
  } catch (error) {
    console.error('⚠️ Notion 쿠키 삭제 실패:', error);
  }
  
  // OAuth URL 로드
  notionOAuthWin.loadURL(authUrl);
  
  // URL 변경 감지 (콜백 URL로 리디렉션되면 자동으로 처리)
  notionOAuthWin.webContents.on('will-redirect', (event, url) => {
    console.log('🔄 리디렉션 감지:', url);
    
    // 콜백 URL인지 확인
    if (url.startsWith('http://localhost:8000/api/v1/auth/notion/callback')) {
      console.log('✅ Notion OAuth 콜백 감지 - 창 닫기');
      
      // 콜백 URL을 메인 창에서 처리하도록 로드
      if (loginWin && !loginWin.isDestroyed()) {
        // 콜백을 처리하고 /landing으로 리디렉션될 것임
        loginWin.loadURL(url);
      }
      
      // OAuth 창 즉시 닫기
      if (notionOAuthWin && !notionOAuthWin.isDestroyed()) {
        notionOAuthWin.close();
      }
    }
  });
  
  // did-navigate 이벤트도 감지 (일부 경우 will-redirect가 안 잡힐 수 있음)
  notionOAuthWin.webContents.on('did-navigate', (event, url) => {
    console.log('🔄 네비게이션 감지:', url);
    
    // 콜백 URL이거나 /landing으로 리디렉션되면 창 닫기
    if (url.startsWith('http://localhost:8000/api/v1/auth/notion/callback') || 
        url.includes('/landing?notion_connected=true')) {
      console.log('✅ Notion OAuth 완료 - 창 닫기');
      
      // 메인 창에 알림
      if (loginWin && !loginWin.isDestroyed()) {
        loginWin.loadURL('http://localhost:8000/landing?notion_connected=true');
      }
      
      // OAuth 창 즉시 닫기
      if (notionOAuthWin && !notionOAuthWin.isDestroyed()) {
        notionOAuthWin.close();
      }
    }
  });
  
  // 창 닫힘 이벤트
  notionOAuthWin.on('closed', () => {
    console.log('🔗 Notion OAuth 창 닫힘');
    notionOAuthWin = null;
  });
});


// 백엔드 서버가 준비될 때까지 대기하는 함수
async function waitForBackend(maxRetries = 30) {
  const http = require('http');

  for (let i = 0; i < maxRetries; i++) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get('http://localhost:8000/health', (res) => {
          if (res.statusCode === 200) {
            resolve();
          } else {
            reject(new Error(`Status: ${res.statusCode}`));
          }
        });
        req.on('error', reject);
        req.setTimeout(1000);
      });

      console.log('✅ 백엔드 서버 준비 완료!');
      return true;
    } catch (err) {
      console.log(`⏳ 백엔드 대기 중... (${i + 1}/${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  console.error('❌ 백엔드 서버 시작 타임아웃');
  return false;
}

app.whenReady().then(async () => {
  console.log('🚀 일렉트론 앱 시작!');
  console.log('📝 세션 기반 - 앱 종료 시 로그인 정보 삭제됨');
  console.log('⌨️  단축키: ESC = 종료, F12 = 개발자 도구');

  // 🔥 앱 시작 시 캐시만 삭제 (Refresh Token은 유지 - 15일 자동 로그인)
  console.log('🗑️  캐시 삭제 중...');
  const { session } = require('electron');
  await session.defaultSession.clearStorageData({
    storages: ['localstorage', 'sessionstorage', 'cachestorage']
  });
  await session.defaultSession.clearCache();
  console.log('✅ 캐시 삭제 완료 - Refresh Token 유지됨');

  // 백엔드 서버 시작
  console.log('🔧 백엔드 서버 시작 중...');
  const isWindows = process.platform === 'win32';
  
  // Windows: 새 콘솔 창에서 Python 실행 (백엔드 출력을 별도 콘솔로)
  // Linux/Mac: stdout을 파일로 리다이렉트하거나 기존 방식 유지
  if (isWindows) {
    // Windows에서 새 콘솔 창 생성
    // CREATE_NEW_CONSOLE 플래그를 사용하면 새 콘솔 창이 생성되고
    // Python의 stdout/stderr가 그 창에 출력됨
    // stdio를 설정하지 않으면 기본적으로 새 콘솔 창에 출력됨
    backendProcess = spawn('python', ['assistant.py'], {
      detached: false,  // Electron과 함께 종료되도록 유지
      // stdio를 설정하지 않으면 CREATE_NEW_CONSOLE로 생성된 새 콘솔 창에 출력됨
      shell: false,
      windowsVerbatimArguments: false,
      creationFlags: 0x00000010, // CREATE_NEW_CONSOLE - 새 콘솔 창 생성
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1'
      }
    });
  } else {
    // Linux/Mac: 기존 방식 (터미널에서 직접 실행하는 경우)
    backendProcess = spawn('python3', ['assistant.py'], {
      stdio: ['ignore', 'pipe', 'pipe'], // stdout/stderr을 파이프로 받음
      shell: true,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1'
      }
    });
    
    // 백엔드 출력을 파일로 리다이렉트 (선택사항)
    const fs = require('fs');
    const logDir = path.join(__dirname, 'logs');
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
    const logFile = fs.createWriteStream(path.join(logDir, 'backend.log'), { flags: 'a' });
    
    backendProcess.stdout.pipe(logFile);
    backendProcess.stderr.pipe(logFile);
    
    // 터미널에도 출력 (Electron 콘솔이 아닌 터미널)
    backendProcess.stdout.pipe(process.stdout);
    backendProcess.stderr.pipe(process.stderr);
  }

  backendProcess.on('error', (err) => {
    console.error('❌ 백엔드 서버 시작 실패:', err);
  });

  backendProcess.on('exit', (code) => {
    console.log(`📴 백엔드 서버 종료됨 (코드: ${code})`);
  });

  // 백엔드가 준비될 때까지 대기
  const ready = await waitForBackend();

  if (ready) {
    // 백엔드 준비 완료 후 랜딩 페이지 띄움
    createLandingWindow();
  } else {
    console.error('❌ 백엔드를 시작할 수 없습니다.');
    app.quit();
  }
});

app.on('window-all-closed', () => {
  console.log('👋 앱 종료 중...');

  // 백엔드 프로세스 종료
  if (backendProcess && !backendProcess.killed) {
    console.log('🛑 백엔드 서버 종료 중...');
    backendProcess.kill('SIGTERM');
  }

  // 세션 삭제 (Refresh Token은 유지 - 15일 자동 로그인)
  const { session } = require('electron');
  session.defaultSession.clearStorageData({
    storages: ['localstorage', 'sessionstorage']
  }).then(() => {
    console.log('🗑️  세션 삭제 완료 - Refresh Token 유지됨');
    app.quit();
  });
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createLandingWindow();
  }
});

// 앱 종료 전 정리
app.on('before-quit', async (event) => {
  console.log('🧹 앱 종료 전 정리 중...');

  // 백엔드 프로세스 종료
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
  }

  // 세션 삭제 (Refresh Token은 유지 - 15일 자동 로그인)
  console.log('🗑️  세션 삭제 중...');
  const { session } = require('electron');
  try {
    await session.defaultSession.clearStorageData({
      storages: ['localstorage', 'sessionstorage', 'cachestorage']
    });
    await session.defaultSession.clearCache();
    console.log('✅ 세션 삭제 완료 - Refresh Token 유지됨');
  } catch (err) {
    console.error('⚠️ 세션 삭제 실패:', err);
  }
});
