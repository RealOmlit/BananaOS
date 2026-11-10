#!/usr/bin/env python3
"""Check root-level HTML files in games/ for external dependencies"""
import re
from pathlib import Path

GAMES_DIR = Path("C:/Users/Om 2/Downloads/UBG-Ultra-main/UBG-Ultra-main/games")

def check_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return "READ ERROR"
    
    issues = []
    
    # Check base href
    base_match = re.search(r'base href="([^"]+)"', content)
    if base_match:
        url = base_match.group(1)
        if url.startswith('http://') or url.startswith('https://'):
            issues.append(f"EXTERNAL base href: {url[:80]}")
    
    # Check script/src references to external CDNs
    external_refs = re.findall(r'(?:src|href)=["\'](https?://[^"\']+)["\']', content)
    cdn_refs = [r for r in external_refs if any(cdn in r for cdn in ['jsdelivr.net', 'cdn.jsdelivr.net', 'rawcdn.githack.com', 'unpkg.com', 'cdnjs.cloudflare.com'])]
    if cdn_refs:
        issues.append(f"CDN refs: {len(cdn_refs)}")
    
    if issues:
        return " | ".join(issues)
    return "LOCAL"

def main():
    html_files = list(GAMES_DIR.glob("*.html"))
    print(f"Checking {len(html_files)} root-level HTML files...\n")
    
    local = 0
    external = 0
    
    for f in sorted(html_files):
        result = check_file(f)
        if result == "LOCAL":
            local += 1
        else:
            print(f"[EXTERNAL] {f.name}: {result}")
            external += 1
    
    print(f"\nSummary: {local} local, {external} with external deps")

if __name__ == "__main__":
    main()