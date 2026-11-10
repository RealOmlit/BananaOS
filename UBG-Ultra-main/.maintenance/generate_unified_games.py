import json
import os
import re
from pathlib import Path

def load_g_json():
    with open('truffled-main/public/js/json/g.json', 'r', encoding='utf-8') as f:
        return json.load(f)['games']

def load_zones_json():
    with open('zones.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def scan_games_folder():
    games_dir = Path('games')
    games = []
    for file in games_dir.glob('*.html'):
        if file.name in ['index.html', 'play.bat', 'desktop.ini', 'FlashpointSuperHallOfFame.json']:
            continue
        name = file.stem.replace('-', ' ').replace('_', ' ')
        name = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', name)
        name = re.sub(r'([A-Za-z])(\d+)', r'\1 \2', name)
        name = ' '.join(word.capitalize() for word in name.split())
        games.append({
            'name': name,
            'url': f'/games/{file.name}',
            'thumbnail': f'/png/games/{file.stem}.webp',
            'frameType': 'iframe',
            'source': 'games_folder'
        })
    for dir_path in games_dir.iterdir():
        if dir_path.is_dir() and dir_path.name not in ['__pycache__', '2048', 'assets', 'asteroids', 'backrooms-infestation', 'chess', 'codequest', 'connect-four', 'cookie-clicker', 'dino-run', 'epoch-td', 'flappy-bird', 'hexarch', 'hextris', 'lights-out', 'memory', 'minesweeper', 'mini-sudoku', 'neon-breaker', 'neon-catch', 'neon-core', 'neon-rise', 'neon-void', 'patches', 'platformer', 'road-racer', 'society-ultra', 'super-mario', 'tango', 'tower', 'tower-defense', 'wave-defense', 'zip']:
            index_file = dir_path / 'index.html'
            if index_file.exists():
                name = dir_path.name.replace('-', ' ').replace('_', ' ')
                name = ' '.join(word.capitalize() for word in name.split())
                games.append({
                    'name': name,
                    'url': f'/games/{dir_path.name}/index.html',
                    'thumbnail': f'/png/games/{dir_path.name}.webp',
                    'frameType': 'iframe',
                    'source': 'games_folder'
                })
    return games

def scan_html_main_folder(zones_data=None):
    html_main_dir = Path('html-main')
    games = []
    if not html_main_dir.exists():
        return games
    
    # Build a mapping from filename to zone data
    zone_by_file = {}
    zone_by_id = {}
    if zones_data:
        for zone in zones_data:
            if zone.get('id', -2) >= 0 and zone.get('url', '').startswith('{HTML_URL}/'):
                filename = zone['url'].replace('{HTML_URL}/', '')
                zone_by_file[filename] = zone
                zone_by_id[zone['id']] = zone
    
    for file in html_main_dir.glob('*.html'):
        if file.name in ['index.html', 'play.bat', 'desktop.ini']:
            continue
        
        # Try to get proper name from zones.json
        if file.name in zone_by_file:
            zone = zone_by_file[file.name]
            name = zone['name']
            zone_id = zone['id']
        else:
            # Try to match by base ID (e.g., 114.html -> ID 114)
            stem = file.stem
            # Extract numeric ID from filename (e.g., "164-temp" -> 164)
            id_match = re.match(r'(\d+)', stem)
            if id_match:
                zone_id = int(id_match.group(1))
                if zone_id in zone_by_id:
                    zone = zone_by_id[zone_id]
                    name = zone['name'] + " (variant)"
                else:
                    name = file.stem.replace('-', ' ').replace('_', ' ')
                    name = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', name)
                    name = re.sub(r'([A-Za-z])(\d+)', r'\1 \2', name)
                    name = ' '.join(word.capitalize() for word in name.split())
                    zone_id = None
            else:
                name = file.stem.replace('-', ' ').replace('_', ' ')
                name = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', name)
                name = re.sub(r'([A-Za-z])(\d+)', r'\1 \2', name)
                name = ' '.join(word.capitalize() for word in name.split())
                zone_id = None
        
        games.append({
            'name': name,
            'url': f'/html-main/{file.name}',
            'thumbnail': f'/png/games/{file.stem}.webp',
            'frameType': 'iframe',
            'source': 'html_main',
            'zone_id': zone_id
        })
    return games

def normalize_name(name):
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.replace('webport', '').replace('web port', '').strip()
    return name

def deduplicate_games(g_json_games, folder_games):
    seen = {}
    all_games = []
    
    for game in g_json_games:
        norm_name = normalize_name(game['name'])
        if norm_name not in seen:
            game['source'] = 'g_json'
            game['alt_names'] = game.get('altNames', [])
            game['normalized_name'] = norm_name
            seen[norm_name] = game
            all_games.append(game)
        else:
            existing = seen[norm_name]
            if 'altNames' in game:
                existing['alt_names'] = list(set(existing.get('alt_names', []) + game['altNames']))
            if game.get('thumbnail') and not existing.get('thumbnail'):
                existing['thumbnail'] = game['thumbnail']
    
    for game in folder_games:
        norm_name = normalize_name(game['name'])
        if norm_name not in seen:
            game['normalized_name'] = norm_name
            game['alt_names'] = []
            seen[norm_name] = game
            all_games.append(game)
        else:
            existing = seen[norm_name]
            if game.get('thumbnail') and not existing.get('thumbnail'):
                existing['thumbnail'] = game['thumbnail']
    
    return all_games

def categorize_game(game):
    name = game['name'].lower()
    url = game.get('url', '').lower()
    
    categories = []
    
    if any(kw in name for kw in ['minecraft', 'terraria', 'starbound', 'raft', 'subnautica', 'scrap mechanic', 'teardown']):
        categories.append('Sandbox')
    if any(kw in name for kw in ['fnaf', 'five nights', 'granny', 'horror', 'scary', 'slender', 'bendy', 'amanda', 'dead plate', 'tattletail', 'poppy', 'backrooms', 'freddy', 'security breach', 'help wanted', 'pizzeria simulator', 'ultimate custom night', 'fazbear', 'a bite at freddy', 'baldi', 'baldis', 'basics', 'education and learning', 'baldi basics']):
        categories.append('Horror')
    if any(kw in name for kw in ['mario', 'sonic', 'zelda', 'kirby', 'donkey kong', 'metroid', 'pokemon', 'pikmin', 'yoshi', 'luigi', 'wario', 'smash bros']):
        categories.append('Nintendo')
    if any(kw in name for kw in ['doom', 'quake', 'half life', 'portal', 'counter strike', 'csgo', 'tf2', 'overwatch', 'valorant', 'apex', 'call of duty', 'battlefield', 'halo', 'destiny', 'borderlands', 'fallout', 'skyrim', 'elder scrolls', 'wolfenstein', 'duke nukem', 'serious sam', 'painkiller']):
        categories.append('FPS')
    if any(kw in name for kw in ['racing', 'drift', 'moto', 'car', 'drive', 'need for speed', 'forza', 'gran turismo', 'burnout', 'trackmania', 'hill climb', 'traffic', 'highway', 'road racer', 'moto x3m', 'bike', 'kart', 'nascar', 'f1', 'rally', 'asphalt', 'real racing', 'csr', 'blumgi', 'racer', 'bolt master', 'drag', 'street race', 'formula', 'grand prix', 'speed']):
        categories.append('Racing')
    if any(kw in name for kw in ['fighting', 'street fighter', 'tekken', 'mortal kombat', 'smash', 'brawl', 'guilty gear', 'blazblue', 'king of fighters', 'injustice', 'dragon ball fighterz', 'naruto', 'one piece', 'jojo', 'punch', 'combat', 'versus', 'vs.', 'choppy orc', 'orc', 'slime', 'slimy', 'brawlhalla', 'rivals of aether', 'nickelodeon all star', 'multiversus', 'super smash flash', 'super smash flash 2', 'ssf2', 'mcleodgaming', 'flash fighting', 'anime fighting', 'mugen', 'ikemen', 'fighter maker', 'fighterz', 'dragon ball z', 'dragon ball super', 'dragon ball gt', 'dragon ball heroes', 'dragon ball legends', 'dragon ball dokkan', 'dragon ball fighterz', 'dragon ball xenoverse', 'dragon ball xenoverse 2', 'dragon ball kakarot', 'dragon ball z kakarot', 'dragon ball z battle of z', 'dragon ball z ultimate tenkaichi', 'dragon ball z burst limit', 'dragon ball z infinite world', 'dragon ball z shin budokai', 'dragon ball z shin budokai 2', 'dragon ball z tenkaichi tag team', 'dragon ball z tenkaichi 3', 'dragon ball z tenkaichi 2', 'dragon ball z tenkaichi', 'dragon ball z budokai tenkaichi', 'dragon ball z budokai tenkaichi 2', 'dragon ball z budokai tenkaichi 3', 'dragon ball z budokai 3', 'dragon ball z budokai 2', 'dragon ball z budokai']):
        categories.append('Fighting')
    if any(kw in name for kw in ['puzzle', 'tetris', '2048', 'sudoku', 'minesweeper', 'solitaire', 'mahjong', 'match', 'bejeweled', 'candy crush', 'bubble', 'peg', 'riddle', 'brain', 'logic', 'escape room', 'the witness', 'portal', 'talos', 'baba is you', 'stephen', 'sausage', 'unpacking', 'block blast', 'merge', 'tile', 'word', 'crossword', 'jigsaw', 'logic', 'brain training', 'bad ice cream', 'badicecream', 'bad icecream', 'bloxorz', 'bloxors', 'breaklock', '99 balls', 'blumgi', 'cut the rope', 'where is my water', 'angry birds', 'plants vs zombies', 'pvz', 'monument valley', 'the room', 'rusty lake', 'cube escape', 'escape game', 'point and click', 'hidden object', 'mahjong', 'solitaire', 'freecell', 'spider solitaire', 'klondike', 'yukon', 'golf solitaire', 'pyramid solitaire', 'tripeaks', 'bad piggies', 'badpiggies', 'amazing alex', 'contraption', 'incredible machine', 'fantastic contraption', 'world of goo', 'bridge constructor', 'poly bridge', 'bridge builder', 'engineering', 'physics puzzle', 'logic puzzle', 'maze', 'labyrinth', 'sliding puzzle', 'block puzzle', 'number puzzle', 'word puzzle', 'pattern', 'sequence']):
        categories.append('Puzzle')
    if any(kw in name for kw in ['platformer', 'jump', 'run', 'sonic', 'mario', 'celeste', 'hollow knight', 'meat boy', 'super meat', 'getting over it', 'only up', 'gear', 'hollow', 'knight', 'ori', 'dead cells', 'hades', 'roguelike', 'metroidvania', 'castlevania', 'blasphemous', 'end er lilies', 'bacon may die', 'bad ice cream', 'badicecream', 'bad icecream', 'fireboy', 'watergirl', 'red ball', 'run 1', 'run 2', 'run 3', 'ovo', 'vex', 'n', 'super mario', 'donkey kong country', 'rayman', 'shovel knight', 'cuphead', 'hollow knight', 'shantae', 'wonder boy', 'bob the robber', 'bobtherobber', 'cave story', 'limbo', 'inside', 'little nightmares', 'playdead', 'grim fandango', 'psychonauts', 'ratchet', 'clank', 'jak', 'daxter', 'sly cooper', 'ty the tasmanian tiger', 'spyro', 'crash bandicoot', 'banjo kazooie', 'conker', 'glover', 'rocket robot', 'chibi robo', 'klonoa', 'klonoa 2', 'klonoa 3']):
        categories.append('Platformer')
    if any(kw in name for kw in ['shooter', 'gun', 'bullet', 'hell', 'enter the gungeon', 'nuclear throne', 'risk of rain', 'vampire survivors', 'brotato', '20 minutes', '10 minutes', 'survivor', 'holo cure', 'holo', 'cure', 'awesome tanks', 'bowmasters', 'archero', 'tank', 'bullet', 'archery', 'rifle', 'sniper', 'pistol', 'shotgun', 'blaster', 'turret', 'defense', 'tower defense', 'artillery', 'cannon', 'missile', 'rocket', 'bazooka', 'bazooka boy', 'ball blast', 'basket battle', 'ragdoll', 'hitman', 'sniper', 'assassin', 'contract killer', 'gun mayhem', 'stickman', 'gunfight', 'shootout', 'gun game', 'artillery', 'bomb', 'blade ball', 'blockpost', 'block post', 'forward assault', 'critical strike', 'bullet force', 'maskgun', 'war brokers', 'ev.io', 'shell shockers', 'krunker', 'superhot', 'time shooter']):
        categories.append('Shooter')
    if any(kw in name for kw in ['sport', 'soccer', 'football', 'basketball', 'baseball', 'tennis', 'golf', 'bowling', 'pool', 'billiard', 'volley', 'cricket', 'rugby', 'hockey', 'skate', 'bike', 'bmx', 'snowboard', 'surf', 'ping pong', 'table tennis', 'badminton', 'boxing', 'wrestling', 'mma', 'ufc', 'fifa', 'nba', 'nfl', 'mlb', 'blackjack', 'black jack', 'poker', 'casino', 'card game', 'solitaire', 'hearts', 'spades', 'bridge', 'uno', 'rummy', 'small world cup', 'world cup', 'football', 'soccer', 'penalty', 'free kick', 'corner kick', 'goal', 'striker', 'goalkeeper', 'referee', 'offside', 'champions league', 'premier league', 'la liga', 'serie a', 'bundesliga', 'ligue 1', 'mls', 'copa america', 'euro', 'world cup', 'club world cup', 'basket bros', 'basketbros', 'basket battle', 'dunk', 'hoop', 'ncaa', 'march madness', 'final four', 'nba 2k', 'nba live', 'nba jam', 'street ball', 'and1', 'ball is life']):
        categories.append('Sports')
    if any(kw in name for kw in ['strategy', 'tactics', 'turn based', '4x', 'civilization', 'age of empires', 'starcraft', 'command conquer', 'total war', 'crusader kings', 'eu4', 'hoi4', 'stellaris', 'rimworld', 'factorio', 'satisfactory', 'dyson sphere', 'mindustry', 'shapez', 'automation', 'factory', 'logistics', 'transport', 'tycoon', 'simulator', 'management', 'city builder', 'colony', 'survival', 'craft', 'build', 'ages of conflict', 'polytopia', 'hex empire', 'territorial', 'conquest', 'empire', 'kingdom', 'age of war', 'ageofwar', 'chess', 'checkers', 'draughts', 'go', 'weiqi', 'baduk', 'shogi', 'xiangqi', 'chinese chess', 'chess ai', 'stockfish', 'lichess', 'chess.com', 'chess24', 'fide', 'elo', 'grandmaster', 'master', 'candidate master', 'expert', 'class a', 'class b', 'class c', 'class d', 'class e', 'puzzle rush', 'puzzle battle', 'tactics', 'endgame', 'opening', 'middlegame', 'mate in', 'checkmate', 'stalemate', 'fork', 'pin', 'skewer', 'discovered attack', 'double check', 'zwischenzug', 'zugzwang', 'zwischenzug', 'windmill', 'greek gift', 'sacrifice', 'combination', 'tactical motif']):
        categories.append('Strategy')
    if any(kw in name for kw in ['rpg', 'role playing', 'final fantasy', 'dragon quest', 'chronos', 'persona', 'smt', 'shin megami', 'yakuza', 'like a dragon', 'witcher', 'cyberpunk', 'baldur', 'divinity', 'pillars of eternity', 'disco elysium', 'planescape', 'fallout', 'elder scrolls', 'skyrim', 'oblivion', 'morrowind', 'kingdom come', 'deliverance', 'elden ring', 'dark souls', 'demon souls', 'bloodborne', 'sekiro', 'armored core', 'nier', 'automata', 'replicant', 'drakengard', 'xenogears', 'xenosaga', 'chronicle', 'octopath', 'bravely', 'triangle strategy', 'fire emblem', 'tactics ogre', 'final fantasy tactics', 'disgaea', 'yomawari', 'madoka', 'magia record', 'undertale', 'deltarune', 'earthbound', 'mother', 'pokemon', 'dragon quest', 'bravely default']):
        categories.append('RPG')
    if any(kw in name for kw in ['io', 'agar', 'slither', 'diep', 'mope', 'worm', 'snake', 'paper', 'hole', 'crowd', 'city', 'superhero', 'evowars', 'zombs', 'surviv', 'krunker', 'shell shockers', 'bullet force', 'war brokers', 'combat', 'strike', 'contract', 'warfare', 'territorial.io', 'paper.io', 'hole.io', 'crowd city', 'superhero.io']):
        categories.append('.IO Games')
    if any(kw in name for kw in ['flash', 'classic', 'retro', 'old school', 'nes', 'snes', 'gb', 'gba', 'n64', 'ps1', 'ps2', 'dreamcast', 'saturn', 'genesis', 'arcade', 'mame', 'emulator', 'webport', 'gameboy', 'game boy', 'nintendo 64', 'playstation', 'sega', 'atari', 'commodore', 'amiga', 'dos', 'windows 95', 'windows 98', 'asteroids', 'space invaders', 'pac-man', 'pacman', 'donkey kong', 'frogger', 'galaga', 'centipede', 'missile command', 'defender', 'joust', 'robotron', 'sinistar', 'tempest', 'asteroids deluxe', 'lunar lander', 'battlezone', 'red baron', 'star wars', 'empire strikes back', 'return of the jedi', 'pole position', 'outrun', 'after burner', 'space harrier', 'hang on', 'enduro', 'road rash', 'moto racer', 'daytona', 'sega rally', 'ridge racer', 'need for speed', 'grand theft auto', 'gta', 'doom', 'wolfenstein', 'quake', 'duke nukem', 'rise of the triad', 'blake stone', 'corridor 7', 'operation body count', 'island perimeter', 'rocket knight', 'sparkster', 'rocket knight adventures', 'contra', 'metal slug', 'gunstar heroes', 'alien soldier', 'thunder force', 'gradius', 'r-type', 'darius', 'rayforce', 'layer section', 'raystorm', 'raycrisis', 'einhander', 'gradius v', 'parodius', 'twinbee', 'detana twinbee', 'popn twinbee', 'rainbow bell', 'detana!! twinbee', 'donpachi', 'doDonPachi', 'dodonpachi daioujou', 'ketsui', 'espgaluda', 'mushihimesama', 'deathsmiles', 'akiba trip', 'akiba trip 2', 'akiba trip undead', 'akiba trip hellbound']):
        categories.append('Retro')
    if any(kw in name for kw in ['multiplayer', 'online', 'co-op', 'coop', 'party', 'jackbox', 'among us', 'fall guys', 'gang beasts', 'human fall flat', 'move or die', 'stick fight', 'brawlhalla', 'rivals of aether', 'nickelodeon all star', 'multiversus', '1v1', '2 player', '3 player', '4 player', 'local multiplayer', 'online multiplayer']):
        categories.append('Multiplayer')
    if any(kw in name for kw in ['clicker', 'idle', 'incremental', 'cookie', 'adventure capitalist', 'trimps', 'universal paperclips', 'kittens', 'antimatter', 'ngu', 'melvor', 'idleon', 'idle slayer', 'leaf blower', 'progress knight', 'ngu idle', 'cookie clicker', 'clicker heroes', 'realm grinder', 'antimatter dimensions', 'idle miner']):
        categories.append('Idle/Clicker')
    if any(kw in name for kw in ['rhythm', 'beat', 'dance', 'guitar hero', 'rock band', 'osu', 'fnf', 'friday night', 'funkin', 'parappa', 'amplitude', 'rez', 'thumper', 'crypt of the necrodancer', 'necrodancer', 'beat saber', 'synth riders', 'audio trip', 'pistol whip', 'geometry dash', 'rhythm doctor', 'just dance', 'stepmania', 'ddr', 'pump it up', 'sprunki', 'adofai', 'a dance of fire and ice', 'bust a loop', 'buster jam', 'sayonara wild hearts', 'thumper', 'beat saber', 'synth riders', 'pistol whip', 'audio trip', 'just dance', 'stepmania', 'ddr', 'pump it up', 'in the groove', 'beatmania', 'iidx', 'popn music', 'jubeat', 'reflec beat', 'sound voltex', 'museca', 'chunithm', 'maimai', 'ongeki', 'wacca', 'arcade rhythm', 'rhythm game']):
        categories.append('Rhythm')
    if any(kw in name for kw in ['educational', 'math', 'typing', 'geography', 'history', 'science', 'chemistry', 'physics', 'biology', 'programming', 'coding', 'code', 'algorithm', 'data structure', 'khan academy', 'abcya', 'coolmath', 'hooda math', 'math playground', 'prodigy', 'chat bot', 'chatbot', 'ai', 'gpt', 'llm', 'artificial intelligence', 'machine learning', 'neural network', 'deep learning', 'tensorflow', 'pytorch', 'scikit learn', 'pandas', 'numpy', 'jupyter', 'colab', 'kaggle', 'data science', 'computer science', 'algorithms', 'leetcode', 'hackerrank', 'codeforces', 'atcoder', 'project euler', 'advent of code', 'codingame', 'edabit', 'exercism', 'codewars', 'codecademy', 'freecodecamp', 'the odin project', 'cs50', 'mit ocw', 'stanford cs', 'berkeley cs', 'harvard cs', 'princeton cs', 'yale cs', 'caltech cs', 'cmu cs', 'cornell cs', 'ucla cs', 'ucb cs', 'ucsd cs', 'uci cs', 'ucsc cs', 'ucd cs', 'uci cs', 'ucr cs', 'ucm cs', 'ucsb cs', 'ucsc cs']):
        categories.append('Educational')
    if any(kw in name for kw in ['simulation', 'simulator', 'tycoon', 'management', 'farm', 'farming', 'harvest moon', 'stardew valley', 'animal crossing', 'sims', 'simcity', 'cities skylines', 'planet zoo', 'planet coaster', 'rollercoaster tycoon', 'rct', 'two point hospital', 'prison architect', 'rimworld', 'dwarf fortress', 'oxygen not included', 'space engineers', 'kerbal space program', 'ksp', 'simpleplanes', 'simple rockets', 'flight simulator', 'truck simulator', 'bus simulator', 'train simulator', 'euro truck', 'american truck', 'farming simulator', 'construction simulator', 'car mechanic', 'pc building', 'house flipper', 'power wash', 'lawn mowing', 'garbage truck', 'police simulator', 'ambulance', 'firefighter', 'surgeon', 'cooking simulator', 'cooking mama', 'overcooked', 'papa', 'bakeria', 'burgeria', 'cheeseria', 'cupcakeria', 'donuteria', 'freezeria', 'hot doggeria', 'pancakeria', 'pastaria', 'pizzeria', 'scooperia', 'sushiria', 'taco mia', 'wingeria', 'bitlife', 'life simulator', 'life sim', 'aviamasters', 'aviation', 'pilot', 'airline', 'airport', 'flight', 'flying', 'drone', 'space flight', 'orbiter', 'x-plane', 'microsoft flight', 'dcs world', 'war thunder', 'il-2', 'rise of flight', 'bird', 'wings']):
        categories.append('Simulation')
    
    if not categories:
        categories.append('Other')
    
    return categories

def main():
    g_json_games = load_g_json()
    print(f"Loaded {len(g_json_games)} games from g.json")
    
    folder_games = scan_games_folder()
    print(f"Found {len(folder_games)} games in games/ folder")
    
    zones_data = load_zones_json()
    print(f"Loaded {len(zones_data)} zones from zones.json")
    
    html_main_games = scan_html_main_folder(zones_data)
    print(f"Found {len(html_main_games)} games in html-main/ folder")
    
    all_games = deduplicate_games(g_json_games, folder_games + html_main_games)
    print(f"After deduplication: {len(all_games)} unique games")
    
    for game in all_games:
        game['categories'] = categorize_game(game)
        if 'thumbnail' not in game or not game['thumbnail']:
            game['thumbnail'] = '/png/logo.png'
        if 'frameType' not in game:
            game['frameType'] = 'iframe'
    
    all_games.sort(key=lambda x: x['name'].lower())
    
    output = {
        'games': all_games,
        'total': len(all_games),
        'categories': sorted(list(set(cat for game in all_games for cat in game['categories'])))
    }
    
    with open('truffled-main/public/js/json/unified_games.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved unified games to unified_games.json")
    print(f"Categories: {output['categories']}")

if __name__ == '__main__':
    main()