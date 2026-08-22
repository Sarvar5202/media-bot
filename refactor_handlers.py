import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will parse the file carefully. It's better to just do string replacements.

import_str = "from downloader import download_media"
new_import = "from downloader import download_media, get_media_info\nimport asyncio"
content = content.replace(import_str, new_import)

# First, extract process_dl
process_dl_match = re.search(r'@router\.callback_query\(F\.data\.startswith\("dl_"\)\)\nasync def process_dl\(callback: CallbackQuery\):.*?try:\n            await status_msg\.delete\(\)\n        except Exception:\n            pass', content, re.DOTALL)

if process_dl_match:
    old_process_dl = process_dl_match.group(0)
    
    # We create the helper function
    helper_code = '''async def execute_download_and_send(url: str, url_hash: str, is_audio: bool, user_id: int, bot, chat_id: int, reply_to_message_id: int, status_msg_to_delete=None):
    platform = 'Boshqa'
    url_lower = url.lower()
    if 'instagram.com' in url_lower: platform = 'Instagram'
    elif 'tiktok.com' in url_lower: platform = 'TikTok'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower: platform = 'YouTube'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower: platform = 'X/Twitter'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower: platform = 'Facebook'
    elif 'pinterest.com' in url_lower or 'pin.it' in url_lower: platform = 'Pinterest'
    
    await increment_platform_stat(platform)
    
    caption_text = await get_text(user_id, 'caption')
    
    cache_key = f"{url_hash}_{'aud' if is_audio else 'vid'}"
    cached_data = await MEDIA_CACHE.get(cache_key)
    if cached_data:
        try:
            track_info = cached_data.get('track_info')
            if track_info:
                music_detected_fmt = await get_text(user_id, "music_detected")
                caption_text = f"{caption_text}\\n\\n{music_detected_fmt.format(track_info=track_info)}"
                
            if cached_data['type'] == 'photo':
                await bot.send_photo(chat_id=chat_id, photo=cached_data['id'], caption=caption_text, reply_to_message_id=reply_to_message_id)
            elif cached_data['type'] == 'video':
                await bot.send_video(chat_id=chat_id, video=cached_data['id'], caption=caption_text, reply_to_message_id=reply_to_message_id)
            elif cached_data['type'] == 'audio':
                await bot.send_audio(chat_id=chat_id, audio=cached_data['id'], caption=caption_text, reply_to_message_id=reply_to_message_id)
            elif cached_data['type'] == 'group':
                media_group = []
                for i, item in enumerate(cached_data['items']):
                    if item['type'] == 'photo':
                        media_group.append(InputMediaPhoto(media=item['id'], caption=caption_text if i == 0 else None))
                    else:
                        media_group.append(InputMediaVideo(media=item['id'], caption=caption_text if i == 0 else None))
                await bot.send_media_group(chat_id=chat_id, media=media_group, reply_to_message_id=reply_to_message_id)
            if status_msg_to_delete:
                try: await status_msg_to_delete.delete()
                except Exception: pass
            return True
        except Exception:
            pass

    status_msg = await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "wait"), reply_to_message_id=reply_to_message_id)
    if status_msg_to_delete:
        try: await status_msg_to_delete.delete()
        except Exception: pass

    results = []
    
    try:
        temp_dir_ctx = temporary_media_directory()
        temp_dir = await temp_dir_ctx.__aenter__()
        async with ChatActionSender.upload_video(bot=bot, chat_id=chat_id):
            results = await download_media(url, is_audio=is_audio, temp_dir=temp_dir)
            
            if not results:
                await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "too_large"), reply_to_message_id=reply_to_message_id)
                return False
            
            if len(results) == 1:
                res = results[0]
                
                track_info = res.get('track_info')
                if track_info:
                    music_detected_fmt = await get_text(user_id, "music_detected")
                    caption_text = f"{caption_text}\\n\\n{music_detected_fmt.format(track_info=track_info)}"
                    
                filepath = res['filepath']
                is_photo = res['ext'] in ['jpg', 'jpeg', 'png', 'webp']
                file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                
                if file_size > 0 and file_size < 10 * 1024 * 1024:
                    with open(filepath, 'rb') as f:
                        file_bytes = f.read()
                    media = BufferedInputFile(file_bytes, filename=os.path.basename(filepath))
                    os.remove(filepath)
                else:
                    media = FSInputFile(filepath)
                
                if is_audio:
                    sent_msg = await bot.send_audio(chat_id=chat_id, audio=media, caption=caption_text, reply_to_message_id=reply_to_message_id)
                    if sent_msg.audio:
                        await MEDIA_CACHE.set(cache_key, {'type': 'audio', 'id': sent_msg.audio.file_id, 'track_info': res.get('track_info')})
                elif is_photo:
                    sent_msg = await bot.send_photo(chat_id=chat_id, photo=media, caption=caption_text, reply_to_message_id=reply_to_message_id)
                    if sent_msg.photo:
                        await MEDIA_CACHE.set(cache_key, {'type': 'photo', 'id': sent_msg.photo[-1].file_id, 'track_info': res.get('track_info')})
                else:
                    sent_msg = await bot.send_video(chat_id=chat_id, video=media, caption=caption_text, reply_to_message_id=reply_to_message_id)
                    if sent_msg.video:
                        await MEDIA_CACHE.set(cache_key, {'type': 'video', 'id': sent_msg.video.file_id, 'track_info': res.get('track_info')})
            else:
                media_group = []
                for i, res in enumerate(results[:10]):
                    filepath = res['filepath']
                    file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                    
                    item_caption = caption_text
                    if i == 0 and res.get('track_info'):
                        music_detected_fmt = await get_text(user_id, "music_detected")
                        item_caption = f"{caption_text}\\n\\n{music_detected_fmt.format(track_info=res.get('track_info'))}"
                    
                    if file_size > 0 and file_size < 10 * 1024 * 1024:
                        with open(filepath, 'rb') as f:
                            file_bytes = f.read()
                        media = BufferedInputFile(file_bytes, filename=os.path.basename(filepath))
                        os.remove(filepath)
                    else:
                        media = FSInputFile(filepath)
                        
                    if res['ext'] in ['jpg', 'jpeg', 'png', 'webp']:
                        media_group.append(InputMediaPhoto(media=media, caption=item_caption if i == 0 else None))
                    else:
                        media_group.append(InputMediaVideo(media=media, caption=item_caption if i == 0 else None))
                
                sent_msgs = await bot.send_media_group(chat_id=chat_id, media=media_group, reply_to_message_id=reply_to_message_id)
                if sent_msgs:
                    cached_items = []
                    for msg in sent_msgs:
                        if msg.photo:
                            cached_items.append({'type': 'photo', 'id': msg.photo[-1].file_id})
                        elif msg.video:
                            cached_items.append({'type': 'video', 'id': msg.video.file_id})
                    if cached_items:
                        await MEDIA_CACHE.set(cache_key, {'type': 'group', 'items': cached_items, 'track_info': results[0].get('track_info') if results else None})
        return True
    except ValueError as ve:
        err_key = str(ve)
        if err_key in ["private_video", "timeout", "login_required"]:
            await bot.send_message(chat_id=chat_id, text=await get_text(user_id, err_key), reply_to_message_id=reply_to_message_id)
        else:
            await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "error"), reply_to_message_id=reply_to_message_id)
        return False
    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "error"), reply_to_message_id=reply_to_message_id)
        return False
    finally:
        for res in results:
            if res and 'filepath' in res and os.path.exists(res['filepath']):
                try:
                    os.remove(res['filepath'])
                except Exception:
                    pass
        try:
            await temp_dir_ctx.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            await status_msg.delete()
        except Exception:
            pass

@router.callback_query(F.data.startswith("dl_"))
async def process_dl(callback: CallbackQuery):
    action, url_hash = callback.data.split("|")
    is_audio = (action == "dl_aud")
    
    url = await URL_CACHE.get(url_hash)
    if not url:
        await callback.message.edit_text("❌ Havola muddati tugagan. Iltimos, qaytadan yuboring.")
        await callback.answer()
        return
        
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await execute_download_and_send(url, url_hash, is_audio, callback.from_user.id, callback.bot, callback.message.chat.id, callback.message.message_id, status_msg_to_delete=callback.message)
    await callback.answer()
'''

    content = content.replace(old_process_dl, helper_code)
    
    # Now replace handle_media_url
    old_handle = '''@router.message(F.text.regexp(URL_PATTERN).as_("url_match"))
async def handle_media_url(message: Message, url_match: re.Match):
    url = url_match.group(1)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    
    await URL_CACHE.set(url_hash, url)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Videoni yuklab olish", callback_data=f"dl_vid|{url_hash}")],
        [InlineKeyboardButton(text="🎵 MP3 (Ovozni kuchaytirish)", callback_data=f"dl_aud|{url_hash}")]
    ])
    
    await message.reply("Qaysi formatda yuklab olamiz? / Выберите формат: / Choose format:", reply_markup=markup)'''

    new_handle = '''@router.message(F.text.regexp(URL_PATTERN).as_("url_match"))
async def handle_media_url(message: Message, url_match: re.Match):
    url = url_match.group(1)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    await URL_CACHE.set(url_hash, url)
    
    wait_msg = await message.reply(await get_text(message.from_user.id, "wait"))
    
    info = await get_media_info(url)
    duration = info.get('duration', None)
    
    if duration is not None and duration <= 300:
        # Fast-track path: download both video and audio concurrently
        # Since running both might be heavy, we can do them sequentially or concurrently.
        # Let's do sequentially to avoid hitting limits or TempDir clashes too fast, actually yt-dlp isolates downloads safely.
        await wait_msg.delete()
        task1 = execute_download_and_send(url, url_hash, False, message.from_user.id, message.bot, message.chat.id, message.message_id)
        task2 = execute_download_and_send(url, url_hash, True, message.from_user.id, message.bot, message.chat.id, message.message_id)
        await asyncio.gather(task1, task2)
    else:
        # Interactive path
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Videoni yuklab olish", callback_data=f"dl_vid|{url_hash}")],
            [InlineKeyboardButton(text="🎵 MP3 (Ovozni kuchaytirish)", callback_data=f"dl_aud|{url_hash}")]
        ])
        await wait_msg.delete()
        await message.reply("Qaysi formatda yuklab olamiz? / Выберите формат: / Choose format:", reply_markup=markup)'''

    content = content.replace(old_handle, new_handle)

    with open('handlers.py', 'w', encoding='utf-8') as f:
        f.write(content)

