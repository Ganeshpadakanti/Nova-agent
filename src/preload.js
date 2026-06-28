const { ipcRenderer } = require('electron')
window.novaIPC = {
  drag:     (dx, dy) => ipcRenderer.send('window-drag', { dx, dy }),
  setState: (state)  => ipcRenderer.send('nova-state', state)
}
