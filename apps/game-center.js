const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[char]));

export function launchGameCenter({ createWindow, toast }) {
  const root = document.createElement("div");
  root.className = "app game-center";
  root.innerHTML = `<header class="game-toolbar"><div><h2>UBG Ultra</h2><p class="game-status">Reading bundled game catalog…</p></div><input class="app-input game-search" type="search" placeholder="Search games" aria-label="Search games"></header><div class="game-grid" aria-live="polite"></div><button class="app-button game-more hidden" type="button">Show more games</button><section class="game-player hidden"><div class="tool-toolbar"><button class="app-button game-back" type="button">← Library</button><strong class="game-title"></strong><button class="app-button game-restart" type="button">↻ Reload</button></div><iframe title="UBG Ultra game" sandbox="allow-scripts allow-forms allow-pointer-lock allow-downloads" allow="fullscreen; autoplay" referrerpolicy="no-referrer"></iframe></section>`;
  const grid = root.querySelector(".game-grid"), status = root.querySelector(".game-status"), search = root.querySelector(".game-search");
  const more = root.querySelector(".game-more"), player = root.querySelector(".game-player"), frame = player.querySelector("iframe");
  let games = [], shown = 72, selected = null;

  function render() {
    const query = search.value.trim().toLowerCase();
    const matches = games.filter(game => game.name.toLowerCase().includes(query));
    const visible = matches.slice(0, shown);
    grid.innerHTML = visible.map(game => `<button class="game-card" type="button" data-id="${escapeHTML(game.id)}"><span class="game-cover" aria-hidden="true">🎮</span><strong>${escapeHTML(game.name)}</strong><small>${escapeHTML(game.author || "UBG Ultra")}</small><span class="game-card-state">Launch game</span></button>`).join("") || `<p class="game-empty">No bundled games match that search.</p>`;
    more.classList.toggle("hidden", visible.length >= matches.length);
    grid.querySelectorAll("[data-id]").forEach(card => card.onclick = () => openGame(matches.find(game => String(game.id) === card.dataset.id)));
    status.textContent = `${matches.length.toLocaleString()} local games`;
  }

  async function openGame(game) {
    if (!game) return;
    const filename = typeof game.url === "string" && game.url.includes("{HTML_URL}/") ? game.url.split("{HTML_URL}/").pop() : "";
    if (!filename || filename.includes("..") || filename.startsWith("/")) {
      toast("This catalog entry does not include a local game file.");
      status.textContent = `${game.name}: the game payload is not bundled in this checkout.`;
      return;
    }
    const path = `../html-main/${filename}`;
    try {
      const response = await fetch(new URL(path, import.meta.url), { method: "HEAD" });
      if (!response.ok || !response.headers.get("content-type")?.includes("text/html")) throw new Error("not found");
      selected = new URL(path, import.meta.url).href;
      player.querySelector(".game-title").textContent = game.name;
      frame.src = selected;
      player.classList.remove("hidden"); grid.classList.add("hidden"); more.classList.add("hidden"); search.classList.add("hidden");
    } catch {
      status.textContent = `${game.name}: local game HTML is missing. Add the bundled UBG Ultra game files to html-main to play offline.`;
      toast("Game payload is not included in this repository copy.");
    }
  }

  search.addEventListener("input", render);
  more.addEventListener("click", () => { shown += 72; render(); });
  player.querySelector(".game-back").onclick = () => { frame.src = "about:blank"; selected = null; player.classList.add("hidden"); grid.classList.remove("hidden"); search.classList.remove("hidden"); render(); };
  player.querySelector(".game-restart").onclick = () => { if (selected) frame.src = selected; };
  createWindow({ id: "game-center", title: "Game Center", icon: "🎮", width: 900, height: 620, content: root, onClose: () => { frame.src = "about:blank"; } });

  Promise.all([
    fetch(new URL("../UBG-Ultra-main/zones.json", import.meta.url)).then(response => { if (!response.ok) throw new Error("catalog unavailable"); return response.json(); }),
    fetch(new URL("./local-game-ids.json", import.meta.url)).then(response => { if (!response.ok) throw new Error("local game index unavailable"); return response.json(); })
  ])
    .then(([catalog, localIds]) => { const available = new Set(localIds); games = Array.isArray(catalog) ? catalog.filter(game => game && typeof game.name === "string" && typeof game.url === "string" && available.has(game.id) && game.url.includes("{HTML_URL}/")) : []; render(); })
    .catch(() => { status.textContent = "UBG Ultra catalog is unavailable. The games folder must be committed alongside BananaOS."; grid.innerHTML = `<p class="game-empty">No bundled game catalog was found.</p>`; });
}