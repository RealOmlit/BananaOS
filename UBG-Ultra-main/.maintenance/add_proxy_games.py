#!/usr/bin/env python3
"""
Add CDN games from html-main as proxy entries in games.json
These will work online via the /proxy/ system
"""
import re
import json
import shutil
from pathlib import Path

HTML_MAIN_DIR = Path("html-main")
GAMES_DIR = Path("games")
GAMES_JSON = GAMES_DIR / "assets" / "js" / "games.json"

def extract_cdn_game_info(filepath):
    """Extract game info for proxy catalog"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return None
    
    # Check for external base href
    base_match = re.search(r'base href="([^"]+)"', content)
    if not base_match:
        return None
    
    base_url = base_match.group(1)
    if not (base_url.startswith('http://') or base_url.startswith('https://')):
        return None
    
    # Extract title
    title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else filepath.stem
    
    # Clean title
    title = re.sub(r'\s*[-_]\s*(f|fix|fixed|updated|work|temp|awe|ff|el|z|u|a\d*|f\d*)$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*[-_]\s*(fix2|fixf|fixx|fixedf|updateef|aa2|ef)$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+\d+$', '', title)
    title = re.sub(r'^[0-9]+\.?\s*', '', title)
    title = title.strip()
    
    if len(title) < 2 or title.lower() in ['untitled', 'game', 'html', 'index', 'winter', 'test', 'yt game wrapper', 'unity webgl player', 'unity web player', 'game']:
        return None
    
    return {
        'name': title,
        'proxy_url': base_url.rstrip('/') + '/',
        'filename': filepath.name
    }

def categorize_game(name, url):
    """Determine game category"""
    hay = f"{name} {url}".lower()
    
    if any(kw in hay for kw in ['horror', 'granny', 'scary', 'zombie', 'dead', 'monster', 'fnaf', 'backrooms', 'slender']):
        return ["Horror"]
    if any(kw in hay for kw in ['shoot', 'gun', 'sniper', 'battle', 'fps', 'strike', 'combat', 'war', 'blaster']):
        return ["Shooter"]
    if any(kw in hay for kw in ['race', 'racing', 'drive', 'drift', 'car', 'bike', 'motor', 'kart', 'moto', 'speed', 'traffic']):
        return ["Racing"]
    if any(kw in hay for kw in ['sport', 'football', 'basket', 'tennis', 'soccer', 'golf', 'baseball', 'boxing', 'volley', 'ball']):
        return ["Sport"]
    if any(kw in hay for kw in ['puzzle', '2048', 'merge', 'match', 'logic', 'maze', 'memory', 'word', 'block', 'sudoku', 'chess', 'queens', 'tango']):
        return ["Puzzle"]
    if any(kw in hay for kw in ['adventure', 'quest', 'story', 'explore', 'escape', 'journey', 'robber', 'dadish', 'ducklife', 'cuttherope', 'run', 'platformer']):
        return ["Adventure"]
    if any(kw in hay for kw in ['sim', 'simulator', 'builder', 'idle', 'clicker', 'economy', 'craft', 'farm', 'tycoon', 'life', 'cookie']):
        return ["Simulation"]
    if any(kw in hay for kw in ['strategy', 'tower', 'defense', 'build', 'tactics', 'manager', 'bloons', 'ageofwar', 'hexarch']):
        return ["Strategy"]
    if any(kw in hay for kw in ['multiplayer', '2player', '2 player', 'online', 'basketbros', 'random', '.io', 'evo wars', 'survivor', 'slither']):
        return ["Multiplayer", "Online"]
    if any(kw in hay for kw in ['skill', 'jump', 'climb', 'hook', 'doodle', 'helix', 'stack', 'vex']):
        return ["Skill"]
    
    return ["Arcade"]

def generate_colors(category):
    color_map = {
        "Horror": ["#4a1030", "#12011f"],
        "Shooter": ["#20305e", "#0a1226"],
        "Racing": ["#5e1d20", "#1a0a12"],
        "Sport": ["#0f4d2e", "#072212"],
        "Puzzle": ["#3b2a66", "#140b2b"],
        "Adventure": ["#1d4d5e", "#0a1d26"],
        "Simulation": ["#3b3b4d", "#14141f"],
        "Strategy": ["#264d1d", "#0c1d0a"],
        "Multiplayer": ["#0f3b4d", "#051a24"],
        "Online": ["#0f3b4d", "#051a24"],
        "Skill": ["#0e4d3a", "#041c16"],
        "Board": ["#3a3a2a", "#121210"],
        "Arcade": ["#3d1d66", "#150826"],
    }
    for cat in category:
        if cat in color_map:
            return color_map[cat]
    return ["#3d1d66", "#150826"]

def get_emoji(category):
    emoji_map = {
        "Horror": "👻", "Shooter": "🔫", "Racing": "🏎️", "Sport": "⚽",
        "Puzzle": "🧩", "Adventure": "🗺️", "Simulation": "🏭",
        "Strategy": "🎯", "Multiplayer": "🌐", "Online": "🌐",
        "Skill": "🎯", "Board": "♟️", "Arcade": "🎮",
    }
    for cat in category:
        if cat in emoji_map:
            return emoji_map[cat]
    return "🎮"

def main():
    # Load existing games.json
    with open(GAMES_JSON, 'r') as f:
        existing_games = json.load(f)
    
    existing_names = {g['name'].lower() for g in existing_games}
    existing_links = {g['link'] for g in existing_games}
    
    print(f"Existing games: {len(existing_games)}")
    
    # Get all HTML files from html-main
    html_files = list(HTML_MAIN_DIR.glob("*.html"))
    
    proxy_games = []
    skipped = 0
    
    for html_file in html_files:
        info = extract_cdn_game_info(html_file)
        if not info:
            skipped += 1
            continue
        
        # Skip if name already exists
        if info['name'].lower() in existing_names:
            skipped += 1
            continue
        
        # Create proxy link (the CDN URL)
        proxy_link = info['proxy_url']
        
        categories = categorize_game(info['name'], proxy_link)
        colors = generate_colors(categories)
        emoji = get_emoji(categories)
        
        game_entry = {
            "name": info['name'],
            "link": proxy_link,
            "image": "assets/media/icons/default.png",
            "categories": categories,
            "emoji": emoji,
            "color": colors
        }
        
        proxy_games.append(game_entry)
        existing_names.add(info['name'].lower())
        existing_links.add(proxy_link)
        
        name_safe = info['name'].encode('ascii', 'ignore').decode()
        print(f"  ADDED (PROXY): {name_safe} -> {proxy_link[:60]}... ({categories})")
    
    print(f"\nNew proxy games: {len(proxy_games)}")
    print(f"Skipped: {skipped}")
    
    if proxy_games:
        all_games = existing_games + proxy_games
        
        with open(GAMES_JSON, 'w') as f:
            json.dump(all_games, f, indent=2)
        
        print(f"Updated games.json with {len(all_games)} total games")
    else:
        print("No new proxy games to add")

if __name__ == "__main__":
    main()