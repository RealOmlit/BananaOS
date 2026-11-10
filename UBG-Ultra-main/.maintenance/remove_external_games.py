#!/usr/bin/env python3
"""
Remove HTML files with external base hrefs from games folder
"""
import os
import re
from pathlib import Path

GAMES_DIR = Path("C:/Users/Om 2/Downloads/UBG-Ultra-main/UBG-Ultra-main/games")

def has_external_base_href(filepath):
    """Check if HTML file has external base href"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        base_match = re.search(r'base href="([^"]+)"', content)
        if base_match:
            url = base_match.group(1)
            if url.startswith('http://') or url.startswith('https://'):
                return True, url
    except:
        pass
    return False, None

def main():
    html_files = list(GAMES_DIR.glob("*.html"))
    print(f"Scanning {len(html_files)} HTML files...")
    
    removed = 0
    kept = 0
    
    for html_file in html_files:
        has_external, url = has_external_base_href(html_file)
        if has_external:
            print(f"  REMOVING: {html_file.name} -> {url}")
            try:
                html_file.unlink()
                removed += 1
            except Exception as e:
                print(f"    ERROR: {e}")
        else:
            kept += 1
    
    print(f"\nRemoved: {removed}")
    print(f"Kept: {kept}")

if __name__ == "__main__":
    main()