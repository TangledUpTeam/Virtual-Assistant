const { app, BrowserWindow, globalShortcut, screen, ipcMain } = require('electron');

let win;
function createWindow(){
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  // 전체 화면 투명 창 (클릭-스루 가능)
  win = new BrowserWindow({
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
    webPreferences: { contextIsolation:false, nodeIntegration:true }
  });

  win.loadFile('index.html');

  // 기본은 클릭-스루 (투명 배경은 뒤 클릭 가능)
  // forward: true로 설정하면 마우스 이벤트를 받으면서도 뒤로 전달
  win.setIgnoreMouseEvents(true, { forward: true });
  
  // 개발자 도구 단축키 (디버깅용)
  win.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'F12' || (input.control && input.shift && input.key === 'I')) {
      win.webContents.toggleDevTools();
    }
  });
}

// 렌더러에서 클릭-스루 영역 정보 받기 (마우스가 캐릭터 위에 있는지)
ipcMain.on('va:set-ignore-mouse', (_e, ignore)=>{
  win?.setIgnoreMouseEvents(ignore, { forward: true });
});

app.whenReady().then(createWindow);
app.on('window-all-closed', ()=>{ if (process.platform!=='darwin') app.quit(); });
app.on('activate', ()=>{ if (BrowserWindow.getAllWindows().length===0) createWindow(); });
