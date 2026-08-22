import re

with open('locales.py', 'r', encoding='utf-8') as f:
    content = f.read()

uz_new = "'caption': \"📥 @VidSaveUzBot orqali yuklab olindi\",\n        'music_detected': \"🎵 Aniqlangan musiqa: {track_info}\","
ru_new = "'caption': \"📥 Скачано через @VidSaveUzBot\",\n        'music_detected': \"🎵 Распознанная музыка: {track_info}\","
en_new = "'caption': \"📥 Downloaded via @VidSaveUzBot\",\n        'music_detected': \"🎵 Detected Music: {track_info}\","

content = content.replace("'caption': \"📥 @VidSaveUzBot orqali yuklab olindi\",", uz_new)
content = content.replace("'caption': \"📥 Скачано через @VidSaveUzBot\",", ru_new)
content = content.replace("'caption': \"📥 Downloaded via @VidSaveUzBot\",", en_new)

with open('locales.py', 'w', encoding='utf-8') as f:
    f.write(content)
