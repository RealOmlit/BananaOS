#!/usr/bin/env python3
import json
import re
from pathlib import Path

GAMES_DIR = Path("games")
with open("games/assets/js/games.json", "r") as f:
    games = json.load(f)

print("Checking all games in games.json for external base hrefs...")
found = 0
for g in games:
    link = g.get("link", "")
    filepath = GAMES_DIR / link
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            base_match = re.search(r'base href="([^"]+)"', content)
            if base_match:
                url = base_match.group(1)
                if url.startswith("http://") or url.startswith("https://"):
                    print("  EXTERNAL BASE HREF: {} -> {} ({})".format(g["name"], link, url))
                    found += 1
        except:
            pass
print("Total with external base href:", found)