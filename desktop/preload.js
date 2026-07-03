const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('flowmind', {
    showNotification: (title, body) => ipcRenderer.invoke('show-notification', { title, body }),
    getApiBase: () => ipcRenderer.invoke('get-api-base'),
    isDesktop: true
});
