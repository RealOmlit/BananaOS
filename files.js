// public/js/apps/editor.js
export function initEditorApp(wm, vfs, initialFile = '/home/banana/Desktop/welcome.txt') {
  const container = document.createElement('div');
  container.className = 'editor-container';
  container.innerHTML = `
    <div class="editor-toolbar">
      <input type="text" class="editor-filename" value="${initialFile}" />
      <button class="editor-save-btn">Save</button>
    </div>
    <textarea class="editor-textarea"></textarea>
  `;

  const filenameInput = container.querySelector('.editor-filename');
  const textarea = container.querySelector('.editor-textarea');
  const saveBtn = container.querySelector('.editor-save-btn');

  try {
    textarea.value = vfs.readFile(initialFile);
  } catch {
    textarea.value = '';
  }

  saveBtn.addEventListener('click', () => {
    try {
      vfs.writeFile(filenameInput.value, textarea.value);
      alert('File successfully saved to VFS.');
    } catch (e) {
      alert(`Save error: ${e.message}`);
    }
  });

  wm.createWindow({
    id: 'editor',
    title: 'Banana Notepad',
    icon: '📝',
    width: 540,
    height: 400,
    content: container
  });
}

// public/js/apps/files.js
export function initFileManagerApp(wm, vfs, openEditorFn) {
  let cwd = '/home/banana';
  const container = document.createElement('div');
  container.className = 'fm-container';
  container.innerHTML = `
    <div class="fm-toolbar">
      <button class="fm-up-btn">↑ Up</button>
      <input type="text" class="fm-path" value="${cwd}" readonly />
    </div>
    <div class="fm-grid"></div>
  `;

  const grid = container.querySelector('.fm-grid');
  const pathInput = container.querySelector('.fm-path');
  const upBtn = container.querySelector('.fm-up-btn');

  const render = () => {
    pathInput.value = cwd;
    grid.innerHTML = '';
    try {
      const items = vfs.readDir(cwd);
      items.forEach(item => {
        const itemEl = document.createElement('div');
        itemEl.className = 'fm-item';
        itemEl.innerHTML = `
          <div class="fm-item-icon">${item.type === 'dir' ? '📁' : '📄'}</div>
          <div class="fm-item-name">${item.name}</div>
        `;
        itemEl.addEventListener('dblclick', () => {
          if (item.type === 'dir') {
            cwd = vfs.normalizePath(item.name, cwd);
            render();
          } else {
            openEditorFn(vfs.normalizePath(item.name, cwd));
          }
        });
        grid.appendChild(itemEl);
      });
    } catch (e) {
      grid.innerHTML = `<div class="fm-error">Error: ${e.message}</div>`;
    }
  };

  upBtn.addEventListener('click', () => {
    cwd = vfs.normalizePath('..', cwd);
    render();
  });

  render();

  wm.createWindow({
    id: 'files',
    title: 'File Manager',
    icon: '📁',
    width: 580,
    height: 420,
    content: container
  });
}