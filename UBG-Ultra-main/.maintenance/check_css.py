with open(r'C:\Users\Om 2\Downloads\UBG-Ultra-main\UBG-Ultra-main\games\assets\css\style.css', 'r', encoding='utf-8') as f:
    content = f.read()
# Find switch label styles - look for the switch label structure
idx = content.find('.switch')
if idx >= 0:
    # Get a larger context
    print("=== SWITCH STYLES ===")
    print(content[idx:idx+800])
    print()

# Find field styles
idx2 = content.find('.field {')
if idx2 >= 0:
    print("=== FIELD STYLES ===")
    print(content[idx2:idx2+800])