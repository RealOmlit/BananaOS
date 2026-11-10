#!/usr/bin/env python3
"""
Add missing games from games/ folder to truffled-main/public/js/json/g.json
"""
import json
import os
import re

GAMES_FOLDER = r"C:\Users\Om 2\Downloads\UBG-Ultra-main\UBG-Ultra-main\games"
G_JSON_PATH = r"C:\Users\Om 2\Downloads\UBG-Ultra-main\UBG-Ultra-main\truffled-main\public\js\json\g.json"

EXCLUDES = {"index.html", "ubg-ultra.html", "desktop.ini"}
FOLDER_EXCLUDES = {"assets", "__pycache__", "media"}

NAME_OVERRIDES = {
    "1v1.lol.html": "1v1.LOL",
    "8ballclassic.html": "8 Ball Classic",
    "bloonsTD.html": "Bloons TD",
    "bloonsTD2.html": "Bloons TD 2",
    "bloonsTD3.html": "Bloons TD 3",
    "bloonsTD4.html": "Bloons TD 4",
    "bloonsTD5.html": "Bloons TD 5",
    "cookieclicker.htm": "Cookie Clicker",
    "crossyroad.htm": "Crossy Road",
    "motox3m.htm": "Moto X3M",
    "motox3m2.html": "Moto X3M 2",
    "motox3m3.html": "Moto X3M 3",
    "sm63.html": "Super Mario 63",
    "sm64.html": "Super Mario 64",
    "fnaf.html": "Five Nights at Freddy's",
    "fnaf2.html": "Five Nights at Freddy's 2",
    "fnaf3.html": "Five Nights at Freddy's 3",
    "fnaf4.html": "Five Nights at Freddy's 4",
    "ovo.html": "OvO",
    "run.html": "Run",
    "run2.html": "Run 2",
    "run3.html": "Run 3",
    "slope.html": "Slope",
    "slope3.html": "Slope 3",
    "vex4.html": "Vex 4",
    "vex5.html": "Vex 5",
    "vex6.htm": "Vex 6",
    "vex7.htm": "Vex 7",
    "vex8.htm": "Vex 8",
    "2048.html": "2048",
    "2048cupcakes.html": "2048 Cupcakes",
    "3Dflightsimulator.html": "3D Flight Simulator",
    "10minutestilldawn.html": "10 Minutes Till Dawn",
    "bloonsTD2.html": "Bloons TD 2",
    "bloonsTD3.html": "Bloons TD 3",
    "bloonsTD4.html": "Bloons TD 4",
    "bloonsTD5.html": "Bloons TD 5",
    "motox3mpoolparty.html": "Moto X3M Pool Party",
    "motox3mspookyland.html": "Moto X3M Spooky Land",
    "motox3mwinter.html": "Moto X3M Winter",
    "vexx3m.html": "Vex X3M",
    "vexx3m2.html": "Vex X3M 2",
    "ovo3dimensions.html": "OvO 3 Dimensions",
    "redball4vol1.html": "Red Ball 4 Vol 1",
    "redball4vol2.html": "Red Ball 4 Vol 2",
    "redball4vol3.html": "Red Ball 4 Vol 3",
    "superliquidsoccer.html": "Super Liquid Soccer",
    "subwaysurfersbeijing.html": "Subway Surfers Beijing",
    "subwaysurfershavana.html": "Subway Surfers Havana",
    "subwaysurferssanfrancisco.html": "Subway Surfers San Francisco",
    "superbikethechampion.html": "Super Bike The Champion",
    "plantsvszombies.html": "Plants vs Zombies",
    "worldshardestgame.html": "World's Hardest Game",
    "worldshardestgame2.html": "World's Hardest Game 2",
    "worldshardestgame3.html": "World's Hardest Game 3",
    "theimpossiblequiz.html": "The Impossible Quiz",
    "theimpossiblequiz2.html": "The Impossible Quiz 2",
    "thisistheonlylevel.html": "This Is The Only Level",
    "thisistheonlyleveltoo.html": "This Is The Only Level Too",
    "escapingtheprison.html": "Escaping The Prison",
    "breakingthebank.html": "Breaking The Bank",
    "cleanupio.html": "Cleanup.io",
    "clusterrush.html": "Cluster Rush",
    "holeio.html": "Hole.io",
    "paperio2.htm": "Paper.io 2",
    "territorialio.html": "Territorial.io",
    "agariolite.html": "Agar.io Lite",
    "bitplanes.htm": "Bitplanes",
    "bitlife.html": "BitLife",
    "boxingrandom.htm": "Boxing Random",
    "crossyroad.htm": "Crossy Road",
    "cookieclicker.htm": "Cookie Clicker",
    "driftboss.htm": "Drift Boss",
    "drivemad.htm": "Drive Mad",
    "elasticface.htm": "Elastic Face",
    "motox3m.htm": "Moto X3M",
    "parkingfury.html": "Parking Fury",
    "parkingfury2.html": "Parking Fury 2",
    "parkingfury3.html": "Parking Fury 3",
    "ragdollarchers.htm": "Ragdoll Archers",
    "rooftopsnipers.htm": "Rooftop Snipers",
    "snowrider.htm": "Snow Rider",
    "snowroad.htm": "Snow Road",
    "soccerrandom.htm": "Soccer Random",
    "templerun2.htm": "Temple Run 2",
    "timeshooter3.htm": "Time Shooter 3",
    "tombofthemask.htm": "Tomb Of The Mask",
    "vex6.htm": "Vex 6",
    "vex7.htm": "Vex 7",
    "vex8.htm": "Vex 8",
}

FOLDER_NAME_OVERRIDES = {
    "2048": "2048 Classic",
    "pac-hunt": "Pac Hunt",
    "cookie-clicker": "Cookie Clicker+",
    "solitaire": "Klondike Solitaire",
    "epoch-td": "Epoch Tower Defense",
    "platformer": "Retro Platformer",
    "chess": "Chess AI",
    "connect-four": "Connect Four",
    "lights-out": "Lights Out",
    "memory": "Memory Match",
    "minesweeper": "Minesweeper Classic",
    "mini-sudoku": "Mini Sudoku",
    "patches": "Patches",
    "queens": "Queens Puzzle",
    "tango": "Tango",
    "tic-tac-toe": "Tic Tac Toe",
    "zip": "Zip",
    "orbital-siege": "Orbital Siege",
    "backrooms-infestation": "Backrooms Infestation",
    "wave-defense": "Wave Defense",
    "squarelords": "Square Lords",
    "hexarch": "Hexarch",
    "tower-defense": "HTML5 Tower Defense",
    "society-ultra": "Society Ultra",
    "asteroids": "Asteroids",
    "road-racer": "Road Racer",
    "super-mario": "Super Mario",
    "dino-run": "Dino Run",
    "tower": "Tower Stack",
    "codequest": "Code Quest",
    "hextris": "Hextris",
    "flappy-bird": "Flappy Bird",
    "neon-breaker": "Neon Breaker",
    "neon-catch": "Neon Catch",
    "neon-core": "Neon Core",
    "neon-rise": "Neon Rise",
    "neon-void": "Neon Void",
}

CATEGORY_OVERRIDES = {
    "2048": ["Puzzle"],
    "pac-hunt": ["Arcade", "Puzzle"],
    "cookie-clicker": ["Simulation", "Puzzle"],
    "solitaire": ["Board", "Puzzle"],
    "epoch-td": ["Strategy", "Puzzle"],
    "platformer": ["Skill", "Action"],
    "chess": ["Board", "Strategy"],
    "connect-four": ["Board", "Puzzle"],
    "lights-out": ["Puzzle"],
    "memory": ["Puzzle"],
    "minesweeper": ["Puzzle"],
    "mini-sudoku": ["Puzzle"],
    "patches": ["Puzzle"],
    "queens": ["Puzzle"],
    "tango": ["Puzzle"],
    "tic-tac-toe": ["Board"],
    "zip": ["Puzzle"],
    "orbital-siege": ["Strategy", "Arcade"],
    "backrooms-infestation": ["Horror", "Survival"],
    "wave-defense": ["Strategy", "Shooter"],
    "squarelords": ["Strategy", "Board"],
    "hexarch": ["Strategy", "Board"],
    "tower-defense": ["Strategy"],
    "society-ultra": ["Simulation", "Online"],
    "asteroids": ["Shooter", "Arcade"],
    "road-racer": ["Racing"],
    "super-mario": ["Adventure", "Action"],
    "dino-run": ["Arcade", "Action"],
    "tower": ["Skill", "Arcade"],
    "codequest": ["Action", "Arcade"],
    "hextris": ["Puzzle", "Arcade"],
    "flappy-bird": ["Skill", "Arcade"],
    "neon-breaker": ["Arcade", "Skill"],
    "neon-catch": ["Arcade", "Skill"],
    "neon-core": ["Arcade", "Action"],
    "neon-rise": ["Arcade", "Action"],
    "neon-void": ["Arcade", "Skill"],
}

CATEGORY_RULES = [
    ("Horror", re.compile(r"(granny|horror|scary|night|zombie|dead|monster|slender|haunted|creepy|survival)", re.I)),
    ("Shooter", re.compile(r"(shoot|gun|sniper|battle|shootout|fps|aim|arena|rocket|blaster|war)", re.I)),
    ("Skill", re.compile(r"(skill|precision|timing|platform|parkour|climb|jump|reflex|reaction|mastery)", re.I)),
    ("Racing", re.compile(r"(race|racing|drive|drift|car|bike|motor|traffic|speed|kart)", re.I)),
    ("Sport", re.compile(r"(football|basket|tennis|soccer|sport|golf|baseball|boxing|pingpong|volley|ball)", re.I)),
    ("Puzzle", re.compile(r"(puzzle|2048|merge|match|logic|maze|tile|mind|memory|word|block)", re.I)),
    ("Adventure", re.compile(r"(adventure|quest|story|explore|escape|run|survive|journey|mission)", re.I)),
    ("Action", re.compile(r"(action|arcade|fighter|battle|combat|crazy|stunt|dash|jump)", re.I)),
    ("Simulation", re.compile(r"(sim|simulator|builder|idle|clicker|economy|craft|farm|tycoon)", re.I)),
    ("Strategy", re.compile(r"(strategy|tower|defense|build|tactics|manager)", re.I)),
    ("Online", re.compile(r"(online|multiplayer|2player|2 player|io|server|arena|party|battle)", re.I)),
]

def slugify(filename):
    base = re.sub(r"\.(html|htm)$", "", filename, flags=re.I)
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return base or "game"

def clean_name(filename):
    if filename.lower() in NAME_OVERRIDES:
        return NAME_OVERRIDES[filename.lower()]
    s = re.sub(r"\.(html|htm)$", "", filename, flags=re.I)
    s = re.sub(r"[_-]+", " ", s)
    s = re.sub(r"^(\d)([A-Z])", r"\1 \2", s)
    s = re.sub(r"(\d)([a-z])", r"\1 \2", s)
    s = re.sub(r"([a-z])(\d)", r"\1 \2", s)
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", s)
    s = re.sub(r"(?<=\s)([A-Z])([a-z])", r"\1 \2", s)
    s = re.sub(r"(?<=[a-z])(?=[A-Z][a-z])", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    words = s.split()
    out = []
    for w in words:
        low = w.lower()
        if low in ("lol", "io", "td", "vr", "fps", "2d", "3d", "4k", "ai", "vs"):
            out.append(w.upper())
        elif low in ("of", "the", "a", "an", "and", "or", "to", "in", "on", "for", "with"):
            out.append(low)
        elif re.fullmatch(r"(\d+|\w{1,2})", w):
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out).replace("3 D", "3D").replace("2 D", "2D").replace("4 K", "4K").replace(" Vs ", " vs ")

def categories_for(filename):
    hay = filename.lower()
    tags = [name for name, rx in CATEGORY_RULES if rx.search(hay)]
    return tags if tags else ["Arcade"]

def load_existing_games():
    with open(G_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    existing = set()
    for game in data["games"]:
        existing.add(game["url"].lower())
    return data, existing

def scan_games_folder():
    games = []
    
    # Root level HTML files
    for name in sorted(os.listdir(GAMES_FOLDER)):
        low = name.lower()
        if low in EXCLUDES:
            continue
        if not low.endswith((".html", ".htm")):
            continue
        full = os.path.join(GAMES_FOLDER, name)
        if not os.path.isfile(full):
            continue
        
        display = clean_name(name)
        cats = categories_for(name)
        url = f"/gamefile/{name}"
        thumbnail = f"png/games/{slugify(name)}.webp"
        
        games.append({
            "name": display,
            "url": url,
            "thumbnail": thumbnail,
            "frameType": "iframe",
            "categories": cats
        })
    
    # Subdirectories with index.html
    for name in sorted(os.listdir(GAMES_FOLDER)):
        low = name.lower()
        if low in FOLDER_EXCLUDES:
            continue
        full = os.path.join(GAMES_FOLDER, name)
        if not os.path.isdir(full):
            continue
        
        inner = [f for f in os.listdir(full) if f.lower().endswith((".html", ".htm"))]
        if not inner:
            continue
        entry_html = "index.html" if "index.html" in inner else inner[0]
        
        display = FOLDER_NAME_OVERRIDES.get(low, clean_name(name))
        cats = CATEGORY_OVERRIDES.get(low, categories_for(name))
        url = f"/games/{name}/{entry_html}"
        thumbnail = f"png/games/{slugify(name)}.webp"
        
        games.append({
            "name": display,
            "url": url,
            "thumbnail": thumbnail,
            "frameType": "iframe",
            "categories": cats
        })
    
    return games

def main():
    data, existing_urls = load_existing_games()
    print(f"Existing games in g.json: {len(existing_urls)}")
    
    folder_games = scan_games_folder()
    print(f"Games found in games folder: {len(folder_games)}")
    
    new_games = []
    for game in folder_games:
        if game["url"].lower() not in existing_urls:
            new_games.append(game)
            existing_urls.add(game["url"].lower())
    
    print(f"New games to add: {len(new_games)}")
    
    if new_games:
        # Add new games to the list
        data["games"].extend(new_games)
        
        # Sort by name for consistency
        data["games"].sort(key=lambda x: x["name"].lower())
        
        # Write back
        with open(G_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        print("Added games:")
        for g in new_games:
            print(f"  - {g['name']} -> {g['url']}")
    else:
        print("No new games to add")

if __name__ == "__main__":
    main()