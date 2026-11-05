export function initBrowserApp(wm) {
  const container = document.createElement('div');
  container.className = 'browser-container';
  container.innerHTML = `
    <div class="browser-toolbar">
      <button class="nav-btn btn-back">‹</button>
      <button class="nav-btn btn-forward">›</button>
      <button class="nav-btn btn-reload">⟳</button>
      <input type="text" class="browser-address-bar" value="https://example.com" />
      <button class="btn-go">Go</button>
    </div>
    <div class="browser-viewport">
      <iframe class="browser-iframe" sandbox="allow-forms allow-scripts allow-same-origin"></iframe>
    </div>
  `;

  const input = container.querySelector('.browser-address-bar');
  const iframe = container.querySelector('.browser-iframe');
  const goBtn = container.querySelector('.btn-go');
  const reloadBtn = container.querySelector('.btn-reload');

  const navigate = () => {
    let url = input.value.trim();
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
      input.value = url;
    }
    // Route traffic through the Banana OS CORS bypass proxy backend
    iframe.src = `/api/proxy?url=${encodeURIComponent(url)}`;
  };

  goBtn.addEventListener('click', navigate);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') navigate();
  });
  reloadBtn.addEventListener('click', () => {
    iframe.src = iframe.src;
  });

  wm.createWindow({
    id: 'browser',
    title: 'Banana Web Explorer',
    icon: '🌐',
    width: 820,
    height: 520,
    content: container
  });

  navigate();
}