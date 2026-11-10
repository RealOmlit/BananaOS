# BananaOS

BananaOS is a static, multi-file desktop environment. Its runtime is HTML, CSS, and browser JavaScript; GitHub Pages needs no Node.js service or database.

## Run it

For local development, serve this folder over HTTP (ES modules do not load reliably from `file://`):

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000`. To publish with GitHub Pages:

1. In the repository settings, open **Pages**.
2. Select **Deploy from a branch**, choose the branch and `/ (root)`, and save.
3. Visit the Pages URL after deployment completes.

## What's inside

- A draggable desktop, taskbar, searchable Start menu, and resizable, movable, minimizable, maximizable windows.
- A diagnostic boot sequence that waits for desktop initialization and browser fonts before fading out.
- Exactly 50 catalogued apps across Core Utilities, Network & Media, and Productivity & Lifestyle, plus a separate Game Center.
- Modular app registry and tools in `apps/catalog.js`, `apps/toolkit.js`, and `apps/game-center.js`, with app styling in `apps/apps.css`.
- Local storage for notes, tasks, contacts, settings, and other app data; camera and microphone access are requested only by their apps.
- Gust Browser with local demo pages and a sandboxed direct-site frame.

**Browser limits:** Gust tunnels browsing through its configured WISP relay. The default configuration uses public relays, so relay operators may observe connection metadata; do not enter sensitive credentials or private data. Some destinations or network policies may still prevent access. The embedded Discord account-token client is disabled.

**Game bundle:** Game Center uses `UBG-Ultra-main/zones.json` and the local availability index at `apps/local-game-ids.json`. This checkout currently has 432 matching playable HTML pages under `html-main/`, including game 512. Some games load assets from their original HTTPS CDN and may need an internet connection. If you add or remove game pages, update the local ID index to match.

BananaOS is a static GitHub Pages app and does not provide secure storage for passwords, account tokens, or proxy credentials. Do not paste private credentials into the site.
