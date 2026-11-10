#!/usr/bin/env python3
"""
Check which html-main files have local content (no external base href)
"""
import re
from pathlib import Path

HTML_MAIN_DIR = Path("html-main")
html_files = list(HTML_MAIN_DIR.glob("*.html"))
print(f"Total HTML files in html-main: {len(html_files)}")

local_files = []
external_files = []

for html_file in html_files:
    try:
        with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        base_match = re.search(r'base href="([^"]+)"', content)
        if base_match:
            url = base_match.group(1)
            if url.startswith("http://") or url.startswith("https://"):
                external_files.append((html_file.name, url))
            else:
                local_files.append(html_file.name)
        else:
            local_files.append(html_file.name)
    except:
        local_files.append(html_file.name)

print(f"Files WITHOUT external base href (local): {len(local_files)}")
print(f"Files WITH external base href: {len(external_files)}")
print()
print("Local files (first 50):")
for f in local_files[:50]:
    print(f"  {f}")