import re

with open('downloader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update extractor args for YouTube
yt_old = "'youtube': ['player_client=android,web', 'player_skip=webpage'],"
yt_new = "'youtube': ['player_client=android,mweb,web', 'player_skip=webpage'],"
content = content.replace(yt_old, yt_new)

yt_retry_old = "'youtube': ['player_client=ios,tv', 'player_skip=webpage']"
yt_retry_new = "'youtube': ['player_client=ios,tv,web', 'player_skip=webpage']"
content = content.replace(yt_retry_old, yt_retry_new)

# Update outtmpl for audio
audio_outtmpl_old = "opts['outtmpl'] = os.path.join(temp_dir, f'{dl_uuid}_%(extractor)s_%(id)s_%(playlist_index|)s.%(ext)s')"
audio_outtmpl_new = "opts['outtmpl'] = os.path.join(temp_dir, 'VidSaveUzBot.%(ext)s')"

# We need to replace the first occurrence of audio_outtmpl_old since it appears twice (if is_audio / else)
parts = content.split(audio_outtmpl_old, 2)
if len(parts) == 3:
    content = parts[0] + audio_outtmpl_new + parts[1] + audio_outtmpl_old + parts[2]

with open('downloader.py', 'w', encoding='utf-8') as f:
    f.write(content)
