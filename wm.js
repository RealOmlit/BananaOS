export class WindowManager {
  constructor(desktopElement, taskbarPillsElement) {
    this.desktop = desktopElement;
    this.taskbarPills = taskbarPillsElement;
    this.windows = new Map();
    this.activeWindow = null;
    this.zIndexCounter = 100;
  }

  createWindow({ id, title, icon = '🍌', width = 640, height = 440, content }) {
    if (this.windows.has(id)) {
      this.bringToFront(id);
      return this.windows.get(id);
    }

    const winEl = document.createElement('div');
    winEl.className = 'os-window';
    winEl.id = `win-${id}`;
    winEl.style.width = `${width}px`;
    winEl.style.height = `${height}px`;

    // Cascade offset placement
    const offset = (this.windows.size * 28) % 180 + 40;
    winEl.style.top = `${offset}px`;
    winEl.style.left = `${offset}px`;
    winEl.style.zIndex = ++this.zIndexCounter;

    winEl.innerHTML = `
      <div class="window-header">
        <div class="window-title"><span>${icon}</span> ${title}</div>
        <div class="window-controls">
          <button class="win-btn minimize-btn">—</button>
          <button class="win-btn maximize-btn">□</button>
          <button class="win-btn close-btn">✕</button>
        </div>
      </div>
      <div class="window-body"></div>
      <div class="window-resize-handle"></div>
    `;

    const bodyEl = winEl.querySelector('.window-body');
    if (typeof content === 'string') {
      bodyEl.innerHTML = content;
    } else if (content instanceof HTMLElement) {
      bodyEl.appendChild(content);
    }

    this.desktop.appendChild(winEl);

    // Taskbar entry
    const taskbarItem = document.createElement('div');
    taskbarItem.className = 'taskbar-pill active';
    taskbarItem.innerHTML = `<span>${icon}</span> ${title}`;
    taskbarItem.addEventListener('click', () => this.toggleMinimize(id));
    this.taskbarPills.appendChild(taskbarItem);

    const winObj = {
      id,
      element: winEl,
      taskbarItem,
      isMaximized: false,
      prevBounds: null
    };

    this.windows.set(id, winObj);
    this.bringToFront(id);
    this.attachEvents(winObj);

    return winObj;
  }

  bringToFront(id) {
    const win = this.windows.get(id);
    if (!win) return;

    win.element.style.zIndex = ++this.zIndexCounter;
    this.activeWindow = id;

    this.windows.forEach(w => {
      w.element.classList.remove('active');
      w.taskbarItem.classList.remove('active');
    });

    win.element.classList.remove('minimized');
    win.element.classList.add('active');
    win.taskbarItem.classList.add('active');
  }

  toggleMinimize(id) {
    const win = this.windows.get(id);
    if (!win) return;

    if (win.element.classList.contains('minimized')) {
      win.element.classList.remove('minimized');
      this.bringToFront(id);
    } else if (this.activeWindow === id) {
      win.element.classList.add('minimized');
      win.taskbarItem.classList.remove('active');
      this.activeWindow = null;
    } else {
      this.bringToFront(id);
    }
  }

  toggleMaximize(id) {
    const win = this.windows.get(id);
    if (!win) return;

    if (!win.isMaximized) {
      win.prevBounds = {
        top: win.element.style.top,
        left: win.element.style.left,
        width: win.element.style.width,
        height: win.element.style.height
      };
      win.element.classList.add('maximized');
      win.isMaximized = true;
    } else {
      win.element.classList.remove('maximized');
      win.element.style.top = win.prevBounds.top;
      win.element.style.left = win.prevBounds.left;
      win.element.style.width = win.prevBounds.width;
      win.element.style.height = win.prevBounds.height;
      win.isMaximized = false;
    }
  }

  closeWindow(id) {
    const win = this.windows.get(id);
    if (!win) return;

    win.element.remove();
    win.taskbarItem.remove();
    this.windows.delete(id);
  }

  attachEvents(win) {
    const header = win.element.querySelector('.window-header');
    const resizeHandle = win.element.querySelector('.window-resize-handle');

    win.element.addEventListener('mousedown', () => this.bringToFront(win.id));

    win.element.querySelector('.minimize-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleMinimize(win.id);
    });

    win.element.querySelector('.maximize-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleMaximize(win.id);
    });

    win.element.querySelector('.close-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      this.closeWindow(win.id);
    });

    // Window Dragging Logic
    header.addEventListener('mousedown', (e) => {
      if (win.isMaximized) return;
      let startX = e.clientX;
      let startY = e.clientY;
      let initialLeft = win.element.offsetLeft;
      let initialTop = win.element.offsetTop;

      const onMouseMove = (moveEvent) => {
        const dx = moveEvent.clientX - startX;
        const dy = moveEvent.clientY - startY;
        win.element.style.left = `${Math.max(0, initialLeft + dx)}px`;
        win.element.style.top = `${Math.max(0, initialTop + dy)}px`;
      };

      const onMouseUp = () => {
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    });

    // Window Resizing Logic
    resizeHandle.addEventListener('mousedown', (e) => {
      e.stopPropagation();
      let startX = e.clientX;
      let startY = e.clientY;
      let initialW = win.element.offsetWidth;
      let initialH = win.element.offsetHeight;

      const onMouseMove = (moveEvent) => {
        win.element.style.width = `${Math.max(260, initialW + (moveEvent.clientX - startX))}px`;
        win.element.style.height = `${Math.max(160, initialH + (moveEvent.clientY - startY))}px`;
      };

      const onMouseUp = () => {
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    });
  }
}