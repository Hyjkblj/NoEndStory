const { app, BrowserWindow } = require('electron');
const path = require('path');
const { fileURLToPath } = require('url');

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: 'default',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
    },
    icon: path.join(__dirname, '../build/icon.png'), // 如果有图标的话
  });

  // 开发环境加载本地服务器，生产环境加载打包文件
  if (isDev) {
    win.loadURL('http://localhost:3000');
    // 开发环境自动打开开发者工具
    win.webContents.openDevTools();
  } else {
    // 生产环境加载打包后的文件
    win.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // 窗口关闭事件
  win.on('closed', () => {
    // 在macOS上，即使所有窗口关闭，应用通常也会继续运行
  });
}

// 当Electron完成初始化并准备创建浏览器窗口时调用
app.whenReady().then(() => {
  createWindow();

  // macOS特定：当没有窗口打开时，点击dock图标会重新创建窗口
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 所有窗口关闭时退出应用（macOS除外）
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// 安全：防止新窗口打开
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
  });
});
