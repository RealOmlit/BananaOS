#!/usr/bin/env python3
"""
Filter out games with external base hrefs from games.json
"""
import json
import re
from pathlib import Path

GAMES_DIR = Path("C:/Users/Om 2/Downloads/UBG-Ultra-main/UBG-Ultra-main/games")
GAMES_JSON = GAMES_DIR / "assets" / "js" / "games.json"

def has_external_base_href(filepath):
    """Check if HTML file has external base href"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        base_match = re.search(r'base href="([^"]+)"', content)
        if base_match:
            url = base_match.group(1)
            if url.startswith('http://') or url.startswith('https://'):
                return True
    except:
        pass
    return False

def main():
    with open(GAMES_JSON, 'r') as f:
        games = json.load(f)
    
    print(f"Original games: {len(games)}")
    
    filtered_games = []
    removed = 0
    
    for game in games:
        link = game.get('link', '')
        filepath = GAMES_DIR / link
        
        if filepath.exists() and has_external_base_href(filepath):
            print(f"  REMOVING: {game['name']} ({link}) - external base href")
            removed += 1
            # Optionally delete the file
            # filepath.unlink()
        else:
            filtered_games.append(game)
    
    print(f"Removed: {removed}")
    print(f"Remaining: {len(filtered_games)}")
    
    # Write filtered games.json
    with open(GAMES_JSON, 'w') as f:
        json.dump(filtered_games, f, indent=2)
    
    print("Filtered games.json written")

if __name__ == "__main__":
    main()