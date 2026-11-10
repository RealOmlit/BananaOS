#!/usr/bin/env python3
"""Remove root-level HTML files with CDN dependencies that won't work offline"""
import re
from pathlib import Path

GAMES_DIR = Path("C:/Users/Om 2/Downloads/UBG-Ultra-main/UBG-Ultra-main/games")
GAMES_JSON = GAMES_DIR / "assets" / "js" / "games.json"

def has_cdn_deps(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return False, None
    
    external_refs = re.findall(r'(?:src|href)=["\'](https?://[^"\']+)["\']', content)
    cdn_refs = [r for r in external_refs if any(cdn in r for cdn in ['jsdelivr.net', 'cdn.jsdelivr.net', 'rawcdn.githack.com', 'unpkg.com', 'cdnjs.cloudflare.com'])]
    
    # Also check for external base href
    base_match = re.search(r'base href="([^"]+)"', content)
    if base_match:
        url = base_match.group(1)
        if url.startswith('http://') or url.startswith('https://'):
            cdn_refs.append(url)
    
    return len(cdn_refs) > 0, cdn_refs

def main():
    # Load games.json
    with open(GAMES_JSON, 'r') as f:
        games = json.load(f)
    
    print(f"Games in catalog: {len(games)}")
    
    html_files = list(GAMES_DIR.glob("*.html"))
    print(f"Root HTML files: {len(html_files)}")
    
    cdn_files = []
    for f in html_files:
        has_cdn, refs = has_cdn_deps(f)
        if has_cdn:
            cdn_files.append((f.name, refs))
    
    print(f"Files with CDN deps: {len(cdn_files)}")
    for name, refs in cdn_files:
        print(f"  {name}: {len(refs)} CDN refs")
    
    # Remove from games.json
    cdn_filenames = {f[0] for f in cdn_files}
    filtered_games = [g for g in games if g['link'] not in cdn_filenames]
    
    print(f"\nRemoving {len(games) - len(filtered_games)} games from catalog")
    
    # Write filtered games.json
    with open(GAMES_JSON, 'w') as f:
        json.dump(filtered_games, f, indent=2)
    
    # Optionally delete the HTML files
    for name, _ in cdn_files:
        (GAMES_DIR / name).unlink()
        print(f"Deleted: {name}")
    
    print(f"\nDone. Remaining games: {len(filtered_games)}")

if __name__ == "__main__":
    import json
    main()