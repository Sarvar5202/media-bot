with open('handlers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove lines from index 435 to the end
with open('handlers.py', 'w', encoding='utf-8') as f:
    f.writelines(lines[:435])
