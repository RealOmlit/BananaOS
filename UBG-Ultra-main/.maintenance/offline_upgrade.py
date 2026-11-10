from pathlib import Path
root = Path(__file__).parent / 'games'
p = root / 'index.html'
s = p.read_text(encoding='utf8')
s = s.replace('<script src="assets/js/app.js?v=5" defer></script>', '<link rel="stylesheet" href="assets/css/offline.css?v=1">\n    <script src="assets/js/offline.js?v=1" defer></script>\n    <script src="assets/js/app.js?v=6" defer></script>')
s = s.replace('<button class="nav-btn" data-page="movies">Movies</button>', '<button class="nav-btn" data-page="movies">Movies</button>\n            <button class="nav-btn" data-page="anime">Anime</button>')
a = s.index('            <!-- Movies & Shows -->')
b = s.index('            <!-- Settings -->', a)
media = ''
for kind, title in [('movies','Movies'),('anime','Anime')]:
    media += f'''<section id="page-{kind}" class="page">
      <div class="media-header"><span class="eyebrow">YOUR OFFLINE COLLECTION</span><h1>{title}</h1>
      <p>Save your own videos here. Watch anytime, even without internet.</p></div>
      <div class="media-toolbar"><label class="btn btn-primary">Add videos<input id="{kind}Files" type="file" accept="video/*,.m4v,.ogv" multiple></label>
      <input id="{kind}Search" type="search" placeholder="Search saved {kind}" aria-label="Search saved {kind}"></div>
      <p id="{kind}Status" class="field-note" role="status"></p><div id="{kind}Grid" class="media-grid"></div>
      <p class="field-note">Videos stay in this browser's storage. Keep your original files as a backup. Playback depends on your browser's video codec support.</p>
    </section>'''
s = s[:a] + media + '\n' + s[b:]
s = s.replace('<h1>Settings</h1>', '''<h1>Settings</h1><span class="page-note">Make Ultra feel like you.</span>''')
s = s.replace('<div class="settings-grid">', '''<div class="wallpaper-panel panel">
      <div><span class="eyebrow">SET THE MOOD</span><h2>Your space. Your atmosphere.</h2><p>Soft animated color, rendered on your device. No downloads needed.</p></div>
      <button id="fluidWallpaperButton" class="btn btn-primary" type="button" aria-pressed="false">Fluid wallpaper: Off</button>
      <div class="background-choices"><button type="button" data-background-choice="twilight">Twilight</button><button type="button" data-background-choice="aurora">Aurora</button><button type="button" data-background-choice="ember">Ember</button><button type="button" data-background-choice="midnight">Midnight</button></div>
      <label class="intensity-label" for="fluidIntensity">Wallpaper intensity<input type="range" id="fluidIntensity" min="10" max="70" value="35"></label>
      <p id="offlineStatus" role="status" class="field-note">Preparing offline app…</p>
    </div><div class="settings-grid">''',1)
s = s.replace('Liquid Wallpaper — Reactive fluid that follows your mouse (Strawberri-style)', 'Fluid wallpaper — soft flowing color that responds to your pointer')
s = s.replace('id="liquidWallpaperToggle" checked', 'id="liquidWallpaperToggle"')
s = s.replace('Ask it to play a game, proxy a site, recommend something, or panic.', 'Local command assistant · Works offline · Find games, change wallpaper, or open your saved media.')
s = s.replace('Try: play slope  |  recommend racing  |  open youtube.com', 'Try: recommend racing | fluid wallpaper on | help')
s = s.replace('<div class="panel chat-users-panel">', '''<div class="panel chat-options"><label for="chatMode">Chat location</label><select id="chatMode"><option value="device">This device (offline)</option><option value="lan">Local Wi-Fi server</option></select><label for="localChatName">Display name</label><input id="localChatName" maxlength="24" value="Guest"><p id="localChatStatus" class="field-note" role="status">Device chat is saved here. Other devices need a shared Wi-Fi server.</p></div>
                <div class="panel chat-users-panel">''')
s = s.replace('id="chatText"', 'id="chatText" maxlength="500"')
s = s.replace('    <!-- Ambient particles -->', '''    <dialog id="offlineCinema"><div class="cinema-bar"><h2 id="cinemaTitle">Video</h2><button id="cinemaClose" class="btn" type="button">Close video</button></div><video id="offlineVideo" controls playsinline preload="metadata"></video><p id="cinemaStatus" role="status"></p></dialog>
    <!-- Ambient particles -->''')
p.write_text(s,encoding='utf8')
p=root/'assets/js/app.js';s=p.read_text(encoding='utf8')
# Remove the broken GPU renderer and its fallback; use one local lifecycle.
a=s.index('function startLiquidWallpaper() {');b=s.index('function enhanceGameCards()',a)
s=s[:a]+'''function startLiquidWallpaper() { window.UltraOffline.wallpaper(true); }
function stopLiquidWallpaper() { window.UltraOffline.wallpaper(false); }
'''+s[b:]
a=s.index('async function aiSend() {');b=s.index('/* ============================== navigation',a)
s=s[:a]+'''async function aiSend() { window.UltraOffline.assistant(); }

'''+s[b:]
a=s.index('async function sendChat(e) {');b=s.index('function startChatAndPresence()',a)
s=s[:a]+'''async function sendChat(e) { e?.preventDefault?.(); await window.UltraOffline.chatSend(); }
'''+s[b:]
s=s.replace('  stopChatAndPresence();\n  /* chat SSE */', '''  stopChatAndPresence();
  if (window.UltraOffline.deviceChat()) {
    $("#chatOnline").textContent = "Offline device chat";
    $(".chat-users-panel").classList.add("hidden");
    window.UltraOffline.renderChat();
    return;
  }
  $(".chat-users-panel").classList.remove("hidden");
  /* chat SSE */''')
s=s.replace('    chatStream.onmessage = (ev) => {','    chatStream.onerror = () => { $("#localChatStatus").textContent = "Local server disconnected. Switch to Device chat to keep chatting here."; };\n    chatStream.onmessage = (ev) => {')
s=s.replace('  wireGlobal();', '''  wireGlobal();
  window.UltraOffline.init({games:()=>games, play:g=>{nav("games");play(g);},nav,sid,chatRestart:startChatAndPresence}).catch(e=>console.error("Offline setup:",e));''')
# Delete obsolete online movie code and handlers now replaced by local media.
a=s.index('/* ============================== Movies & Shows');b=s.index('function initGamePreloader()',a)
prefix=s[a:b]
# Retain the preloader cache declaration which precedes the preloader function.
import re
declarations='\n'.join(re.findall(r'^const GAME_PRELOAD_CACHE[^\n]*',prefix,re.M))
s=s[:a]+declarations+'\n'+s[b:]
a=s.index('  /* Movies page */');b=s.index('\n}',a)
s=s[:a]+s[b:]
p.write_text(s,encoding='utf8')
