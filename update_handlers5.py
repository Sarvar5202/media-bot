import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Read cache block
cache_read_old = '''    if cached_data:
        try:
            if cached_data['type'] == 'photo':'''

cache_read_new = '''    if cached_data:
        try:
            track_info = cached_data.get('track_info')
            if track_info:
                music_detected_fmt = await get_text(callback.from_user.id, "music_detected")
                caption_text = f"{caption_text}\\n\\n{music_detected_fmt.format(track_info=track_info)}"
                
            if cached_data['type'] == 'photo':'''

content = content.replace(cache_read_old, cache_read_new)

# Write cache block for single media
cache_write_old_audio = "await MEDIA_CACHE.set(cache_key, {'type': 'audio', 'id': sent_msg.audio.file_id})"
cache_write_new_audio = "await MEDIA_CACHE.set(cache_key, {'type': 'audio', 'id': sent_msg.audio.file_id, 'track_info': res.get('track_info')})"

cache_write_old_photo = "await MEDIA_CACHE.set(cache_key, {'type': 'photo', 'id': sent_msg.photo[-1].file_id})"
cache_write_new_photo = "await MEDIA_CACHE.set(cache_key, {'type': 'photo', 'id': sent_msg.photo[-1].file_id, 'track_info': res.get('track_info')})"

cache_write_old_video = "await MEDIA_CACHE.set(cache_key, {'type': 'video', 'id': sent_msg.video.file_id})"
cache_write_new_video = "await MEDIA_CACHE.set(cache_key, {'type': 'video', 'id': sent_msg.video.file_id, 'track_info': res.get('track_info')})"

content = content.replace(cache_write_old_audio, cache_write_new_audio)
content = content.replace(cache_write_old_photo, cache_write_new_photo)
content = content.replace(cache_write_old_video, cache_write_new_video)

# Write cache block for group media
cache_write_old_group = "await MEDIA_CACHE.set(cache_key, {'type': 'group', 'items': cached_items})"
cache_write_new_group = "await MEDIA_CACHE.set(cache_key, {'type': 'group', 'items': cached_items, 'track_info': results[0].get('track_info') if results else None})"
content = content.replace(cache_write_old_group, cache_write_new_group)

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)
