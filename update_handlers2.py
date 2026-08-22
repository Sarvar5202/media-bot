import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add URL_CACHE
cache_inst_old = 'MEDIA_CACHE = SmartCache(ttl=3600, max_items=1000)'
cache_inst_new = '''MEDIA_CACHE = SmartCache(ttl=3600, max_items=1000)
URL_CACHE = SmartCache(ttl=3600, max_items=1000)'''
content = content.replace(cache_inst_old, cache_inst_new)

# Update cache_cleanup_task
cleanup_old = '''async def cache_cleanup_task():
    while True:
        await asyncio.sleep(600)
        try:
            await MEDIA_CACHE.cleanup()
        except Exception:
            pass'''
cleanup_new = '''async def cache_cleanup_task():
    while True:
        await asyncio.sleep(600)
        try:
            await MEDIA_CACHE.cleanup()
            await URL_CACHE.cleanup()
        except Exception:
            pass'''
content = content.replace(cleanup_old, cleanup_new)

# Find the entire handle_media_url block and replace it
url_match_pattern = re.compile(r'@router\.message\(F\.text\.regexp\(URL_PATTERN\)\.as_\(\"url_match\"\)\).*?finally:\s+for res in results:.*?pass', re.DOTALL)

new_handler = '''@router.message(F.text.regexp(URL_PATTERN).as_("url_match"))
async def handle_media_url(message: Message, url_match: re.Match):
    url = url_match.group(1)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    
    await URL_CACHE.set(url_hash, url)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Videoni yuklab olish", callback_data=f"dl_vid|{url_hash}")],
        [InlineKeyboardButton(text="🎵 MP3 (Ovozni kuchaytirish)", callback_data=f"dl_aud|{url_hash}")]
    ])
    
    await message.reply("Qaysi formatda yuklab olamiz? / Выберите формат: / Choose format:", reply_markup=markup)

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
    
    platform = 'Boshqa'
    url_lower = url.lower()
    if 'instagram.com' in url_lower: platform = 'Instagram'
    elif 'tiktok.com' in url_lower: platform = 'TikTok'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower: platform = 'YouTube'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower: platform = 'X/Twitter'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower: platform = 'Facebook'
    elif 'pinterest.com' in url_lower or 'pin.it' in url_lower: platform = 'Pinterest'
    
    await increment_platform_stat(platform)
    
    caption_text = await get_text(callback.from_user.id, 'caption')
    
    cache_key = f"{url_hash}_{'aud' if is_audio else 'vid'}"
    cached_data = await MEDIA_CACHE.get(cache_key)
    if cached_data:
        try:
            if cached_data['type'] == 'photo':
                await callback.message.reply_photo(photo=cached_data['id'], caption=caption_text)
            elif cached_data['type'] == 'video':
                await callback.message.reply_video(video=cached_data['id'], caption=caption_text)
            elif cached_data['type'] == 'audio':
                await callback.message.reply_audio(audio=cached_data['id'], caption=caption_text)
            elif cached_data['type'] == 'group':
                media_group = []
                for i, item in enumerate(cached_data['items']):
                    if item['type'] == 'photo':
                        media_group.append(InputMediaPhoto(media=item['id'], caption=caption_text if i == 0 else None))
                    else:
                        media_group.append(InputMediaVideo(media=item['id'], caption=caption_text if i == 0 else None))
                await callback.message.answer_media_group(media=media_group, reply_to_message_id=callback.message.message_id)
            await callback.message.delete()
            return
        except Exception:
            pass

    status_msg = await callback.message.reply(await get_text(callback.from_user.id, "wait"))
    results = []
    
    try:
        async with ChatActionSender.upload_video(bot=callback.bot, chat_id=callback.message.chat.id):
            results = await download_media(url, is_audio=is_audio)
            
            if not results:
                await callback.message.reply(await get_text(callback.from_user.id, "too_large"))
                return
            
            if len(results) == 1:
                res = results[0]
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
                    sent_msg = await callback.message.reply_audio(audio=media, caption=caption_text)
                    if sent_msg.audio:
                        await MEDIA_CACHE.set(cache_key, {'type': 'audio', 'id': sent_msg.audio.file_id})
                elif is_photo:
                    sent_msg = await callback.message.reply_photo(photo=media, caption=caption_text)
                    if sent_msg.photo:
                        await MEDIA_CACHE.set(cache_key, {'type': 'photo', 'id': sent_msg.photo[-1].file_id})
                else:
                    sent_msg = await callback.message.reply_video(video=media, caption=caption_text)
                    if sent_msg.video:
                        await MEDIA_CACHE.set(cache_key, {'type': 'video', 'id': sent_msg.video.file_id})
            else:
                media_group = []
                for i, res in enumerate(results[:10]):
                    filepath = res['filepath']
                    file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                    
                    if file_size > 0 and file_size < 10 * 1024 * 1024:
                        with open(filepath, 'rb') as f:
                            file_bytes = f.read()
                        media = BufferedInputFile(file_bytes, filename=os.path.basename(filepath))
                        os.remove(filepath)
                    else:
                        media = FSInputFile(filepath)
                        
                    if res['ext'] in ['jpg', 'jpeg', 'png', 'webp']:
                        media_group.append(InputMediaPhoto(media=media, caption=caption_text if i == 0 else None))
                    else:
                        media_group.append(InputMediaVideo(media=media, caption=caption_text if i == 0 else None))
                
                sent_msgs = await callback.message.answer_media_group(media=media_group, reply_to_message_id=callback.message.message_id)
                if sent_msgs:
                    cached_items = []
                    for msg in sent_msgs:
                        if msg.photo:
                            cached_items.append({'type': 'photo', 'id': msg.photo[-1].file_id})
                        elif msg.video:
                            cached_items.append({'type': 'video', 'id': msg.video.file_id})
                    if cached_items:
                        await MEDIA_CACHE.set(cache_key, {'type': 'group', 'items': cached_items})
                    
    except Exception as e:
        await callback.message.reply(await get_text(callback.from_user.id, "error"))
    finally:
        for res in results:
            if res and 'filepath' in res and os.path.exists(res['filepath']):
                try:
                    os.remove(res['filepath'])
                except Exception:
                    pass
        try:
            await status_msg.delete()
        except Exception:
            pass
        try:
            await callback.message.delete()
        except Exception:
            pass'''

content = url_match_pattern.sub(new_handler, content)

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)
