with open(r'C:\Users\Om 2\Downloads\UBG-Ultra-main\UBG-Ultra-main\games\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the section to replace
start_marker = '<h3>Tab Cloak</h3>'
end_marker = '                </div>\n            </section>'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx >= 0 and end_idx >= 0:
    print("Found!")
    print("Start:", start_idx)
    print("End:", end_idx)
    # Show the content
    print(content[start_idx:end_idx + len(end_marker)])
else:
    print("Not found")
    print("Start marker found:", start_idx >= 0)
    print("End marker found:", content.find(end_marker) >= 0)