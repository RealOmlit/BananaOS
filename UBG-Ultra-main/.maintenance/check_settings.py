with open(r'C:\Users\Om 2\Downloads\UBG-Ultra-main\UBG-Ultra-main\games\index.html', 'r', encoding='utf-8') as f:
    content = f.read()
idx = content.find('id="page-settings"')
if idx >= 0:
    end = content.find('</section>', idx)
    print(content[idx:end+10])