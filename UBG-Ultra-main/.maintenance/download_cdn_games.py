#!/usr/bin/env python3
"""
Download games from CDN URLs in html-main to make them work offline
"""
import re
import os
import json
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse

HTML_MAIN_DIR = Path("html-main")
GAMES_DIR = Path("games")
GAMES_JSON = GAMES_DIR / "assets" / "js" / "games.json"

def extract_game_info(filepath):
    """Extract game info from HTML file"""
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
    
    # Find all asset URLs
    asset_urls = set()
    
    # Scripts
    for match in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE):
        url = match.group(1)
        if url.startswith('http'):
            asset_urls.add(url)
        elif url.startswith('/') or not url.startswith('data:'):
            asset_urls.add(urljoin(base_url, url))
    
    # Stylesheets
    for match in re.finditer(r'<link[^>]+href=["\']([^"\']+)["\']', content, re.IGNORECASE):
        url = match.group(1)
        if url.startswith('http'):
            asset_urls.add(url)
        elif url.startswith('/') or not url.startswith('data:'):
            asset_urls.add(urljoin(base_url, url))
    
    # Images
    for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE):
        url = match.group(1)
        if url.startswith('http'):
            asset_urls.add(url)
        elif url.startswith('/'):
            asset_urls.add(urljoin(base_url, url))
    
    # Module imports
    for match in re.finditer(r'import\s+["\']([^"\']+)["\']', content):
        url = match.group(1)
        if url.startswith('http'):
            asset_urls.add(url)
        elif url.startswith('/'):
            asset_urls.add(urljoin(base_url, url))
    
    # Unity build URL
    unity_match = re.search(r'buildUrl\s*=\s*["\']([^"\']+)["\']', content)
    if unity_match:
        asset_urls.add(unity_match.group(1))
    
    # Service worker
    sw_match = re.search(r'navigator\.serviceWorker\.register\(["\']([^"\']+)["\']', content)
    if sw_match:
        asset_urls.add(sw_match.group(1))
    
    return {
        'title': title,
        'base_url': base_url,
        'assets': list(asset_urls),
        'html_content': content,
        'filename': filepath.name
    }

def download_game(game_info, max_assets=50):
    """Download a game and its assets"""
    # Create a safe folder name
    safe_title = re.sub(r'[^\w\s-]', '', game_info['title']).strip()
    safe_title = re.sub(r'[-\s]+', '-', safe_title)
    safe_title = safe_title.encode('ascii', 'ignore').decode()  # Remove non-ASCII
    folder = GAMES_DIR / safe_title
    
    if folder.exists():
        print(f"  Folder exists: {safe_title}")
        return False
    
    folder.mkdir(parents=True)
    
    # Download HTML and rewrite
    html = game_info['html_content']
    base_url = game_info['base_url']
    
    # Track URL mappings
    url_map = {}
    
    def download_asset(url, max_assets=max_assets):
        if len(url_map) >= max_assets:
            return url
        if url in url_map:
            return url_map[url]
        if url.startswith('data:'):
            return url
        
        try:
            parsed = urlparse(url)
            # Determine local path
            rel_path = parsed.path.lstrip('/')
            if not rel_path or rel_path.endswith('/'):
                rel_path += 'index.html'
            
            local_path = folder / rel_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(resp.content)
                # Map to relative path from HTML
                rel_from_html = os.path.relpath(local_path, folder)
                url_map[url] = rel_from_html
                print(f"    Downloaded: {rel_from_html} ({len(resp.content)} bytes)")
            else:
                print(f"    Failed: {url} ({resp.status_code})")
        except Exception as e:
            print(f"    Error downloading {url}: {e}")
        return url
    
    # Download assets
    for url in game_info['assets'][:max_assets]:
        download_asset(url)
    
    # Rewrite HTML
    for orig_url, local_path in url_map.items():
        html = html.replace(orig_url, local_path)
    
    # Remove base href
    html = re.sub(r'<base href="[^"]+">', '', html)
    
    # Save HTML
    index_path = folder / 'index.html'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"  Saved to: {folder}")
    return True

def main():
    print("Scanning html-main for downloadable games...")
    
    html_files = list(HTML_MAIN_DIR.glob("*.html"))
    print(f"Found {len(html_files)} HTML files")
    
    downloadable = []
    for f in html_files:
        info = extract_game_info(f)
        if info and info['assets']:
            downloadable.append(info)
            title_safe = info['title'].encode('ascii', 'ignore').decode()
            print(f"  {title_safe} ({f.name}) - {len(info['assets'])} assets from {info['base_url'][:60]}")
    
    print(f"\nTotal downloadable: {len(downloadable)}")
    
    # Download first 5 as test
    for i, game in enumerate(downloadable[:5]):
        title_safe = game['title'].encode('ascii', 'ignore').decode()
        print(f"\n[{i+1}] {title_safe} - {len(game['assets'])} assets")
        try:
            download_game(game, max_assets=30)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    main()