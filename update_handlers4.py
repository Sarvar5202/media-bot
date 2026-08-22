import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

single_old = '''            if len(results) == 1:
                res = results[0]
                filepath = res['filepath']'''

single_new = '''            if len(results) == 1:
                res = results[0]
                
                track_info = res.get('track_info')
                if track_info:
                    music_detected_fmt = await get_text(callback.from_user.id, "music_detected")
                    caption_text = f"{caption_text}\\n\\n{music_detected_fmt.format(track_info=track_info)}"
                    
                filepath = res['filepath']'''
content = content.replace(single_old, single_new)


multi_old = '''                    if res['ext'] in ['jpg', 'jpeg', 'png', 'webp']:
                        media_group.append(InputMediaPhoto(media=media, caption=caption_text if i == 0 else None))
                    else:
                        media_group.append(InputMediaVideo(media=media, caption=caption_text if i == 0 else None))'''

multi_new = '''                    item_caption = caption_text
                    if i == 0 and res.get('track_info'):
                        music_detected_fmt = await get_text(callback.from_user.id, "music_detected")
                        item_caption = f"{caption_text}\\n\\n{music_detected_fmt.format(track_info=res.get('track_info'))}"
                    
                    if res['ext'] in ['jpg', 'jpeg', 'png', 'webp']:
                        media_group.append(InputMediaPhoto(media=media, caption=item_caption if i == 0 else None))
                    else:
                        media_group.append(InputMediaVideo(media=media, caption=item_caption if i == 0 else None))'''
content = content.replace(multi_old, multi_new)

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)
