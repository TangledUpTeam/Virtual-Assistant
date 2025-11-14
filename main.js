const { app, BrowserWindow, screen, ipcMain } = require('electron');
const { spawn } = require('child_process');

let loginWin = null;
let characterWin = null;
let backendProcess = null;

/**
 * 로그인/시작 창 생성
 */
function createLoginWindow() {
  console.log('🔐 로그인 창 생성');

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

  // 로그인 페이지 로드 (이미 로그인되어 있으면 자동으로 /start로 이동)
  loginWin.loadURL('http://localhost:8000/login');

  // 개발자 도구 (디버깅용)
  // loginWin.webContents.openDevTools();

  loginWin.on('closed', () => {
    console.log('🔐 로그인 창 닫힘');
    loginWin = null;
  });
}

/**
 * 캐릭터 투명 창 생성
 */
function createCharacterWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  console.log('🎭 투명 전체화면 캐릭터 창 생성');

  // 전체 화면 투명 창 (클릭-스루 가능)
  characterWin = new BrowserWindow({
    width: width,
    height: height,
    x: 0,
    y: 0,
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

  // 메인 페이지 로드 (캐릭터 화면)
  characterWin.loadURL('http://localhost:8000/main');

  console.log('📦 캐릭터 로딩 중...');

  // 기본은 클릭-스루
  characterWin.setIgnoreMouseEvents(true, { forward: true });
  
  // 단축키 (F12: 개발자 도구)
  characterWin.webContents.on('before-input-event', (event, input) => {
    // F12로 개발자 도구
    if (input.key === 'F12' || (input.control && input.shift && input.key === 'I')) {
      characterWin.webContents.toggleDevTools();
    }
  });

  characterWin.webContents.on('did-finish-load', () => {
    console.log('✅ 캐릭터 로드 완료!');
  });

  characterWin.on('closed', () => {
    console.log('🎭 캐릭터 창 닫힘');
    characterWin = null;
  });

  // 개발자 도구 (디버깅용)
  // characterWin.webContents.openDevTools();
}

// 렌더러에서 클릭-스루 영역 정보 받기 (마우스가 캐릭터 위에 있는지)
ipcMain.on('va:set-ignore-mouse', (_e, ignore) => {
  if (characterWin && !characterWin.isDestroyed()) {
    characterWin.setIgnoreMouseEvents(ignore, { forward: true });
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

// 로그아웃 시 로그인 창으로 돌아가기
ipcMain.on('va:logout', () => {
  console.log('👋 로그아웃');
  
  // 캐릭터 창 닫기
  if (characterWin && !characterWin.isDestroyed()) {
    characterWin.close();
  }
  
  // 로그인 창 생성
  if (!loginWin) {
    createLoginWindow();
  }
});

// 종료 요청 (다이얼로그에서 확인 후)
ipcMain.on('va:request-quit', () => {
  console.log('✅ 사용자가 종료를 확인함');
  app.quit();
});

app.whenReady().then(() => {
  console.log('🚀 일렉트론 앱 시작!');
  console.log('📝 세션 기반 - 앱 종료 시 로그인 정보 삭제됨');
  console.log('⌨️  단축키: ESC = 종료, F12 = 개발자 도구');
  
  // 백엔드 서버 시작
  console.log('🔧 백엔드 서버 시작 중...');
  backendProcess = spawn('python', ['assistant.py'], {
    stdio: 'inherit',
    shell: true,
    env: {
      ...process.env,
      PYTHONIOENCODING: 'utf-8',
      PYTHONUTF8: '1'
    }
  });
  
  backendProcess.on('error', (err) => {
    console.error('❌ 백엔드 서버 시작 실패:', err);
  });
  
  backendProcess.on('exit', (code) => {
    console.log(`📴 백엔드 서버 종료됨 (코드: ${code})`);
  });
  
  // 백엔드 시작 후 잠시 대기 (포트 8000 준비)
  setTimeout(() => {
    // 처음에는 로그인 창만 띄움
    createLoginWindow();
  }, 3000);
});

app.on('window-all-closed', () => { 
  console.log('👋 앱 종료 중...');
  
  // 백엔드 프로세스 종료
  if (backendProcess && !backendProcess.killed) {
    console.log('🛑 백엔드 서버 종료 중...');
    backendProcess.kill('SIGTERM');
  }
  
  // 세션 삭제 (로그인 정보 초기화)
  const { session } = require('electron');
  session.defaultSession.clearStorageData({
    storages: ['cookies', 'localstorage', 'sessionstorage']
  }).then(() => {
    console.log('🗑️  세션 삭제 완료');
    app.quit();
  });
});

app.on('activate', () => { 
  if (BrowserWindow.getAllWindows().length === 0) {
    createLoginWindow();
  }
});

// 앱 종료 전 정리
app.on('before-quit', () => {
  console.log('🧹 앱 종료 전 정리 중...');
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
  }
});
