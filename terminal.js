export function initTerminalApp(wm, vfs) {
  let cwd = '/home/banana';

  const container = document.createElement('div');
  container.className = 'terminal-container';
  container.innerHTML = `
    <div class="terminal-body">
      <div class="terminal-output">Banana OS Core Shell [Version 1.0.0]\nType 'help' for commands list.\n</div>
      <div class="terminal-input-row">
        <span class="terminal-prompt">banana@os:${cwd}$</span>
        <input type="text" class="terminal-input" autofocus />
      </div>
    </div>
  `;

  const output = container.querySelector('.terminal-output');
  const input = container.querySelector('.terminal-input');
  const prompt = container.querySelector('.terminal-prompt');

  const updatePrompt = () => {
    prompt.innerText = `banana@os:${cwd}$`;
  };

  const handleCommand = (rawCmd) => {
    const line = rawCmd.trim();
    if (!line) return;

    const [cmd, ...args] = line.split(' ');
    output.innerText += `${prompt.innerText} ${line}\n`;

    switch (cmd) {
      case 'help':
        output.innerText += "Commands: ls, cd, pwd, cat, touch, mkdir, clear, banana-info\n";
        break;
      case 'pwd':
        output.innerText += `${cwd}\n`;
        break;
      case 'clear':
        output.innerText = '';
        break;
      case 'ls': {
        try {
          const items = vfs.readDir(args[0] || '.', cwd);
          const list = items.map(i => i.type === 'dir' ? `[${i.name}]` : i.name).join('  ');
          output.innerText += `${list}\n`;
        } catch (e) {
          output.innerText += `ls: ${e.message}\n`;
        }
        break;
      }
      case 'cd': {
        const target = args[0] || '/home/banana';
        const newPath = vfs.normalizePath(target, cwd);
        const node = vfs.resolveNode(newPath);
        if (node && node.type === 'dir') {
          cwd = newPath;
          updatePrompt();
        } else {
          output.innerText += `cd: no such directory: ${target}\n`;
        }
        break;
      }
      case 'cat': {
        if (!args[0]) {
          output.innerText += "cat: missing file operand\n";
          break;
        }
        try {
          output.innerText += `${vfs.readFile(args[0], cwd)}\n`;
        } catch (e) {
          output.innerText += `cat: ${e.message}\n`;
        }
        break;
      }
      case 'touch': {
        if (!args[0]) {
          output.innerText += "touch: missing file operand\n";
          break;
        }
        try {
          vfs.writeFile(args[0], '', cwd);
        } catch (e) {
          output.innerText += `touch: ${e.message}\n`;
        }
        break;
      }
      case 'mkdir': {
        if (!args[0]) {
          output.innerText += "mkdir: missing directory operand\n";
          break;
        }
        try {
          vfs.mkdir(args[0], cwd);
        } catch (e) {
          output.innerText += `mkdir: ${e.message}\n`;
        }
        break;
      }
      case 'banana-info':
        output.innerText += `
   🍌  Banana OS Web Edition
   OS: BananaOS 1.0 (x86_64 Web Sandbox)
   Kernel: HTML5/ES6 Engine
   Shell: BananaSH
   Memory: 4096MB Emulated Virtual RAM
\n`;
        break;
      default:
        output.innerText += `${cmd}: command not found\n`;
    }

    container.querySelector('.terminal-body').scrollTop = container.querySelector('.terminal-body').scrollHeight;
  };

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      handleCommand(input.value);
      input.value = '';
    }
  });

  wm.createWindow({
    id: 'terminal',
    title: 'Banana Terminal',
    icon: '💻',
    width: 600,
    height: 380,
    content: container
  });
}