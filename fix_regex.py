import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_regex = r\"\"\"URL_PATTERN = re.compile(
    r'(https?://(?:www\.)?(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be|x\.com|twitter\.com|facebook\.com|pin\.it|pinterest\.com)[^\s]+)'
)\"\"\"

new_regex = r\"\"\"URL_PATTERN = re.compile(
    r'(https?://(?:www\.)?(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be|x\.com|twitter\.com|facebook\.com|pin\.it|pinterest\.com)[a-zA-Z0-9_\-\./\?=&%]+)'
)\"\"\"

content = content.replace(old_regex, new_regex)

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)
