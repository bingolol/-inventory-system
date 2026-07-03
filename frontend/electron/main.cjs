const { app, BrowserWindow, Menu } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')

const BACKEND_PORT = 8000

let mainWindow = null
let backendProcess = null

const isDev = !app.isPackaged

// ── 全局单实例锁：同一时刻只允许运行一个应用实例 ──
// 第二次启动时聚焦已有窗口，而不是创建新窗口
const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  // 已有实例在运行，当前进程立即退出
  app.quit()
} else {
  app.on('second-instance', () => {
    // 有人试图启动第二个实例：聚焦已有窗口
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      if (!mainWindow.isVisible()) mainWindow.show()
      mainWindow.focus()
    }
  })

  app.on('ready', async () => {
    Menu.setApplicationMenu(null)
    try {
      await startBackend()
      createWindow()
    } catch (err) {
      console.error('[electron] 启动失败:', err.message)
      app.quit()
    }
  })

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit()
  })

  app.on('before-quit', () => {
    if (backendProcess) { backendProcess.kill(); backendProcess = null }
  })

  app.on('activate', () => {
    if (mainWindow === null) createWindow()
  })
}

const STARTUP_TIMEOUT = 60000

function getBackendPath() {
  if (isDev) {
    const venvPython = path.join(__dirname, '..', '..', 'venv', 'Scripts', 'python.exe')
    const mainPy = path.join(__dirname, '..', '..', 'backend', 'main.py')
    const python = require('fs').existsSync(venvPython) ? venvPython : 'python'
    return { cmd: python, args: [mainPy] }
  }
  return { cmd: path.join(process.resourcesPath, 'backend.exe'), args: [] }
}

function waitForServer(port, timeout = 30000) {
  const start = Date.now()
  return new Promise((resolve, reject) => {
    function check() {
      const req = http.get(`http://127.0.0.1:${port}/api/auth/me`, (res) => {
        res.resume()
        resolve()
      })
      req.on('error', () => {
        if (Date.now() - start > timeout) {
          reject(new Error(`服务启动超时(${timeout}ms)`))
        } else {
          setTimeout(check, 300)
        }
      })
      req.setTimeout(2000, () => { req.destroy() })
    }
    check()
  })
}

async function startBackend() {
  const { cmd, args } = getBackendPath()
  const cwd = isDev ? path.dirname(args[0]) : path.dirname(cmd)
  backendProcess = spawn(cmd, args, {
    cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, INVENTORY_PORT: String(BACKEND_PORT) },
  })
  backendProcess.stdout.on('data', (d) => process.stdout.write(`[backend] ${d}`))
  backendProcess.stderr.on('data', (d) => process.stderr.write(`[backend] ${d}`))
  backendProcess.on('exit', (code) => {
    console.error(`[backend] 进程退出，code=${code}`)
    if (code !== 0 && mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.loadURL(`data:text/html,<h2>后端启动失败</h2><p>退出码: ${code}</p>`)
    }
  })
  await waitForServer(BACKEND_PORT)
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 600,
    center: true,
    show: false,
    title: '进销存管理系统',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      devTools: isDev,
    },
  })

  const ts = Date.now()
  mainWindow.loadURL(`http://127.0.0.1:${BACKEND_PORT}?_=${ts}`)
  mainWindow.once('ready-to-show', () => mainWindow.show())
  mainWindow.on('closed', () => { mainWindow = null })
  mainWindow.webContents.on('did-fail-load', (e, code, desc) => {
    console.error(`[electron] 加载失败: ${code} ${desc}`)
  })
  mainWindow.webContents.on('context-menu', (e) => e.preventDefault())
}
