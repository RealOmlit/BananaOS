export class VirtualFileSystem {
  constructor() {
    this.storageKey = 'banana_os_vfs_root';
    this.root = this.load() || this.createDefaultFS();
  }

  createDefaultFS() {
    const defaultFS = {
      name: '/',
      type: 'dir',
      children: {
        'home': {
          type: 'dir',
          children: {
            'banana': {
              type: 'dir',
              children: {
                'Desktop': {
                  type: 'dir',
                  children: {
                    'welcome.txt': {
                      type: 'file',
                      content: 'Welcome to Banana OS!\nFully functional web operating system.'
                    }
                  }
                },
                'Documents': {
                  type: 'dir',
                  children: {
                    'todo.txt': {
                      type: 'file',
                      content: '1. Test Proxy Browser\n2. Boot sandbox container\n3. Enjoy Banana OS'
                    }
                  }
                }
              }
            }
          }
        },
        'bin': { type: 'dir', children: {} },
        'etc': { type: 'dir', children: {} }
      }
    };
    this.save(defaultFS);
    return defaultFS;
  }

  load() {
    try {
      const data = localStorage.getItem(this.storageKey);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.warn('VFS storage load failed:', e);
      return null;
    }
  }

  save(data = this.root) {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(data));
    } catch (e) {
      console.error('VFS storage save failed:', e);
    }
  }

  resolveNode(absolutePath) {
    const parts = absolutePath.split('/').filter(Boolean);
    let curr = this.root;

    for (const part of parts) {
      if (curr.type !== 'dir' || !curr.children[part]) {
        return null;
      }
      curr = curr.children[part];
    }
    return curr;
  }

  normalizePath(path, cwd = '/home/banana') {
    let raw = path.startsWith('/') ? path : `${cwd}/${path}`;
    const segments = raw.split('/').filter(Boolean);
    const resolved = [];

    for (const segment of segments) {
      if (segment === '.') continue;
      if (segment === '..') {
        resolved.pop();
      } else {
        resolved.push(segment);
      }
    }
    return '/' + resolved.join('/');
  }

  readFile(path, cwd) {
    const fullPath = this.normalizePath(path, cwd);
    const node = this.resolveNode(fullPath);
    if (!node) throw new Error(`File not found: ${path}`);
    if (node.type !== 'file') throw new Error(`Not a file: ${path}`);
    return node.content;
  }

  writeFile(path, content, cwd) {
    const fullPath = this.normalizePath(path, cwd);
    const parts = fullPath.split('/').filter(Boolean);
    const fileName = parts.pop();
    const parentPath = '/' + parts.join('/');
    const parent = this.resolveNode(parentPath);

    if (!parent || parent.type !== 'dir') {
      throw new Error(`Directory not found: ${parentPath}`);
    }

    parent.children[fileName] = {
      type: 'file',
      content: content
    };
    this.save();
  }

  mkdir(path, cwd) {
    const fullPath = this.normalizePath(path, cwd);
    const parts = fullPath.split('/').filter(Boolean);
    const dirName = parts.pop();
    const parentPath = '/' + parts.join('/');
    const parent = this.resolveNode(parentPath);

    if (!parent || parent.type !== 'dir') {
      throw new Error(`Directory not found: ${parentPath}`);
    }
    if (parent.children[dirName]) {
      throw new Error(`File or directory already exists: ${dirName}`);
    }

    parent.children[dirName] = { type: 'dir', children: {} };
    this.save();
  }

  readDir(path, cwd) {
    const fullPath = this.normalizePath(path, cwd);
    const node = this.resolveNode(fullPath);
    if (!node) throw new Error(`Directory not found: ${path}`);
    if (node.type !== 'dir') throw new Error(`Not a directory: ${path}`);
    return Object.keys(node.children).map(name => ({
      name,
      type: node.children[name].type
    }));
  }
}