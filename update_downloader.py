import re

with open('downloader.py', 'r', encoding='utf-8') as f:
    content = f.read()

def get_track_info(info_dict):
    artist = info_dict.get('artist') or info_dict.get('creator') or ''
    track = info_dict.get('track') or info_dict.get('alt_title') or ''
    if artist and track:
        return f"{artist} - {track}"
    elif track:
        return track
    elif artist:
        return artist
    return None

old_append_1 = '''                                results.append({
                                    'filepath': filepath,
                                    'title': entry.get('title', 'Media')[:100],
                                    'ext': 'mp3' if is_audio else entry.get('ext', 'mp4')
                                })'''

new_append_1 = '''                                track_info = entry.get('artist') and entry.get('track') and f"{entry.get('artist')} - {entry.get('track')}" or entry.get('track') or entry.get('artist')
                                results.append({
                                    'filepath': filepath,
                                    'title': entry.get('title', 'Media')[:100],
                                    'ext': 'mp3' if is_audio else entry.get('ext', 'mp4'),
                                    'track_info': track_info
                                })'''

old_append_2 = '''                            results.append({
                                'filepath': filepath,
                                'title': info.get('title', 'Media')[:100],
                                'ext': 'mp3' if is_audio else info.get('ext', 'mp4')
                            })'''

new_append_2 = '''                            track_info = info.get('artist') and info.get('track') and f"{info.get('artist')} - {info.get('track')}" or info.get('track') or info.get('artist')
                            results.append({
                                'filepath': filepath,
                                'title': info.get('title', 'Media')[:100],
                                'ext': 'mp3' if is_audio else info.get('ext', 'mp4'),
                                'track_info': track_info
                            })'''

content = content.replace(old_append_1, new_append_1)
content = content.replace(old_append_2, new_append_2)

with open('downloader.py', 'w', encoding='utf-8') as f:
    f.write(content)
