# UBG Ultra

Double-click **Start Ultra.cmd** in the parent folder to start the arcade and open your browser. Alternatively, run `python play.py` with Python 3.10 or newer. Keep the server window open while playing.

The catalog combines the local `games` folder and bundled `html-main` collection: **1,007 games and editions**. Local editions are labeled; duplicate names become alternate launch sources. Comment pages and emulator tools are excluded. This count includes different editions, not 1,007 independently verified distinct titles.

## Library improvements

- Responsive arcade homepage, local cover art, search, category filters, favorites, and recently played games.
- First 96 search results render immediately; **Show more games** adds the next 96.
- Keyboard accessible game cards and visible focus indicators.
- Restart, open directly, and alternate-version controls in the player.
- Large games receive a loading indicator and recovery controls after 20 seconds.
- The live catalog rebuilds from bundled files. `/library/` preserves the imported games' relative paths and `/artwork/` serves existing covers.

## Verification

Run `python -m unittest discover -s .maintenance -p test_catalog.py` to check every catalog launch URL for HTTP 200, nonempty HTML, and correct content type, plus path-traversal rejection. Run `node --check .ubg-content/assets/js/app.js` for JavaScript syntax validation.

The complete launch-path audit passes. Browser smoke checks also reached 2048's playable board and Waterworks' game menu. These checks do **not** certify full gameplay for every entry. Some games fetch third-party scripts, assets, or multiplayer services and still require an internet connection and an available upstream host.

Serve this project with the included server. Opening `index.html` directly or hosting only the `games` folder omits the imported collection and API routes.
