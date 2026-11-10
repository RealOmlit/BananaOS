#!/usr/bin/env python3
"""
Import games from truffled-main catalog into our games.json
"""
import json
import re
from pathlib import Path

TRUFFLED_JSON = Path("truffled-main/public/js/json/g.json")
GAMES_DIR = Path("games")
GAMES_JSON = GAMES_DIR / "assets" / "js" / "games.json"

def clean_name(name):
    """Clean up game name"""
    name = re.sub(r'\s*[-_]\s*(f|fix|fixed|updated|work|temp|awe|ff|el|z|u|a\d*|f\d*)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*[-_]\s*(fix2|fixf|fixx|fixedf|updateef|aa2|ef)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+\d+$', '', name)
    name = re.sub(r'^[0-9]+\.?\s*', '', name)
    name = name.strip()
    return name

def categorize_game(name, url, categories=None):
    """Determine game category"""
    if categories and len(categories) > 0:
        return categories
    
    hay = f"{name} {url}".lower()
    
    if any(kw in hay for kw in ['horror', 'granny', 'scary', 'zombie', 'dead', 'monster', 'fnaf', 'backrooms', 'slender', 'dead plate', 'deadseat', 'christmas massacre', 'tung sahur', 'lethal ape', 'slendy', 'baldi', 'hello neighbor', 'ugly', 'scary']):
        return ["Horror"]
    if any(kw in hay for kw in ['shoot', 'gun', 'sniper', 'battle', 'fps', 'strike', 'combat', 'war', 'blaster', 'cuphead', 'bloodmoney', 'duckhunt', 'bowmaster', 'bloons', 'tower defense', 'tower defence', 'archer']):
        return ["Shooter"]
    if any(kw in hay for kw in ['race', 'racing', 'drive', 'drift', 'car', 'bike', 'motor', 'kart', 'moto', 'speed', 'traffic', 'blumgi', 'turbo stars', 'mad cars', 'trackmania']):
        return ["Racing"]
    if any(kw in hay for kw in ['sport', 'football', 'basket', 'tennis', 'soccer', 'golf', 'baseball', 'boxing', 'volley', 'ball', 'bowling', 'pool', 'billiard', '8 ball']):
        return ["Sport"]
    if any(kw in hay for kw in ['puzzle', '2048', 'merge', 'match', 'logic', 'maze', 'memory', 'word', 'block', 'sudoku', 'chess', 'queens', 'tango', 'cut the rope', 'angry birds', 'bloxorz', 'monument valley', 'tetris']):
        return ["Puzzle"]
    if any(kw in hay for kw in ['adventure', 'quest', 'story', 'explore', 'escape', 'journey', 'robber', 'dadish', 'ducklife', 'cuttherope', 'run', 'platformer', 'celeste', 'hollow knight', 'undertale', 'deltarune', 'cave story', 'spider-man', 'sonic', 'mario', 'zelda', 'metroid', 'castle', 'cave', 'dungeon']):
        return ["Adventure"]
    if any(kw in hay for kw in ['sim', 'simulator', 'builder', 'idle', 'clicker', 'economy', 'craft', 'farm', 'tycoon', 'life', 'cookie', 'cookie clicker', 'adventure capitalist', 'capibara', 'bitlife', 'animal crossing', 'stardew']):
        return ["Simulation"]
    if any(kw in hay for kw in ['strategy', 'tower', 'defense', 'build', 'tactics', 'manager', 'bloons', 'ageofwar', 'hexarch', 'clash', 'kingdom', 'civilization', 'age of war', 'clash of vikings', 'plague inc', 'paper io', 'territorial']):
        return ["Strategy"]
    if any(kw in hay for kw in ['multiplayer', '2player', '2 player', 'online', 'basketbros', 'random', '.io', 'evo wars', 'survivor', 'slither', 'agar', 'diep', 'mope', 'deeeep', 'starve', 'zombs', 'krunker', 'shellshock', 'ev.io', 'warbot', 'bitburner', 'tag', 'web dashers', 'among us', 'fall guys', 'stumble guys', 'super animal', 'vampire survivors', 'brotato', 'holo', 'super sus', 'sus', 'yohoho']):
        return ["Multiplayer", "Online"]
    if any(kw in hay for kw in ['skill', 'jump', 'climb', 'hook', 'doodle', 'helix', 'stack', 'vex', 'dreadhead', 'parkour', 'getting over it', 'only up', 'jump king', 'pogostuck']):
        return ["Skill"]
    if any(kw in hay for kw in ['board', 'chess', 'connect four', 'tic tac toe', 'solitaire', 'checkers', 'backgammon', 'mahjong', 'domino', 'reversi', 'othello']):
        return ["Board"]
    
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
        "Survival": ["#4a1030", "#12011f"],
        "Action": ["#4d3d0f", "#1c1505"],
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
        "Skill": "🎯", "Board": "♟️", "Arcade": "🎮", "Survival": "🏕️", "Action": "⚡",
    }
    for cat in category:
        if cat in emoji_map:
            return emoji_map[cat]
    return "🎮"

def convert_truffled_url(url):
    """Convert truffled URL to our format"""
    if url.startswith('/games/') and url.endswith('/index.html'):
        # Subfolder game
        folder = url[7:-11]  # Remove '/games/' and '/index.html'
        return folder + '/index.html'
    elif url.startswith('/gamefile/'):
        # Direct HTML file
        filename = url[10:]  # Remove '/gamefile/'
        return filename
    return url

def main():
    # Load truffled catalog
    with open(TRUFFLED_JSON, 'r') as f:
        truffled_data = json.load(f)
    
    truffled_games = truffled_data['games']
    print(f"Truffled games: {len(truffled_games)}")
    
    # Load our games.json
    with open(GAMES_JSON, 'r') as f:
        existing_games = json.load(f)
    
    existing_names = {g['name'].lower() for g in existing_games}
    existing_links = {g['link'] for g in existing_games}
    
    print(f"Existing games: {len(existing_games)}")
    
    new_games = []
    skipped = 0
    
    for tg in truffled_games:
        name = tg.get('name', '').strip()
        if not name:
            skipped += 1
            continue
        
        # Clean name
        clean_title = clean_name(name)
        
        # Skip if name already exists
        if clean_title.lower() in existing_names:
            skipped += 1
            continue
        
        # Skip bad names
        if len(clean_title) < 2 or clean_title.lower() in ['untitled', 'game', 'html', 'index', 'test']:
            skipped += 1
            continue
        
        # Get URL
        url = tg.get('url', '')
        link = convert_truffled_url(url)
        
        if not link:
            skipped += 1
            continue
        
        # Skip if link already exists
        if link in existing_links:
            skipped += 1
            continue
        
        # Categorize
        categories = categorize_game(clean_title, link, tg.get('categories'))
        colors = generate_colors(categories)
        emoji = get_emoji(categories)
        
        # Check if file exists
        filepath = GAMES_DIR / link
        if not filepath.exists():
            # Try alternative paths
            alt_paths = [
                GAMES_DIR / link,
                GAMES_DIR / link.replace('/', '_'),
            ]
            found = False
            for p in alt_paths:
                if p.exists():
                    filepath = p
                    found = True
                    break
            if not found:
                # File doesn't exist - skip for now
                skipped += 1
                continue
        
        game_entry = {
            "name": clean_title,
            "link": link,
            "image": "assets/media/icons/default.png",
            "categories": categories,
            "emoji": emoji,
            "color": colors
        }
        
        new_games.append(game_entry)
        existing_names.add(clean_title.lower())
        existing_links.add(link)
        
        print(f"  ADDED: {clean_title} -> {link} ({categories})")
    
    print(f"\nNew games: {len(new_games)}")
    print(f"Skipped: {skipped}")
    
    if new_games:
        all_games = existing_games + new_games
        
        with open(GAMES_JSON, 'w') as f:
            json.dump(all_games, f, indent=2)
        
        print(f"Updated games.json with {len(all_games)} total games")
    else:
        print("No new games to add")

if __name__ == "__main__":
    main()