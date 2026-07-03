const { app, BrowserWindow, ipcMain, Notification } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;

function startBackend() {
    // Start the Peq Python backend
    const backendPath = path.join(__dirname, '..', 'backend', 'app', 'main.py');
    backendProcess = spawn('python3', [backendPath], {
        env: { ...process.env, PORT: '8765' },
        stdio: 'pipe'
    });
    
    backendProcess.stdout.on('data', (data) => {
        console.log(`Backend: ${data}`);
    });
    
    backendProcess.stderr.on('data', (data) => {
        console.error(`Backend error: ${data}`);
    });
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        title: 'Peq — AI Automation Engine',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false
        },
        show: false
    });
    
    // Load the dashboard
    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
    
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });
    
    // Update API base to point to local backend
    mainWindow.webContents.executeJavaScript(`
        window.PEQ_API = 'http://localhost:8765/api/v1';
    `);
    
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// IPC handlers for desktop features
ipcMain.handle('show-notification', (event, { title, body }) => {
    new Notification({ title, body }).show();
});

ipcMain.handle('get-api-base', () => {
    return 'http://localhost:8765/api/v1';
});

app.whenReady().then(() => {
    startBackend();
    // Give backend time to start
    setTimeout(createWindow, 2000);
    
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        if (backendProcess) {
            backendProcess.kill();
        }
        app.quit();
    }
});

app.on('before-quit', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
});
