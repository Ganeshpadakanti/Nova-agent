const { app, BrowserWindow, Tray, Menu, ipcMain, screen } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const fs = require('fs')

let novaWindow    = null
let tray          = null
let pythonProcess = null

function getApiKey() {
  const settingsPath = path.join(app.getPath('userData'), 'nova-settings.json')
  try { return JSON.parse(fs.readFileSync(settingsPath, 'utf8')).apiKey || '' }
  catch { return '' }
}

function saveSettings(settings) {
  const settingsPath = path.join(app.getPath('userData'), 'nova-settings.json')
  fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2))
}

// ─── PYTHON BRAIN ─────────────────────────────────────────────────────────────
function startPythonBrain() {
  const scriptPath = path.join(__dirname, 'voice_brain.py')
  const apiKey     = getApiKey()
  console.log('Starting Python brain...')

  pythonProcess = spawn('python', [scriptPath, apiKey], {
    cwd: path.join(__dirname, '..'),
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    shell: true,
    windowsHide: true
  })

  let buffer = ''
  pythonProcess.stdout.on('data', (data) => {
    buffer += data.toString()
    const lines = buffer.split('\n'); buffer = lines.pop()
    for (const line of lines) {
      const t = line.trim(); if (!t) continue
      try { handlePythonMessage(JSON.parse(t)) } catch { console.log('py:', t) }
    }
  })
  pythonProcess.stderr.on('data', (d) => console.error('py err:', d.toString()))
  pythonProcess.on('error', (e) => console.error('py start err:', e.message))
  pythonProcess.on('close', (code) => {
    console.log('Python exited:', code)
    setTimeout(() => { if (novaWindow && !novaWindow.isDestroyed()) startPythonBrain() }, 3000)
  })
}

function handlePythonMessage({ event, data }) {
  console.log('[py]', event, data)
  if (!novaWindow || novaWindow.isDestroyed()) return
  switch (event) {
    case 'state': novaWindow.webContents.send('nova-set-state', data); break
    case 'wake':  novaWindow.webContents.send('nova-set-state', 'listening'); break
    case 'log':   console.log('[Brain]', data); break
    case 'error': console.error('[Brain ERR]', data); break
  }
}

// ─── NOVA WINDOW (draggable, no cursor tracking) ──────────────────────────────
function createNovaWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  novaWindow = new BrowserWindow({
    width: 120,
    height: 120,
    x: width - 160,
    y: height - 160,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    focusable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      preload: path.join(__dirname, 'preload.js')
    }
  })

  novaWindow.setIgnoreMouseEvents(false)
  novaWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
  novaWindow.webContents.on('did-finish-load', () => {
    console.log('Nova window loaded!')
    setTimeout(startPythonBrain, 1000)
  })
}

// ─── TRAY ─────────────────────────────────────────────────────────────────────
function createTray() {
  const iconPath = path.join(__dirname, '..', 'assets', 'tray-icon.png')
  try { tray = new Tray(iconPath) } catch { console.log('no tray icon') }

  const menu = Menu.buildFromTemplate([
    { label: 'Nova Agent', enabled: false },
    { type: 'separator' },
    { label: 'Show Nova', click: () => novaWindow.show() },
    { label: 'Hide Nova', click: () => novaWindow.hide() },
    { type: 'separator' },
    { label: 'Settings',  click: () => openSettings() },
    { type: 'separator' },
    { label: 'Quit', click: () => {
        if (pythonProcess) pythonProcess.kill()
        app.quit()
    }}
  ])

  if (tray) {
    tray.setToolTip('Nova Agent')
    tray.setContextMenu(menu)
    tray.on('click', () => novaWindow.isVisible() ? novaWindow.hide() : novaWindow.show())
  }
}

function openSettings() {
  const win = new BrowserWindow({
    width: 420, height: 520, title: 'Nova Settings',
    webPreferences: { nodeIntegration: true, contextIsolation: false }
  })
  win.loadFile(path.join(__dirname, 'renderer', 'settings.html'))
  win.setMenu(null)
}

// ─── IPC ──────────────────────────────────────────────────────────────────────
ipcMain.on('window-drag', (event, { dx, dy }) => {
  try {
    const [x, y] = novaWindow.getPosition()
    novaWindow.setPosition(x + dx, y + dy)
  } catch (e) {}
})

ipcMain.on('save-settings', (e, s) => {
  saveSettings(s)
  if (pythonProcess) { pythonProcess.kill(); setTimeout(startPythonBrain, 1500) }
})

// ─── APP ──────────────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  createNovaWindow()
  createTray()
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createNovaWindow() })
})
app.on('window-all-closed', (e) => e.preventDefault())
app.on('before-quit', () => { if (pythonProcess) pythonProcess.kill() })
