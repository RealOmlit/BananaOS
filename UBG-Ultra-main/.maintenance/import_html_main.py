#!/usr/bin/env python3
"""
Import games from html-main folder to games folder and update games.json
"""
import os
import json
import re
import shutil
from pathlib import Path

HTML_MAIN_DIR = Path("C:/Users/Om 2/Downloads/UBG-Ultra-main/UBG-Ultra-main/html-main")
GAMES_DIR = Path("C:/Users/Om 2/Downloads/UBG-Ultra-main/UBG-Ultra-main/games")
GAMES_JSON = GAMES_DIR / "assets" / "js" / "games.json"

def extract_title_from_html(filepath):
    """Extract game title from HTML file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for external base href - these games won't work locally
        base_match = re.search(r'base href="([^"]+)"', content)
        if base_match:
            url = base_match.group(1)
            # If base href points to external CDN, this game won't work locally
            if url.startswith('http://') or url.startswith('https://'):
                return None  # Signal to skip this game
        
        # Try to find title tag
        title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        
        # Fallback to filename
        return filepath.stem.replace('-', ' ').replace('_', ' ').title()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return filepath.stem.replace('-', ' ').replace('_', ' ').title()

def clean_name(name):
    """Clean up game name"""
    # Remove common suffixes
    name = re.sub(r'\s*[-_]\s*(f|fix|fixed|updated|work|temp|awe|ff|el|z|u|a\d*|f\d*)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*[-_]\s*(fix2|fixf|fixx|fixedf|updateef|aa2|ef)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+\d+$', '', name)  # trailing numbers like "101"
    name = re.sub(r'^[0-9]+\.?\s*', '', name)  # leading numbers like "100 "
    name = name.strip()
    return name

def categorize_game(name, filepath):
    """Determine game category based on name and content"""
    name_lower = name.lower()
    path_str = str(filepath).lower()
    
    # Check filename patterns first
    if any(kw in path_str for kw in ['horror', 'granny', 'scary', 'zombie', 'dead', 'monster', 'fnaf', 'backrooms']):
        return ["Horror"]
    if any(kw in path_str for kw in ['shoot', 'gun', 'sniper', 'battle', 'fps', 'strike', 'combat', 'war']):
        return ["Shooter"]
    if any(kw in path_str for kw in ['race', 'racing', 'drive', 'drift', 'car', 'bike', 'motor', 'kart', 'moto', 'speed']):
        return ["Racing"]
    if any(kw in path_str for kw in ['sport', 'football', 'basket', 'tennis', 'soccer', 'golf', 'baseball', 'boxing', 'volley']):
        return ["Sport"]
    if any(kw in path_str for kw in ['puzzle', '2048', 'merge', 'match', 'logic', 'maze', 'memory', 'word', 'block', 'sudoku', 'chess', 'queens', 'tango']):
        return ["Puzzle"]
    if any(kw in path_str for kw in ['adventure', 'quest', 'story', 'explore', 'escape', 'journey', 'robber', 'dadish', 'ducklife', 'cuttherope', 'run', 'platformer']):
        return ["Adventure"]
    if any(kw in path_str for kw in ['sim', 'simulator', 'builder', 'idle', 'clicker', 'economy', 'craft', 'farm', 'tycoon', 'life', 'cookie']):
        return ["Simulation"]
    if any(kw in path_str for kw in ['strategy', 'tower', 'defense', 'build', 'tactics', 'manager', 'bloons', 'ageofwar', 'hexarch']):
        return ["Strategy"]
    if any(kw in path_str for kw in ['multiplayer', '2 ?player', 'online', 'basketbros', 'random', '.io']):
        return ["Multiplayer"]
    if any(kw in path_str for kw in ['skill', 'jump', 'climb', 'hook', 'doodle', 'helix', 'stack']):
        return ["Skill"]
    
    return ["Arcade"]

def generate_colors(category):
    """Generate color scheme based on category"""
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
        "Skill": ["#0e4d3a", "#041c16"],
        "Board": ["#3a3a2a", "#121210"],
        "Arcade": ["#3d1d66", "#150826"],
    }
    for cat in category:
        if cat in color_map:
            return color_map[cat]
    return ["#3d1d66", "#150826"]

def get_emoji(category):
    """Get emoji for category"""
    emoji_map = {
        "Horror": "👻",
        "Shooter": "🔫",
        "Racing": "🏎️",
        "Sport": "⚽",
        "Puzzle": "🧩",
        "Adventure": "🗺️",
        "Simulation": "🏭",
        "Strategy": "🎯",
        "Multiplayer": "🌐",
        "Skill": "🎯",
        "Board": "♟️",
        "Arcade": "🎮",
    }
    for cat in category:
        if cat in emoji_map:
            return emoji_map[cat]
    return "🎮"

def main():
    # Load existing games.json
    with open(GAMES_JSON, 'r') as f:
        existing_games = json.load(f)
    
    # Build set of existing links (filenames)
    existing_links = {game['link'] for game in existing_games}
    existing_names = {game['name'].lower() for game in existing_games}
    
    print(f"Existing games: {len(existing_games)}")
    print(f"Existing links: {len(existing_links)}")
    
    # Get all HTML files from html-main
    html_files = list(HTML_MAIN_DIR.glob("*.html"))
    print(f"HTML files in html-main: {len(html_files)}")
    
    new_games = []
    skipped = 0
    
    for html_file in html_files:
        filename = html_file.name
        
        # Skip if already exists in games folder
        if (GAMES_DIR / filename).exists():
            print(f"  SKIP (exists in games): {filename.encode('ascii', 'ignore').decode()}")
            skipped += 1
            continue
        
        # Skip if link already in games.json
        if filename in existing_links:
            print(f"  SKIP (in games.json): {filename.encode('ascii', 'ignore').decode()}")
            skipped += 1
            continue
        
        # Extract title
        raw_title = extract_title_from_html(html_file)
        if raw_title is None:
            print(f"  SKIP (external base href): {filename.encode('ascii', 'ignore').decode()}")
            skipped += 1
            continue
        clean_title = clean_name(raw_title)
        
        # Skip if name already exists (case-insensitive)
        if clean_title.lower() in existing_names:
            print(f"  SKIP (duplicate name): {clean_title.encode('ascii', 'ignore').decode()} ({filename.encode('ascii', 'ignore').decode()})")
            skipped += 1
            continue
        
        # Skip if title is too generic or empty
        if len(clean_title) < 2 or clean_title.lower() in ['untitled', 'game', 'html', 'index', 'winter', 'test']:
            print(f"  SKIP (bad title): {clean_title.encode('ascii', 'ignore').decode()} ({filename.encode('ascii', 'ignore').decode()})")
            skipped += 1
            continue
        
        # Categorize
        categories = categorize_game(clean_title, html_file)
        colors = generate_colors(categories)
        emoji = get_emoji(categories)
        
        # Copy file to games folder
        dest = GAMES_DIR / filename
        shutil.copy2(html_file, dest)
        
        # Create game entry
        game_entry = {
            "name": clean_title,
            "link": filename,
            "image": "assets/media/icons/default.png",
            "categories": categories,
            "emoji": emoji,
            "color": colors
        }
        
        new_games.append(game_entry)
        existing_links.add(filename)
        existing_names.add(clean_title.lower())
        
        print(f"  ADDED: {clean_title.encode('ascii', 'ignore').decode()} ({filename}) -> {categories}")
    
    print(f"\nTotal new games: {len(new_games)}".encode('ascii', 'ignore').decode())
    print(f"Skipped: {skipped}")
    
    if new_games:
        # Add new games to existing
        all_games = existing_games + new_games
        
        # Write updated games.json
        with open(GAMES_JSON, 'w') as f:
            json.dump(all_games, f, indent=2)
        
        print(f"Updated games.json with {len(all_games)} total games")
    else:
        print("No new games to add")

if __name__ == "__main__":
    main()