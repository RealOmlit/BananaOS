#!/usr/bin/env python3
"""
UBG Ultra — Game Catalog Builder

Scans the 'games' folder for HTML game files and builds the catalog used by
the app. Works both as a CLI script and as an importable module so play.py can
re-scan on demand.

    python generate_games.py            # rebuild assets/js/games.json
    from generate_games import build_catalog, write_catalog

Features:
  - Registers every .html/.htm file (excluding index.html and the app itself)
  - Cleans filenames into friendly display names
  - Auto-tags categories by name heuristics (mirrors the client rules)
  - Picks a custom thumbnail if assets/media/icons/<slug>.* exists
"""

import json
import os
import re
import tempfile

EXCLUDES = {
    "index.html",
    "ubg-ultra.html",
}

_ICON_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico")

# Per-category styling for dynamic fallback thumbnails (emoji + gradient).
CATEGORY_STYLE = {
    "Horror":      {"emoji": "\U0001F47B", "color": ["#4a1030", "#12011f"]},
    "Shooter":     {"emoji": "\U0001F52B", "color": ["#20305e", "#0a1226"]},
    "Skill":       {"emoji": "\U0001F3AF", "color": ["#0e4d3a", "#041c16"]},
    "Racing":      {"emoji": "\U0001F3CE", "color": ["#5e1d20", "#1a0a12"]},
    "Sport":       {"emoji": "\u26BD", "color": ["#0f4d2e", "#072212"]},
    "Puzzle":      {"emoji": "\U0001F9E9", "color": ["#3b2a66", "#140b2b"]},
    "Adventure":   {"emoji": "\U0001F5FA", "color": ["#1d4d5e", "#0a1d26"]},
    "Action":      {"emoji": "\u26A1", "color": ["#4d3d0f", "#1c1505"]},
    "Simulation":  {"emoji": "\U0001F6E0", "color": ["#3b3b4d", "#14141f"]},
    "Strategy":    {"emoji": "\U0001F3F0", "color": ["#264d1d", "#0c1d0a"]},
    "Online":      {"emoji": "\U0001F310", "color": ["#0f3b4d", "#051a24"]},
    "Arcade":      {"emoji": "\U0001F3AE", "color": ["#3d1d66", "#150826"]},
    "Board":       {"emoji": "\u265F", "color": ["#3a3a2a", "#121210"]},
}
DEFAULT_STYLE = {"emoji": "\U0001F3B9", "color": ["#23233a", "#0b0b17"]}

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

# Explicit overrides for games the heuristics get wrong or miss.
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
    "slitherio.html": "Slither.io",
    "diepio.html": "Diep.io",
    "mopeio.html": "Mope.io",
    "deeeepio.html": "Deeeep.io",
    "starveio.html": "Starve.io",
    "zombsio.html": "Zombs.io",
    "zombsroyaleio.html": "Zombs Royale.io",
    "krunkerio.html": "Krunker.io",
    "shellshockio.html": "Shell Shockers.io",
    "evio.html": "Ev.io",
    "warbotio.html": "Warbot.io",
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
    # --- Common game name fixes ---
    "ageofwar.html": "Age of War",
    "ageofwar2.html": "Age of War 2",
    "agesofconflict.html": "Ages of Conflict",
    "amongus.html": "Among Us",
    "angrybirds.html": "Angry Birds",
    "angrybirdsshowdown.html": "Angry Birds Showdown",
    "angrybirdsspace.html": "Angry Birds Space",
    "awesometanks.html": "Awesome Tanks",
    "awesometanks2.html": "Awesome Tanks 2",
    "baconmaydie.html": "Bacon May Die",
    "badicecream.html": "Bad Ice Cream",
    "badicecream2.html": "Bad Ice Cream 2",
    "badicecream3.html": "Bad Ice Cream 3",
    "badparenting.html": "Bad Parenting",
    "badpiggies.html": "Bad Piggies",
    "baldisbasics.html": "Baldi's Basics",
    "baseballbros.html": "Baseball Bros",
    "basketballlegends.html": "Basketball Legends",
    "basketballstars.html": "Basketball Stars",
    "basketbros.html": "Basket Bros",
    "basketrandom.html": "Basket Random",
    "bitplanes.htm": "Bit Planes",
    "blockysnakes.html": "Blocky Snakes",
    "blumgiracers.html": "Blumgi Racers",
    "blumgirocket.html": "Blumgi Rocket",
    "bobtherobber.html": "Bob The Robber",
    "bobtherobber2.html": "Bob The Robber 2",
    "bobtherobber5.html": "Bob The Robber 5",
    "bouncymotors.html": "Bouncy Motors",
    "bowmasters.html": "Bow Masters",
    "bubbleshooter.html": "Bubble Shooter",
    "candycrush.html": "Candy Crush",
    "capybaraclicker.html": "Capybara Clicker",
    "cardrawing.html": "Car Drawing",
    "carkingarena.html": "Car King Arena",
    "clashofvikings.html": "Clash of Vikings",
    "crazycars.html": "Crazy Cars",
    "crazycrashlanding.html": "Crazy Crash Landing",
    "crazymotorcycle.html": "Crazy Motorcycle",
    "deathchase.html": "Death Chase",
    "demolitionderbycrashracing.html": "Demolition Derby Crash Racing",
    "doodlejump.html": "Doodle Jump",
    "drawclimber.html": "Draw Climber",
    "dreadheadparkour.htm": "Dreadhead Parkour",
    "ducklife.html": "Duck Life",
    "ducklife2.html": "Duck Life 2",
    "ducklife3.html": "Duck Life 3",
    "ducklife4.html": "Duck Life 4",
    "ducklife5.html": "Duck Life 5",
    "ducklingsio.html": "Ducklings.io",
    "eagleride.html": "Eagle Ride",
    "earntodie.html": "Earn to Die",
    "earntodie2.html": "Earn to Die 2",
    "eggycar.html": "Eggy Car",
    "escaperoad.html": "Escape Road",
    "escaperoad2.html": "Escape Road 2",
    "fancypantsadventure.html": "Fancy Pants Adventure",
    "fancypantsadventure2.html": "Fancy Pants Adventure 2",
    "fireboyandwatergirl.html": "Fireboy and Watergirl",
    "fireboyandwatergirl2.html": "Fireboy and Watergirl 2",
    "fireboyandwatergirl3.html": "Fireboy and Watergirl 3",
    "fireboyandwatergirl4.html": "Fireboy and Watergirl 4",
    "flappybird.html": "Flappy Bird",
    "footballbros.html": "Football Bros",
    "footballlegends.html": "Football Legends",
    "freerider3.html": "Free Rider 3",
    "fruitninja.html": "Fruit Ninja",
    "funnybattle.html": "Funny Battle",
    "funnybattle2.html": "Funny Battle 2",
    "funnymadracing.html": "Funny Mad Racing",
    "funnyshooter2.html": "Funny Shooter 2",
    "geometrydash.html": "Geometry Dash",
    "geometrydashlite.html": "Geometry Dash Lite",
    "geometryvibes.html": "Geometry Vibes",
    "getawayshootout.htm": "Getaway Shootout",
    "getontop.html": "Get On Top",
    "gladihoppers.html": "Gladihoppers",
    "googlebaseball.html": "Google Baseball",
    "googledino.html": "Google Dino",
    "guesstheiranswer.html": "Guess Their Answer",
    "happywheels.html": "Happy Wheels",
    "helixjump.html": "Helix Jump",
    "highwaytraffic.html": "Highway Traffic",
    "hillclimbracinglite.html": "Hill Climb Racing Lite",
    "houseofhazards.html": "House of Hazards",
    "hoverracerdrive.html": "Hover Racer Drive",
    "idlebreakout.html": "Idle Breakout",
    "ironsnout.html": "Iron Snout",
    "jetpackjoyride.html": "Jetpack Joyride",
    "johnnytrigger.html": "Johnny Trigger",
    "jumpingshell.html": "Jumping Shell",
    "karatebros.html": "Karate Bros",
    "kartbros.html": "Kart Bros",
    "learntofly.html": "Learn to Fly",
    "learntofly2.html": "Learn to Fly 2",
    "learntofly3.html": "Learn to Fly 3",
    "learntoflyidle.html": "Learn to Fly Idle",
    "leveldevil.html": "Level Devil",
    "madalinstuntcars2.html": "Madalin Stunt Cars 2",
    "melonplayground.html": "Melon Playground",
    "mergeroundracers.html": "Merge Round Racers",
    "monkeymart.htm": "Monkey Mart",
    "monstertracks.html": "Monster Tracks",
    "noobminer.html": "Noob Miner",
    "oppositeday.html": "Opposite Day",
    "pacman.html": "Pac-Man",
    "papasbakeria.html": "Papa's Bakeria",
    "papasburgeria.html": "Papa's Burgeria",
    "papascheeseria.html": "Papa's Cheeseria",
    "papascupcakeria.html": "Papa's Cupcakeria",
    "papasdonuteria.html": "Papa's Donuteria",
    "papasfreezeria.html": "Papa's Freezeria",
    "papashotdoggeria.html": "Papa's Hot Doggeria",
    "papaspancakeria.html": "Papa's Pancakeria",
    "papaspastaria.html": "Papa's Pastaria",
    "papaspizzeria.html": "Papa's Pizzeria",
    "papasscooperia.html": "Papa's Scooperia",
    "papassushiria.html": "Papa's Sushiria",
    "papastacomia.html": "Papa's Taco Mia",
    "papaswingeria.html": "Papa's Wingeria",
    "pingpongchaos.html": "Ping Pong Chaos",
    "pixelspeedrun.html": "Pixel Speedrun",
    "plonky.html": "Plonky",
    "poorbunny.html": "Poor Bunny",
    "ragdollhit.html": "Ragdoll Hit",
    "ragdollsoccer.html": "Ragdoll Soccer",
    "retrobowl.html": "Retro Bowl",
    "retrobowlcollege.html": "Retro Bowl College",
    "retrohighway.html": "Retro Highway",
    "retropingpong.html": "Retro Ping Pong",
    "rocketsoccerderby.html": "Rocket Soccer Derby",
    "rooftopsnipers2.html": "Rooftop Snipers 2",
    "sandgame.html": "Sand Game",
    "shortlife.html": "Short Life",
    "slowroads.html": "Slow Roads",
    "snowballio.html": "Snowball.io",
    "soccerbros.html": "Soccer Bros",
    "spacebarclicker.html": "Spacebar Clicker",
    "spaceiskey.html": "Space Is Key",
    "spaceiskey2.html": "Space Is Key 2",
    "spacewaves.html": "Space Waves",
    "speedstars.html": "Speed Stars",
    "stickarchersbattle.html": "Stick Archers Battle",
    "stickfighter.html": "Stick Fighter",
    "stickmanhook.html": "Stickman Hook",
    "stickmerge.html": "Stick Merge",
    "superstarcar.html": "Superstar Car",
    "tabletennisworldtour.html": "Table Tennis World Tour",
    "templeofboom.html": "Temple of Boom",
    "thereisnog.html": "There Is No Game",
    "theyarecoming.html": "They Are Coming",
    "trapthecat.html": "Trap The Cat",
    "triviacrack.html": "Trivia Crack",
    "tubejumpers.html": "Tube Jumpers",
    "tunnelrush.html": "Tunnel Rush",
    "unicyclehero.html": "Unicycle Hero",
    "volleyrandom.html": "Volley Random",
    "wartheknights.html": "War The Knights",
    "webecomewhatwebehold.html": "We Become What We Behold",
    "wheeliebike.html": "Wheelie Bike",
    "wordleunlimited.html": "Wordle Unlimited",
    "wrestlebros.html": "Wrestle Bros",
    "zombierush.html": "Zombie Rush",
    "bloonsTD2.html": "Bloons TD 2",
    "bloonsTD3.html": "Bloons TD 3",
    "bloonsTD4.html": "Bloons TD 4",
    "bloonsTD5.html": "Bloons TD 5",
    "choppyorc.html": "Choppy Orc",
    "cuttherope.html": "Cut The Rope",
    "evilglitch.html": "Evil Glitch",
    "picosschool.html": "Pico's School",
    "riddleschool.html": "Riddle School",
    "riddleschool2.html": "Riddle School 2",
    "riddleschool3.html": "Riddle School 3",
    "riddleschool4.html": "Riddle School 4",
    "riddleschool5.html": "Riddle School 5",
    "riddletransfer.html": "Riddle Transfer",
    "riddletransfer2.html": "Riddle Transfer 2",
    "stateio.html": "State.io",
    "taproad.html": "Tap Road",
    "tinyfishing.html": "Tiny Fishing",
    # --- open-source games added from subfolders ---
    "tetris": "Tetris",
    "road-racer": "Road Racer",
    "asteroids": "Asteroids",
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
    # --- second batch of open-source games ---
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
    # --- third batch (epoch-td style) ---
    "orbital-siege": "Orbital Siege",
    "backrooms-infestation": "Backrooms Infestation",
    "wave-defense": "Wave Defense",
    "squarelords": "Square Lords",
    "hexarch": "Hexarch",
    "tower-defense": "HTML5 Tower Defense",
    # --- Society Ultra (3D multiplayer sandbox) ---
    "society-ultra": "Society Ultra",
}

# Sensible categories for the added open-source games.
CATEGORY_OVERRIDES = {
    "tetris": ["Puzzle", "Arcade"],
    "road-racer": ["Racing"],
    "asteroids": ["Shooter", "Arcade"],
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
    # --- second batch ---
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
    # --- third batch ---
    "orbital-siege": ["Strategy", "Arcade"],
    "backrooms-infestation": ["Horror", "Survival"],
    "wave-defense": ["Strategy", "Shooter"],
    "squarelords": ["Strategy", "Board"],
    "hexarch": ["Strategy", "Board"],
    "tower-defense": ["Strategy"],
    # --- Society Ultra ---
    "society-ultra": ["Simulation", "Online"],
}

FOLDER_EXCLUDES = {"assets", "__pycache__", "media"}

# The multi-file games use numeric directory names on disk so the library
# contents do not expose their titles in File Explorer.  Keep the original
# folder slug here so the catalog can still render the real name, category,
# and artwork in memory.
FOLDER_ALIASES = {
    "1": "109",
    "2": "11-f",
    "3": "2048",
    "4": "asteroids",
    "5": "backrooms-infestation",
    "6": "Bowmasters",
    "7": "chess",
    "8": "codequest",
    "9": "connect-four",
    "10": "cookie-clicker",
    "11": "dino-run",
    "12": "epoch-td",
    "13": "flappy-bird",
    "14": "hexarch",
    "15": "hextris",
    "16": "lights-out",
    "17": "memory",
    "18": "minesweeper",
    "19": "mini-sudoku",
    "20": "neon-breaker",
    "21": "neon-catch",
    "22": "neon-core",
    "23": "neon-rise",
    "24": "neon-void",
    "25": "orbital-siege",
    "26": "OvO",
    "27": "pac-hunt",
    "28": "patches",
    "29": "platformer",
    "30": "queens",
    "31": "road-racer",
    "32": "society-ultra",
    "33": "solitaire",
    "34": "squarelords",
    "35": "super-mario",
    "36": "tango",
    "37": "Temple-Run-2",
    "38": "tetris",
    "39": "tic-tac-toe",
    "40": "tower",
    "41": "tower-defense",
    "42": "wave-defense",
    "43": "zip",
}


def slugify(filename):
    """Turn 'geometrydashlite.html' into a filesystem-safe slug like
    'geometrydashlite' or '1v1-lol'."""
    base = re.sub(r"\.(html|htm)$", "", filename, flags=re.I)
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return base or "game"


def clean_name(filename):
    """Human-friendly title from a filename."""
    key = filename.lower()
    for k, v in NAME_OVERRIDES.items():
        if k.lower() == key:
            return v
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
    """Return category tags based on the filename/display name."""
    hay = filename.lower()
    tags = [name for name, rx in CATEGORY_RULES if rx.search(hay)]
    return tags if tags else ["Arcade"]


def style_for(categories):
    """Pick emoji + gradient for the dynamic fallback thumbnail."""
    for cat in categories:
        if cat in CATEGORY_STYLE:
            return CATEGORY_STYLE[cat]
    return DEFAULT_STYLE


# Explicit icon overrides for games whose filenames don't match an icon slug.
ICON_OVERRIDES = {
    "8ballclassic.html": "8ball.webp",
    "sandgame.html": "sand.webp",
}


def _build_icon_index(games_folder):
    """Map compact slug (letters+digits only) -> icon path relative to icons dir.

    Only real artwork at the top level of the icons dir is used; the 'gen/'
    gradient placeholders are excluded so games without a genuine image get an
    emoji + gradient card instead."""
    idx = {}
    icons_dir = os.path.join(games_folder, "assets", "media", "icons")
    if os.path.isdir(icons_dir):
        for name in os.listdir(icons_dir):
            full = os.path.join(icons_dir, name)
            if os.path.isdir(full):
                continue
            base, ext = os.path.splitext(name)
            if ext.lower() not in _ICON_EXTS or name.lower() == "default.png":
                continue
            key = re.sub(r"[^a-z0-9]", "", base.lower())
            if key and key not in idx:
                idx[key] = name
    artwork = os.path.join(os.path.dirname(games_folder), "truffled-main", "public", "png", "games")
    if os.path.isdir(artwork):
        for name in sorted(os.listdir(artwork)):
            stem, ext = os.path.splitext(name)
            key = re.sub(r"[^a-z0-9]", "", stem.lower())
            if ext.lower() in _ICON_EXTS and key:
                idx.setdefault(key, "/artwork/" + name)
    return idx


def find_icon(games_folder, filename, index):
    """Find a custom thumbnail by slug, else fall back to the shared default."""
    if filename.lower() in ICON_OVERRIDES:
        return "assets/media/icons/" + ICON_OVERRIDES[filename.lower()]
    slug = slugify(filename)
    compact = re.sub(r"[^a-z0-9]", "", slug)
    for key in (compact, slug):
        if key in index:
            return index[key] if index[key].startswith("/") else "assets/media/icons/" + index[key].replace("\\", "/")
    return "assets/media/icons/default.png"


def build_catalog(games_folder):
    """Scan a folder and return the game catalog list.

    Scans top-level .html files plus subfolders that contain an index.html
    (registered as "subfolder/index.html" so multi-file games work)."""
    catalog = []
    try:
        names = sorted(os.listdir(games_folder))
    except OSError:
        return catalog
    icon_index = _build_icon_index(games_folder)
    for name in names:
        low = name.lower()
        if low in EXCLUDES:
            continue
        full = os.path.join(games_folder, name)
        if os.path.isdir(full):
            if low in FOLDER_EXCLUDES:
                continue
            inner = sorted(f for f in os.listdir(full) if f.lower().endswith((".html", ".htm")))
            if not inner:
                continue
            entry_html = "index.html" if "index.html" in inner else inner[0]
            source_name = FOLDER_ALIASES.get(name, name)
            source_low = source_name.lower()
            display = NAME_OVERRIDES.get(source_low, clean_name(source_name))
            cats = CATEGORY_OVERRIDES.get(source_low, categories_for(source_name))
            icon = find_icon(games_folder, source_name, icon_index)
            entry = {
                "name": display,
                "link": name + "/" + entry_html,
                "image": icon,
                "categories": cats,
            }
            if icon.endswith("default.png"):
                style = style_for(cats)
                entry["emoji"] = style["emoji"]
                entry["color"] = style["color"]
            catalog.append(entry)
            continue
        if not low.endswith((".html", ".htm")):
            continue
        cats = categories_for(name)
        icon = find_icon(games_folder, name, icon_index)
        entry = {
            "name": clean_name(name),
            "link": name,
            "image": icon,
            "categories": cats,
        }
        if icon.endswith("default.png"):
            style = style_for(cats)
            entry["emoji"] = style["emoji"]
            entry["color"] = style["color"]
        catalog.append(entry)
    # The bundled HTML collection is served at /library/, preserving relative assets.
    base = os.path.dirname(os.path.abspath(games_folder))
    zones_path = os.path.join(base, "zones.json")
    if os.path.isfile(zones_path):
        with open(zones_path, encoding="utf-8") as f:
            zones = json.load(f)
        by_id = {str(z.get("id")): z for z in zones}
        for entry in catalog:
            disk_stem = entry["link"].split("/")[0]
            stem = FOLDER_ALIASES.get(disk_stem, disk_stem)
            match = re.fullmatch(r"(\d+)(?:[-][\w-]+|ff)?(?:\.html)?", stem)
            if match and match[1] in by_id and re.match(r"^\d+(?:\s|$)", entry["name"]):
                entry["name"] = by_id[match[1]]["name"] + " (local edition)"
        seen = {re.sub(r"[^a-z0-9]", "", g["name"].lower()) for g in catalog}
        for zone in zones:
            url = zone.get("url", "")
            if zone.get("id", -1) < 0 or not url.startswith("{HTML_URL}/"):
                continue
            filename = url.removeprefix("{HTML_URL}/")
            if not os.path.isfile(os.path.join(base, "html-main", filename)):
                continue
            key = re.sub(r"[^a-z0-9]", "", zone["name"].lower())
            if key in seen:
                for existing in catalog:
                    if re.sub(r"[^a-z0-9]", "", existing["name"].lower()) == key:
                        existing.setdefault("alternates", []).append("/library/" + filename)
                        break
                continue
            seen.add(key)
            cats = categories_for(zone["name"])
            style = style_for(cats)
            catalog.append({"name": zone["name"], "link": "/library/" + filename,
                            "image": find_icon(games_folder, zone["name"], icon_index),
                            "categories": cats, "emoji": style["emoji"], "color": style["color"]})
    # Duplicate names are alternate launch sources, not additional games.
    unique = {}
    for entry in catalog:
        if entry["name"].startswith("[!]") or "emulator" in entry["name"].lower():
            continue
        key = re.sub(r"[^a-z0-9]", "", entry["name"].lower())
        if key in unique:
            unique[key].setdefault("alternates", []).append(entry["link"])
        else:
            unique[key] = entry
    return sorted(unique.values(), key=lambda g: g["name"].casefold())


def write_catalog(games_folder):
    """Build and atomically persist the catalog to assets/js/games.json.

    Writing directly to the live file can leave it empty when a scan is
    interrupted after opening it.  A same-directory temporary file plus
    ``os.replace`` means readers see either the previous complete catalog or
    the new complete catalog, never a partially-written one.
    """
    catalog = build_catalog(games_folder)
    json_path = os.path.join(games_folder, "assets", "js", "games.json")
    json_dir = os.path.dirname(json_path)
    os.makedirs(json_dir, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="games-", suffix=".json.tmp", dir=json_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, json_path)
    except Exception:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise
    return catalog


def main():
    games_folder = os.path.dirname(os.path.abspath(__file__))
    catalog = write_catalog(games_folder)
    print("[OK] Registered %d games" % len(catalog))
    print("  Saved to: %s" % os.path.join(games_folder, "assets", "js", "games.json"))


if __name__ == "__main__":
    main()
