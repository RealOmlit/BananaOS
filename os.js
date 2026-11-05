import { VirtualFileSystem } from './vfs.js';
import { WindowManager } from './wm.js';
import { initBrowserApp } from './apps/browser.js';
import { initVirtualBoxApp } from './apps/virtualbox.js';
import { initTerminalApp } from './apps/terminal.js';
import { initEditorApp } from './apps/editor.js';
import { initFileManagerApp } from './apps/files.js';

document.addEventListener('DOMContentLoaded', () => {
  const desktopEl = document.getElementById('desktop');
  const taskbarPillsEl = document.getElementById('taskbar-pills');
  const startBtn = document.getElementById('start-btn');
  const startMenu = document.getElementById('start-menu');
  const trayClock = document.getElementById('tray-clock');

  // Core Subsystems
  const vfs = new VirtualFileSystem();
  const wm = new WindowManager(desktopEl, taskbarPillsEl);

  // App Launcher Dispatcher
  const launchApp = (appName, params) => {
    switch (appName) {
      case 'browser':
        initBrowserApp(wm);
        break;
      case 'virtualbox':
        initVirtualBoxApp(wm);
        break;
      case 'terminal':
        initTerminalApp(wm, vfs);
        break;
      case 'editor':
        initEditorApp(wm, vfs, params);
        break;
      case 'files':
        initFileManagerApp(wm, vfs, (filePath) => launchApp('editor', filePath));
        break;
      default:
        console.warn(`Unknown application: ${appName}`);
    }
    startMenu.classList.add('hidden');
  };

  // Bind Desktop Shortcuts
  document.querySelectorAll('.desktop-shortcut').forEach(el => {
    el.addEventListener('dblclick', () => launchApp(el.getAttribute('data-app')));
  });

  // Bind Start Menu Items
  document.querySelectorAll('.start-item').forEach(el => {
    el.addEventListener('click', () => launchApp(el.getAttribute('data-app')));
  });

  // Start Menu Toggle
  startBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    startMenu.classList.toggle('hidden');
  });

  document.addEventListener('click', (e) => {
    if (!startMenu.contains(e.target) && e.target !== startBtn) {
      startMenu.classList.add('hidden');
    }
  });

  // System Tray Clock
  const updateClock = () => {
    const now = new Date();
    trayClock.innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  setInterval(updateClock, 1000);
  updateClock();

  // Initial welcome launch
  launchApp('terminal');
});