#!/usr/bin/env python3
"""Check all subfolder games for external dependencies"""
import os
import re
from pathlib import Path

GAMES_DIR = Path("C:/Users/Om 2/Downloads/UBG-Ultra-main/UBG-Ultra-main/games")

def check_folder(folder):
    index_path = GAMES_DIR / folder / "index.html"
    if not index_path.exists():
        return "NO index.html"
    
    try:
        with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return "READ ERROR"
    
    issues = []
    
    # Check base href
    base_match = re.search(r'base href="([^"]+)"', content)
    if base_match:
        url = base_match.group(1)
        if url.startswith('http://') or url.startswith('https://'):
            issues.append(f"EXTERNAL base href: {url}")
    
    # Check script/src references to external CDNs
    external_refs = re.findall(r'(?:src|href)=["\'](https?://[^"\']+)["\']', content)
    cdn_refs = [r for r in external_refs if any(cdn in r for cdn in ['jsdelivr.net', 'cdn.jsdelivr.net', 'rawcdn.githack.com', 'unpkg.com', 'cdnjs.cloudflare.com'])]
    if cdn_refs:
        issues.append(f"CDN references: {len(cdn_refs)} found")
    
    # Check for module imports from external
    module_refs = re.findall(r'import\s+["\'](https?://[^"\']+)["\']', content)
    if module_refs:
        issues.append(f"External ES modules: {len(module_refs)} found")
    
    if issues:
        return " | ".join(issues)
    return "LOCAL"

def main():
    folders = [d for d in GAMES_DIR.iterdir() if d.is_dir() and d.name not in ['assets', '__pycache__']]
    print(f"Checking {len(folders)} game subfolders...\n")
    
    local_count = 0
    external_count = 0
    
    for folder in sorted(folders):
        result = check_folder(folder.name)
        if result == "LOCAL":
            print(f"[OK] {folder.name}: LOCAL")
            local_count += 1
        else:
            print(f"[EXTERNAL] {folder.name}: {result}")
            external_count += 1
    
    print(f"\nSummary: {local_count} local, {external_count} with external deps")

if __name__ == "__main__":
    main()