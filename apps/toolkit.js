const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[char]));
const readData = key => { try { return JSON.parse(localStorage.getItem(key) || "null"); } catch { return null; } };
const writeData = (key, value) => localStorage.setItem(key, JSON.stringify(value));
const input = (label, type = "text", value = "") => `<label class="tool-field">${label}<input class="app-input" type="${type}" value="${escapeHTML(value)}"></label>`;
const button = (label, action, primary = false) => `<button class="app-button${primary ? " primary" : ""}" data-action="${action}" type="button">${label}</button>`;

export function launchToolApp(app, { createWindow, state, toast }) {
  const root = document.createElement("div");
  root.className = "app tool-app";
  const key = `banana-app-${app.id}`;
  const saved = readData(key);
  let onClose = null;
  const savedText = typeof saved === "string" ? saved : "";

  switch (app.id) {
    case "editor":
    case "code-editor":
    case "markdown": {
      const source = (typeof saved === "string" ? saved : saved?.text) || (app.id === "markdown" ? "# Welcome\n\nWrite **Markdown** on the left." : "");
      root.innerHTML = `<div class="tool-toolbar">${input("File name", "text", saved?.name || `${app.id === "markdown" ? "readme.md" : "untitled.txt"}`)}${button("Save", "save", true)}${app.id === "markdown" ? button("Preview", "preview") : ""}</div><textarea class="tool-editor" aria-label="${app.name}" spellcheck="false">${escapeHTML(source)}</textarea><pre class="tool-preview hidden"></pre><p class="tool-status" aria-live="polite">Saved in this browser</p>`;
      const area = root.querySelector(".tool-editor");
      const status = root.querySelector(".tool-status");
      root.querySelector('[data-action="save"]').addEventListener("click", () => { writeData(key, { name: root.querySelector("input").value, text: area.value }); status.textContent = "Saved locally"; });
      if (app.id === "markdown") root.querySelector('[data-action="preview"]').addEventListener("click", () => {
        const preview = root.querySelector(".tool-preview");
        preview.innerHTML = renderMarkdown(area.value);
        preview.classList.toggle("hidden");
      });
      if (app.id === "code-editor") {
        root.querySelector(".tool-toolbar").insertAdjacentHTML("beforeend", button("Highlight", "highlight"));
        root.querySelector('[data-action="highlight"]').onclick = () => {
          const preview = root.querySelector(".tool-preview") || root.appendChild(document.createElement("pre"));
          preview.className = "tool-preview code-highlight";
          preview.innerHTML = highlightCode(area.value);
        };
      }
      area.addEventListener("input", () => { if (app.id === "code-editor") status.textContent = `${area.value.split("\n").length} lines · ${area.value.length} characters`; });
      break;
    }
    case "monitor": {
      root.innerHTML = `<div class="tool-heading"><h2>System Monitor</h2><p>Live browser-tab estimates; these are not host operating-system metrics.</p></div><div class="monitor-grid"><div><label>CPU activity <b data-cpu>--%</b></label><progress data-cpu-bar max="100" value="0"></progress></div><div><label>Memory estimate <b data-memory>-- MB</b></label><progress data-memory-bar max="100" value="0"></progress></div><div><label>Storage used <b data-storage>-- KB</b></label><progress data-storage-bar max="100" value="0"></progress></div></div><p class="tool-status">Refreshes every second</p>`;
      const update = () => {
        const cpu = Math.round(8 + Math.random() * 35), memory = Math.round(performance.memory?.usedJSHeapSize / 1048576 || 48 + Math.random() * 70);
        const storage = Math.round(new Blob(Object.keys(localStorage).map(item => localStorage.getItem(item))).size / 1024);
        root.querySelector("[data-cpu]").textContent = `${cpu}%`; root.querySelector("[data-cpu-bar]").value = cpu;
        root.querySelector("[data-memory]").textContent = `${memory} MB`; root.querySelector("[data-memory-bar]").value = Math.min(100, memory / 8);
        root.querySelector("[data-storage]").textContent = `${storage} KB`; root.querySelector("[data-storage-bar]").value = Math.min(100, storage / 100);
      };
      update(); const timer = setInterval(update, 1000); onClose = () => clearInterval(timer);
      break;
    }
    case "clock":
    case "stopwatch": {
      root.innerHTML = `<div class="tool-clock"><output class="clock-readout">--:--:--</output><div class="tool-toolbar">${app.id === "clock" ? `<label class="tool-field">Alarm time<input class="app-input alarm-time" type="time"></label>${button("Set alarm", "alarm", true)}` : button("Start", "start", true)}${button(app.id === "clock" ? "Clear alarm" : "Reset", "reset")}</div><p class="tool-status" aria-live="polite"></p></div>`;
      const display = root.querySelector(".clock-readout"), status = root.querySelector(".tool-status");
      if (app.id === "clock") {
        const update = () => { const now = new Date(); display.textContent = now.toLocaleTimeString(); const alarm = readData("banana-clock-alarm"); if (alarm && now.toTimeString().slice(0, 5) === alarm && now.getSeconds() === 0) { status.textContent = "Alarm: time is up"; toast("Clock alarm"); } };
        update(); const timer = setInterval(update, 1000); onClose = () => clearInterval(timer);
        root.querySelector('[data-action="alarm"]').onclick = () => { const value = root.querySelector(".alarm-time").value; writeData("banana-clock-alarm", value); status.textContent = value ? `Alarm set for ${value}` : "Choose an alarm time first"; };
        root.querySelector('[data-action="reset"]').onclick = () => { localStorage.removeItem("banana-clock-alarm"); status.textContent = "Alarm cleared"; };
      } else {
        let started = 0, elapsed = 0, timer = null;
        const render = () => { const ms = elapsed + (started ? performance.now() - started : 0); display.textContent = `${(ms / 1000).toFixed(2)} s`; };
        root.querySelector('[data-action="start"]').onclick = event => { if (started) { elapsed += performance.now() - started; started = 0; clearInterval(timer); event.currentTarget.textContent = "Resume"; } else { started = performance.now(); timer = setInterval(render, 30); event.currentTarget.textContent = "Pause"; } render(); };
        root.querySelector('[data-action="reset"]').onclick = () => { started = 0; elapsed = 0; clearInterval(timer); render(); root.querySelector('[data-action="start"]').textContent = "Start"; };
        onClose = () => clearInterval(timer); render();
      }
      break;
    }
    case "weather":
      root.innerHTML = `<div class="weather-view"><p class="tool-eyebrow">OFFLINE DEMO · SAMPLE CONDITIONS</p><h2>☀️ 22°</h2><p>Clear skies · Light breeze</p><div class="weather-week">${["Mon","Tue","Wed","Thu","Fri"].map((day, i) => `<div><b>${day}</b><span>${["☀️","🌤️","☁️","🌦️","☀️"][i]}</span><small>${20 + i}° / ${13 + i}°</small></div>`).join("")}</div><p class="tool-status">Live forecasts need a weather service and network access.</p></div>`;
      break;
    case "recorder": {
      root.innerHTML = `<div class="tool-heading"><h2>Audio Recorder</h2><p>Microphone access is requested only after you press Record.</p></div><div class="tool-toolbar">${button("Record", "record", true)}${button("Stop", "stop")}</div><audio class="tool-audio" controls></audio><p class="tool-status" aria-live="polite">Ready</p>`;
      let stream, recorder, chunks = [];
      root.querySelector('[data-action="record"]').onclick = async () => {
        try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); recorder = new MediaRecorder(stream); chunks = []; recorder.ondataavailable = event => chunks.push(event.data); recorder.onstop = () => { root.querySelector("audio").src = URL.createObjectURL(new Blob(chunks, { type: recorder.mimeType })); root.querySelector(".tool-status").textContent = "Recording ready to play"; }; recorder.start(); root.querySelector(".tool-status").textContent = "Recording…"; }
        catch { root.querySelector(".tool-status").textContent = "Microphone permission was denied or is unavailable."; }
      };
      root.querySelector('[data-action="stop"]').onclick = () => { if (recorder?.state === "recording") recorder.stop(); stream?.getTracks().forEach(track => track.stop()); };
      onClose = () => { if (recorder?.state === "recording") recorder.stop(); stream?.getTracks().forEach(track => track.stop()); };
      break;
    }
    case "image-viewer":
    case "video-player":
    case "pdf": {
      const kind = app.id === "image-viewer" ? "image/*" : app.id === "video-player" ? "video/*" : "application/pdf";
      const tag = app.id === "image-viewer" ? "img" : app.id === "video-player" ? "video" : "iframe";
      root.innerHTML = `<div class="tool-toolbar"><label class="app-button">Open file<input class="file-open hidden-input" type="file" accept="${kind}"></label><span class="tool-status">Choose a local file</span></div><div class="media-stage">${tag === "iframe" ? `<iframe title="PDF preview"></iframe>` : `<${tag} ${tag === "video" ? "controls" : "alt=\"Local image preview\""}></${tag}>`}</div>`;
      const media = root.querySelector(tag), status = root.querySelector(".tool-status"); let objectURL;
      root.querySelector(".file-open").onchange = event => { const file = event.target.files?.[0]; if (!file) return; if (objectURL) URL.revokeObjectURL(objectURL); objectURL = URL.createObjectURL(file); media.src = objectURL; status.textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`; };
      onClose = () => { if (objectURL) URL.revokeObjectURL(objectURL); };
      break;
    }
    case "radio":
      root.innerHTML = `<div class="tool-heading"><h2>Web Radio</h2><p>Enter a direct, publicly playable audio-stream URL.</p></div><div class="tool-toolbar">${input("Stream URL", "url", "")}${button("Tune in", "tune", true)}</div><audio controls class="tool-audio"></audio><p class="tool-status">Third-party streams may block playback or require HTTPS.</p>`;
      root.querySelector('[data-action="tune"]').onclick = () => { try { const url = new URL(root.querySelector("input").value); if (!/^https?:$/.test(url.protocol)) throw new Error(); root.querySelector("audio").src = url.href; root.querySelector("audio").play().catch(() => {}); } catch { root.querySelector(".tool-status").textContent = "Enter a valid HTTP or HTTPS audio URL."; } };
      break;
    case "music": {
      root.innerHTML = `<div class="tool-heading"><h2>Music Player</h2><p>Choose an audio file on this device. The file is not uploaded.</p></div><div class="tool-toolbar"><label class="app-button">Open audio<input class="hidden-input audio-file" type="file" accept="audio/*"></label><span class="tool-status">No track loaded</span></div><audio class="tool-audio" controls></audio>`;
      let objectURL;
      root.querySelector(".audio-file").onchange = event => { const file = event.target.files?.[0]; if (!file) return; if (objectURL) URL.revokeObjectURL(objectURL); objectURL = URL.createObjectURL(file); root.querySelector("audio").src = objectURL; root.querySelector(".tool-status").textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`; };
      onClose = () => { if (objectURL) URL.revokeObjectURL(objectURL); };
      break;
    }
    case "email":
      root.innerHTML = `<div class="tool-heading"><h2>Local Mail</h2><p>This mock client does not connect to an email server.</p></div><form class="tool-form">${input("To", "email")}${input("Subject")}<label class="tool-field">Message<textarea class="app-input" rows="6"></textarea></label><button class="app-button primary">Save draft</button></form><div class="tool-list"></div>`;
      root.querySelector("form").onsubmit = event => { event.preventDefault(); const values = [...root.querySelectorAll("form input, form textarea")].map(field => field.value); const drafts = readData(key) || []; drafts.unshift({ to: values[0], subject: values[1], body: values[2], date: new Date().toLocaleString() }); writeData(key, drafts); root.querySelector(".tool-list").textContent = `Saved drafts: ${drafts.length}`; };
      break;
    case "chat":
      root.innerHTML = `<div class="tool-chat" aria-live="polite"></div><form class="tool-compose"><input class="app-input" aria-label="Message" placeholder="Write a message"><button class="app-button primary">Send</button></form>`;
      root.querySelector("form").onsubmit = event => { event.preventDefault(); const field = root.querySelector("input"), text = field.value.trim(); if (!text) return; const line = document.createElement("p"); line.textContent = `You: ${text}`; root.querySelector(".tool-chat").append(line); const reply = document.createElement("p"); reply.textContent = "Local demo: message received. No network connection was made."; root.querySelector(".tool-chat").append(reply); field.value = ""; };
      break;
    case "rss":
      root.innerHTML = `<div class="tool-heading"><h2>RSS Feed Reader</h2><p>Cross-origin feed fetches are restricted by CORS. Add a feed to your local reading list.</p></div><form class="tool-compose"><input class="app-input" type="url" placeholder="https://example.com/feed.xml" aria-label="Feed URL"><button class="app-button primary">Add feed</button></form><div class="tool-list"></div>`;
      root.querySelector("form").onsubmit = event => { event.preventDefault(); try { const url = new URL(root.querySelector("input").value); if (!/^https?:$/.test(url.protocol)) throw new Error(); const feeds = readData(key) || []; feeds.push(url.href); writeData(key, feeds); root.querySelector(".tool-list").innerHTML = feeds.map(feed => `<p>${escapeHTML(feed)}</p>`).join(""); } catch { toast("Enter a valid HTTP or HTTPS feed URL."); } };
      break;
    case "camera": {
      root.innerHTML = `<div class="tool-heading"><h2>Camera</h2><p>Your camera stays in this tab and is not recorded.</p></div><div class="tool-toolbar">${button("Start camera", "start", true)}${button("Stop", "stop")}</div><video class="camera-video" autoplay playsinline></video><p class="tool-status" aria-live="polite">Camera is off</p>`;
      let stream;
      root.querySelector('[data-action="start"]').onclick = async () => { try { stream = await navigator.mediaDevices.getUserMedia({ video: true }); root.querySelector("video").srcObject = stream; root.querySelector(".tool-status").textContent = "Camera active"; } catch { root.querySelector(".tool-status").textContent = "Camera permission was denied or is unavailable."; } };
      root.querySelector('[data-action="stop"]').onclick = () => { stream?.getTracks().forEach(track => track.stop()); stream = null; root.querySelector("video").srcObject = null; root.querySelector(".tool-status").textContent = "Camera is off"; };
      onClose = () => stream?.getTracks().forEach(track => track.stop());
      break;
    }
    case "ftp":
      root.innerHTML = `<div class="tool-heading"><h2>FTP Client Simulator</h2><p>FTP access is not available from a secure static browser app.</p></div><div class="tool-toolbar">${input("Host", "text", "files.example.test")}${button("Connect", "connect", true)}</div><div class="tool-list">📁 public<br>📄 readme.txt<br>📁 uploads</div><p class="tool-status">Simulation only · no credentials are requested or stored.</p>`;
      root.querySelector('[data-action="connect"]').onclick = () => { root.querySelector(".tool-status").textContent = `Showing a sample listing for ${root.querySelector("input").value || "demo host"}`; };
      break;
    case "color-picker":
      root.innerHTML = `<div class="tool-color"><input type="color" value="#f9d94c" aria-label="Choose a color"><output>#F9D94C</output>${button("Copy HEX", "copy", true)}<div class="tool-color-preview"></div></div>`;
      root.querySelector("input").oninput = event => { const value = event.target.value.toUpperCase(); root.querySelector("output").textContent = value; root.querySelector(".tool-color-preview").style.background = value; };
      root.querySelector('[data-action="copy"]').onclick = async () => { try { await navigator.clipboard.writeText(root.querySelector("output").textContent); toast("Color copied"); } catch { toast("Clipboard permission unavailable"); } };
      break;
    case "devtools":
      root.innerHTML = `<div class="tool-heading"><h2>Browser diagnostics</h2><p>Information exposed to this page by your browser.</p></div><dl class="tool-details">${[["User agent", navigator.userAgent], ["Language", navigator.language], ["Online", navigator.onLine], ["Viewport", `${innerWidth} × ${innerHeight}`], ["Storage", `${new Blob(Object.keys(localStorage).map(item => localStorage.getItem(item))).size} bytes`], ["Secure context", isSecureContext]].map(([label, value]) => `<dt>${label}</dt><dd>${escapeHTML(value)}</dd>`).join("")}</dl>`;
      break;
    case "icon-designer":
      root.innerHTML = `<div class="tool-toolbar">${input("Symbol", "text", "🍌")}${input("Background", "color", "#f9d94c")}${button("Download SVG", "download", true)}</div><div class="icon-preview">🍌</div>`;
      root.querySelectorAll("input").forEach(field => field.oninput = () => { const preview = root.querySelector(".icon-preview"); preview.textContent = root.querySelector('input[type="text"]').value.slice(0, 4); preview.style.background = root.querySelector('input[type="color"]').value; });
      root.querySelector('[data-action="download"]').onclick = () => { const symbol = root.querySelector('input[type="text"]').value.slice(0, 4); const color = root.querySelector('input[type="color"]').value; download(`icon.svg`, `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect width="128" height="128" rx="24" fill="${color}"/><text x="64" y="84" text-anchor="middle" font-size="64">${escapeHTML(symbol)}</text></svg>`, "image/svg+xml"); };
      break;
    case "logs":
      root.innerHTML = `<div class="tool-heading"><h2>System Logs</h2><p>Recent browser-local events and app actions.</p></div><div class="tool-list">${(readData("banana-os-logs") || []).slice(-100).reverse().map(entry => `<p><time>${escapeHTML(entry.time)}</time> ${escapeHTML(entry.message)}</p>`).join("") || "No saved log entries yet."}</div>${button("Clear logs", "clear")}`;
      root.querySelector('[data-action="clear"]').onclick = () => { writeData("banana-os-logs", []); root.querySelector(".tool-list").textContent = "Logs cleared"; };
      break;
    case "help":
      root.innerHTML = `<div class="tool-heading"><h2>BananaOS Help</h2></div><div class="tool-list"><h3>Files and privacy</h3><p>Your app data is saved in this browser's local storage. Do not store passwords or sensitive data here.</p><h3>Gust Browser</h3><p>External sites load directly in a sandboxed frame when the site permits embedding. Static pages cannot bypass another site's CORS or frame restrictions.</p><h3>Permissions</h3><p>Camera and microphone access are requested only by their apps and require a secure context such as HTTPS.</p><h3>Games</h3><p>Game Center reads the bundled UBG catalog. Only game files actually included in the repository can be played from GitHub Pages.</p></div>`;
      break;
    case "spreadsheet": {
      const rows = saved?.rows || Array.from({ length: 8 }, () => Array(5).fill(""));
      root.innerHTML = `<div class="tool-toolbar">${button("Save", "save", true)}<span class="tool-status">Edit cells, then save</span></div><div class="sheet-wrap"><table class="tool-sheet"><tbody>${rows.map((row, r) => `<tr>${row.map((cell, c) => `<td><input aria-label="Cell ${r + 1}, ${c + 1}" data-row="${r}" data-col="${c}" value="${escapeHTML(cell)}"></td>`).join("")}</tr>`).join("")}</tbody></table></div><p class="tool-status" data-total>Total of numeric cells: 0</p>`;
      const update = () => { const total = [...root.querySelectorAll(".tool-sheet input")].reduce((sum, field) => sum + (Number(field.value) || 0), 0); root.querySelector("[data-total]").textContent = `Total of numeric cells: ${total}`; };
      root.querySelectorAll(".tool-sheet input").forEach(field => field.oninput = update); update();
      root.querySelector('[data-action="save"]').onclick = () => { const cells = [...root.querySelectorAll(".tool-sheet input")]; const next = Array.from({ length: 8 }, () => Array(5).fill("")); cells.forEach(field => { next[Number(field.dataset.row)][Number(field.dataset.col)] = field.value; }); writeData(key, { rows: next }); toast("Spreadsheet saved locally"); };
      break;
    }
    case "presentation": {
      const slides = saved?.slides || ["A new presentation\nAdd your key idea here."];
      let index = 0;
      root.innerHTML = `<div class="tool-toolbar">${button("Previous", "previous")}${button("Next", "next")}${button("Add slide", "add", true)}${button("Save", "save")}<span class="tool-status"></span></div><textarea class="tool-slide" aria-label="Slide content"></textarea><div class="slide-preview"></div>`;
      const area = root.querySelector(".tool-slide"), status = root.querySelector(".tool-status");
      const sync = () => { area.value = slides[index] || ""; status.textContent = `Slide ${index + 1} of ${slides.length}`; root.querySelector(".slide-preview").textContent = area.value; };
      area.oninput = () => { slides[index] = area.value; root.querySelector(".slide-preview").textContent = area.value; };
      root.querySelector('[data-action="previous"]').onclick = () => { slides[index] = area.value; index = (index - 1 + slides.length) % slides.length; sync(); };
      root.querySelector('[data-action="next"]').onclick = () => { slides[index] = area.value; index = (index + 1) % slides.length; sync(); };
      root.querySelector('[data-action="add"]').onclick = () => { slides[index] = area.value; slides.push("New slide"); index = slides.length - 1; sync(); };
      root.querySelector('[data-action="save"]').onclick = () => { slides[index] = area.value; writeData(key, { slides }); toast("Presentation saved"); }; sync();
      break;
    }
    case "pomodoro": {
      root.innerHTML = `<div class="tool-clock"><output class="clock-readout">25:00</output><label class="tool-field">Focus minutes<input class="app-input" type="number" min="1" max="120" value="25"></label><div class="tool-toolbar">${button("Start", "start", true)}${button("Reset", "reset")}</div><p class="tool-status">Focus session</p></div>`;
      let remaining = 1500, timer = null;
      const display = root.querySelector("output"); const render = () => { display.textContent = `${String(Math.floor(remaining / 60)).padStart(2, "0")}:${String(remaining % 60).padStart(2, "0")}`; };
      root.querySelector('[data-action="start"]').onclick = event => { if (timer) { clearInterval(timer); timer = null; event.currentTarget.textContent = "Resume"; return; } if (remaining === 1500) remaining = Math.max(60, Number(root.querySelector("input").value) * 60); event.currentTarget.textContent = "Pause"; timer = setInterval(() => { remaining--; render(); if (remaining <= 0) { clearInterval(timer); timer = null; root.querySelector(".tool-status").textContent = "Focus session complete"; toast("Pomodoro complete"); } }, 1000); };
      root.querySelector('[data-action="reset"]').onclick = () => { clearInterval(timer); timer = null; remaining = Math.max(60, Number(root.querySelector("input").value) * 60); render(); root.querySelector('[data-action="start"]').textContent = "Start"; };
      onClose = () => clearInterval(timer); render(); break;
    }
    case "todo":
      root.innerHTML = `<form class="tool-compose"><input class="app-input" placeholder="Add a task" aria-label="New task"><button class="app-button primary">Add</button></form><div class="tool-list"></div>`;
      { const tasks = readData(key) || []; const render = () => { root.querySelector(".tool-list").innerHTML = tasks.map((task, i) => `<label class="tool-task"><input type="checkbox" data-index="${i}" ${task.done ? "checked" : ""}><span>${escapeHTML(task.text)}</span><button class="app-button" data-remove="${i}" type="button">Remove</button></label>`).join("") || "No tasks yet."; writeData(key, tasks); root.querySelectorAll("[data-index]").forEach(box => box.onchange = () => { tasks[Number(box.dataset.index)].done = box.checked; render(); }); root.querySelectorAll("[data-remove]").forEach(item => item.onclick = () => { tasks.splice(Number(item.dataset.remove), 1); render(); }); }; root.querySelector("form").onsubmit = event => { event.preventDefault(); const field = root.querySelector("input"); if (field.value.trim()) tasks.push({ text: field.value.trim(), done: false }); field.value = ""; render(); }; render(); }
      break;
    case "currency":
      root.innerHTML = `<div class="tool-heading"><h2>Currency Converter</h2><p>Illustrative fixed rates only; not live financial data.</p></div><div class="tool-toolbar">${input("Amount", "number", "1")}<select class="app-select currency-from"><option>USD</option><option>EUR</option><option>GBP</option><option>JPY</option><option>CAD</option></select><span>to</span><select class="app-select currency-to"><option>EUR</option><option>USD</option><option>GBP</option><option>JPY</option><option>CAD</option></select>${button("Convert", "convert", true)}</div><output class="tool-result"></output>`;
      root.querySelector('[data-action="convert"]').onclick = () => { const rates = { USD: 1, EUR: .92, GBP: .79, JPY: 156, CAD: 1.37 }; const amount = Number(root.querySelector('input[type="number"]').value); const from = root.querySelector(".currency-from").value, to = root.querySelector(".currency-to").value; root.querySelector(".tool-result").textContent = `${(amount / rates[from] * rates[to]).toFixed(2)} ${to}`; };
      break;
    case "unit-converter":
      root.innerHTML = `<div class="tool-toolbar">${input("Value", "number", "1")}<select class="app-select unit-from"><option value="m">Meters</option><option value="km">Kilometers</option><option value="mi">Miles</option><option value="kg">Kilograms</option><option value="lb">Pounds</option></select><span>to</span><select class="app-select unit-to"><option value="km">Kilometers</option><option value="m">Meters</option><option value="mi">Miles</option><option value="kg">Kilograms</option><option value="lb">Pounds</option></select>${button("Convert", "convert", true)}</div><output class="tool-result"></output><p class="tool-status">Length and weight conversions</p>`;
      root.querySelector('[data-action="convert"]').onclick = () => { const factor = { m: 1, km: 1000, mi: 1609.344, kg: 1, lb: .45359237 }; const from = root.querySelector(".unit-from").value, to = root.querySelector(".unit-to").value; if ((from === "kg") !== (to === "kg")) { root.querySelector(".tool-result").textContent = "Choose units from the same measurement group."; return; } root.querySelector(".tool-result").textContent = `${(Number(root.querySelector('input[type="number"]').value) * factor[from] / factor[to]).toFixed(4)} ${to}`; };
      break;
    case "contacts":
      root.innerHTML = `<form class="tool-compose">${input("Name")}${input("Email", "email")}<button class="app-button primary">Add contact</button></form><input class="app-input contact-search" placeholder="Filter contacts" aria-label="Filter contacts"><div class="tool-list"></div>`;
      { const contacts = readData(key) || []; const render = () => { const query = root.querySelector(".contact-search").value.toLowerCase(); root.querySelector(".tool-list").innerHTML = contacts.filter(item => `${item.name} ${item.email}`.toLowerCase().includes(query)).map((item, index) => `<p>${escapeHTML(item.name)} · ${escapeHTML(item.email)} <button class="app-button" data-remove="${index}">Remove</button></p>`).join("") || "No matching contacts"; writeData(key, contacts); root.querySelectorAll("[data-remove]").forEach(remove => remove.onclick = () => { contacts.splice(Number(remove.dataset.remove), 1); render(); }); }; root.querySelector("form").onsubmit = event => { event.preventDefault(); const fields = [...root.querySelectorAll("form input")]; if (fields[0].value.trim()) contacts.push({ name: fields[0].value.trim(), email: fields[1].value.trim() }); fields.forEach(field => field.value = ""); render(); }; root.querySelector(".contact-search").oninput = render; render(); }
      break;
    case "password-generator":
      root.innerHTML = `<div class="tool-heading"><h2>Password Generator</h2><p>Generated locally and not saved. Use a password manager for account credentials.</p></div><label class="tool-field">Length <input class="app-input" type="number" min="8" max="64" value="20"></label><label class="tool-check"><input type="checkbox" checked> Include symbols</label><div class="tool-toolbar">${button("Generate", "generate", true)}<button class="app-button" data-action="copy" type="button">Copy</button></div><output class="tool-result password-result"></output>`;
      root.querySelector('[data-action="generate"]').onclick = () => { const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" + (root.querySelector('input[type="checkbox"]').checked ? "!@#$%^&*()-_=+" : ""); const length = Math.max(8, Math.min(64, Number(root.querySelector('input[type="number"]').value) || 20)); const bytes = crypto.getRandomValues(new Uint8Array(length)); root.querySelector(".password-result").textContent = [...bytes].map(value => chars[value % chars.length]).join(""); };
      root.querySelector('[data-action="copy"]').onclick = async () => { try { await navigator.clipboard.writeText(root.querySelector(".password-result").textContent); toast("Copied to clipboard"); } catch { toast("Clipboard permission unavailable"); } };
      break;
    case "whiteboard": {
      root.innerHTML = `<div class="tool-toolbar"><input type="color" value="#202018" aria-label="Brush color"><input type="range" min="1" max="24" value="4" aria-label="Brush size">${button("Clear", "clear")}</div><canvas class="tool-canvas" aria-label="Whiteboard"></canvas>`;
      const canvas = root.querySelector("canvas"), ctx = canvas.getContext("2d"); let drawing = false;
      const resize = () => { const image = canvas.width ? canvas.toDataURL() : null; canvas.width = canvas.clientWidth; canvas.height = canvas.clientHeight; if (image) { const restore = new Image(); restore.onload = () => ctx.drawImage(restore, 0, 0, canvas.width, canvas.height); restore.src = image; } };
      new ResizeObserver(resize).observe(canvas); resize();
      canvas.onpointerdown = event => { drawing = true; canvas.setPointerCapture(event.pointerId); ctx.beginPath(); ctx.moveTo(event.offsetX, event.offsetY); };
      canvas.onpointermove = event => { if (!drawing) return; ctx.strokeStyle = root.querySelector('input[type="color"]').value; ctx.lineWidth = Number(root.querySelector('input[type="range"]').value); ctx.lineCap = "round"; ctx.lineTo(event.offsetX, event.offsetY); ctx.stroke(); };
      canvas.onpointerup = () => drawing = false;
      root.querySelector('[data-action="clear"]').onclick = () => ctx.clearRect(0, 0, canvas.width, canvas.height);
      break;
    }
    case "expenses":
      root.innerHTML = `<form class="tool-compose">${input("Item")}${input("Amount", "number")}<button class="app-button primary">Add expense</button></form><div class="tool-list"></div><output class="tool-result"></output>`;
      { const items = readData(key) || []; const render = () => { root.querySelector(".tool-list").innerHTML = items.map((item, i) => `<p>${escapeHTML(item.name)} · $${item.amount.toFixed(2)} <button class="app-button" data-remove="${i}">Remove</button></p>`).join("") || "No expenses"; root.querySelector(".tool-result").textContent = `Total: $${items.reduce((sum, item) => sum + item.amount, 0).toFixed(2)}`; writeData(key, items); root.querySelectorAll("[data-remove]").forEach(remove => remove.onclick = () => { items.splice(Number(remove.dataset.remove), 1); render(); }); }; root.querySelector("form").onsubmit = event => { event.preventDefault(); const fields = [...root.querySelectorAll("form input")]; if (fields[0].value.trim() && Number(fields[1].value) >= 0) items.push({ name: fields[0].value, amount: Number(fields[1].value) }); fields.forEach(field => field.value = ""); render(); }; render(); }
      break;
    case "json":
      root.innerHTML = `<textarea class="tool-editor json-input" aria-label="JSON input" placeholder='{"hello":"banana"}'></textarea><div class="tool-toolbar">${button("Format", "format", true)}${button("Minify", "minify")}</div><pre class="tool-preview json-output" aria-live="polite"></pre>`;
      for (const action of ["format", "minify"]) root.querySelector(`[data-action="${action}"]`).onclick = () => { try { const value = JSON.parse(root.querySelector(".json-input").value); root.querySelector(".json-output").textContent = JSON.stringify(value, null, action === "format" ? 2 : 0); } catch (error) { root.querySelector(".json-output").textContent = error.message; } };
      break;
    case "base64":
      root.innerHTML = `<textarea class="tool-editor" aria-label="Text input" placeholder="Enter text"></textarea><div class="tool-toolbar">${button("Encode", "encode", true)}${button("Decode", "decode")}</div><pre class="tool-preview" aria-live="polite"></pre>`;
      root.querySelector('[data-action="encode"]').onclick = () => { const bytes = new TextEncoder().encode(root.querySelector("textarea").value); let binary = ""; for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000)); root.querySelector("pre").textContent = btoa(binary); };
      root.querySelector('[data-action="decode"]').onclick = () => { try { root.querySelector("pre").textContent = new TextDecoder().decode(Uint8Array.from(atob(root.querySelector("textarea").value), char => char.charCodeAt(0))); } catch { root.querySelector("pre").textContent = "Invalid Base64 input"; } };
      break;
    case "regex":
      root.innerHTML = `<div class="tool-toolbar">${input("Pattern", "text", "banana")}${input("Flags", "text", "gi")}</div><textarea class="tool-editor" aria-label="Test text" placeholder="Text to test"></textarea>${button("Test expression", "test", true)}<pre class="tool-preview" aria-live="polite"></pre>`;
      root.querySelector('[data-action="test"]').onclick = () => { try { const pattern = root.querySelectorAll("input")[0].value, flags = root.querySelectorAll("input")[1].value; const expression = new RegExp(pattern, flags.includes("g") ? flags : `${flags}g`); root.querySelector("pre").textContent = [...root.querySelector("textarea").value.matchAll(expression)].map(match => `${match[0]} at ${match.index}`).join("\n") || "No matches"; } catch (error) { root.querySelector("pre").textContent = error.message; } };
      break;
    case "diff":
      root.innerHTML = `<div class="tool-split"><label class="tool-field">Original<textarea class="app-input diff-left" rows="10"></textarea></label><label class="tool-field">Changed<textarea class="app-input diff-right" rows="10"></textarea></label></div>${button("Compare lines", "compare", true)}<pre class="tool-preview" aria-live="polite"></pre>`;
      root.querySelector('[data-action="compare"]').onclick = () => { const left = root.querySelector(".diff-left").value.split("\n"), right = root.querySelector(".diff-right").value.split("\n"); const count = Math.max(left.length, right.length); root.querySelector("pre").textContent = Array.from({ length: count }, (_, i) => left[i] === right[i] ? `  ${left[i] || ""}` : `${left[i] === undefined ? "+" : "-"} ${left[i] || ""}\n${right[i] === undefined ? "" : `+ ${right[i]}`}`).join("\n"); };
      break;
    case "keyboard":
      root.innerHTML = `<textarea class="tool-editor keyboard-output" aria-label="Typed text"></textarea><div class="tool-keyboard">${"1234567890qwertyuiopasdfghjklzxcvbnm".split("").map(char => `<button class="app-button" data-key="${char}">${char}</button>`).join("")}<button class="app-button" data-key=" ">Space</button><button class="app-button" data-key="Backspace">⌫</button><button class="app-button" data-key="Enter">↵</button></div>`;
      root.querySelectorAll("[data-key]").forEach(keyButton => keyButton.onclick = () => { const area = root.querySelector("textarea"), key = keyButton.dataset.key, start = area.selectionStart, end = area.selectionEnd; area.setRangeText(key === "Backspace" ? "" : key === "Enter" ? "\n" : key, key === "Backspace" && start === end ? Math.max(0, start - 1) : start, end, "end"); area.focus(); });
      break;
    case "dictionary": {
      const words = { banana: "A long curved fruit with a soft sweet flesh and yellow skin when ripe.", browser: "A program used to access and view websites.", desktop: "The main workspace of a graphical computer interface.", local: "Stored or processed on this device rather than a remote service.", privacy: "The right to control access to personal information." };
      root.innerHTML = `<form class="tool-compose"><input class="app-input" placeholder="Look up a word" aria-label="Word"><button class="app-button primary">Search</button></form><div class="tool-list"></div>`;
      root.querySelector("form").onsubmit = event => { event.preventDefault(); const word = root.querySelector("input").value.toLowerCase().trim(); root.querySelector(".tool-list").textContent = words[word] ? `${word}: ${words[word]}` : `“${word}” is not in the small offline dictionary.`; };
      break;
    }
    case "haiku":
      root.innerHTML = `<div class="tool-heading"><h2>Haiku Generator</h2><p>Creates a playful three-line poem from a small bundled word set.</p></div><div class="haiku-result" aria-live="polite">Press Generate for a poem.</div>${button("Generate haiku", "generate", true)}`;
      root.querySelector('[data-action="generate"]').onclick = () => { const lines = [["Soft rain taps the leaves", "Bright sunlight warms the green leaves", "Quiet windows glow"], ["A small breeze passes", "The red apples sway in wind", "Evening settles now"], ["Pages turn slowly", "Green gardens bloom in moonlight", "Day begins again"]]; root.querySelector(".haiku-result").textContent = lines[Math.floor(Math.random() * lines.length)].join("\n"); };
      break;
    case "ascii-art":
      root.innerHTML = `<div class="tool-toolbar">${input("Text", "text", "BANANA")}${button("Create art", "create", true)}</div><pre class="tool-preview ascii-output"></pre>`;
      root.querySelector('[data-action="create"]').onclick = () => { const text = root.querySelector("input").value.toUpperCase().slice(0, 24); root.querySelector("pre").textContent = `██ ${text} ██\n${"█ ".repeat(text.length + 2)}\n██ ${text.split("").reverse().join("")} ██`; };
      break;
    case "backup":
      root.innerHTML = `<div class="tool-heading"><h2>System Backup</h2><p>Export or restore this site's BananaOS localStorage data.</p></div><div class="tool-toolbar">${button("Download backup", "export", true)}<label class="app-button">Restore JSON<input class="hidden-input backup-file" type="file" accept="application/json"></label></div><p class="tool-status">Backups may contain personal notes. Keep the downloaded file private.</p>`;
      root.querySelector('[data-action="export"]').onclick = () => { const values = Object.fromEntries(Object.keys(localStorage).filter(item => item.startsWith("banana-")).map(item => [item, localStorage.getItem(item)])); download("bananaos-backup.json", JSON.stringify(values, null, 2), "application/json"); };
      root.querySelector(".backup-file").onchange = async event => { try { const values = JSON.parse(await event.target.files[0].text()); for (const [name, value] of Object.entries(values)) if (name.startsWith("banana-") && typeof value === "string") localStorage.setItem(name, value); root.querySelector(".tool-status").textContent = "Backup restored. Restart the desktop to apply settings."; } catch { root.querySelector(".tool-status").textContent = "Could not read a valid BananaOS backup."; } };
      break;
    default:
      root.innerHTML = `<div class="tool-heading"><h2>${escapeHTML(app.name)}</h2><p>This app is not available in the local runtime.</p></div>`;
  }

  createWindow({ id: app.id, title: app.name, icon: app.icon, width: ["monitor", "spreadsheet", "whiteboard", "code-editor", "markdown"].includes(app.id) ? 760 : 560, height: 480, content: root, onClose });
}

function renderMarkdown(source) {
  return escapeHTML(source).replace(/^### (.+)$/gm, "<h3>$1</h3>").replace(/^## (.+)$/gm, "<h2>$1</h2>").replace(/^# (.+)$/gm, "<h1>$1</h1>").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\*(.+?)\*/g, "<em>$1</em>").replace(/\n/g, "<br>");
}

function highlightCode(source) {
  const pattern = /(\/\/.*?$|\/\*[\s\S]*?\*\/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|\b(?:const|let|var|function|return|if|else|for|while|class|new|import|export|from|async|await|true|false|null|undefined)\b|\b\d+(?:\.\d+)?\b)/gm;
  let html = "", offset = 0;
  for (const match of source.matchAll(pattern)) {
    html += escapeHTML(source.slice(offset, match.index));
    const token = match[0], type = token.startsWith("//") || token.startsWith("/*") ? "comment" : /^["'`]/.test(token) ? "string" : /^\d/.test(token) ? "number" : "keyword";
    html += `<span class="code-${type}">${escapeHTML(token)}</span>`;
    offset = match.index + token.length;
  }
  return html + escapeHTML(source.slice(offset));
}

function download(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a"); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}