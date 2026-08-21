import os
import re
import hashlib
from aiocache import Cache
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, InputMediaVideo, InputMediaPhoto
from aiogram.filters import CommandStart, Command
from aiogram.utils.chat_action import ChatActionSender
from downloader import download_media
from db import add_user, get_users_count, get_all_users

router = Router()

URL_PATTERN = re.compile(
    r'(https?://(?:www\.)?(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be|x\.com|twitter\.com|facebook\.com|pin\.it|pinterest\.com)[^\s]+)'
)

import io
import time
import asyncio

class SmartCache:
    def __init__(self, ttl=3600, max_items=1000):
        self.cache = Cache(Cache.MEMORY, ttl=ttl)
        self.ttl = ttl
        self.max_items = max_items
        self.keys = {}
        
    async def get(self, key):
        return await self.cache.get(key)
        
    async def set(self, key, value):
        await self.cache.set(key, value)
        self.keys[key] = time.time()
        
    async def cleanup(self):
        now = time.time()
        expired = [k for k, t in self.keys.items() if now - t > self.ttl]
        for k in expired:
            await self.cache.delete(k)
            self.keys.pop(k, None)
            
        if len(self.keys) > self.max_items:
            sorted_keys = sorted(self.keys.items(), key=lambda x: x[1])
            to_remove = len(self.keys) - self.max_items
            for k, _ in sorted_keys[:to_remove]:
                await self.cache.delete(k)
                self.keys.pop(k, None)

MEDIA_CACHE = SmartCache(ttl=3600, max_items=1000)

async def cache_cleanup_task():
    while True:
        await asyncio.sleep(600)
        try:
            await MEDIA_CACHE.cleanup()
        except Exception:
            pass

CAPTION_TEXT = "📥 @VidSaveUzBot orqali yuklab olindi"
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
SUPER_ADMIN_ID = 7890020641

@router.message(CommandStart())
async def cmd_start(message: Message):
    add_user(message.from_user.id, message.from_user.username)
    await message.reply("👋 Assalomu alaykum! Menga Instagram, TikTok, YouTube, X/Twitter, Pinterest yoki Facebook havolasini yuboring, uni darhol yuklab beraman. 🚀")

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply("Shunchaki havolani yuboring! Men uni siz uchun yuklab beraman. (Maksimal hajmi 50MB)")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not ADMIN_IDS or message.from_user.id in ADMIN_IDS or message.from_user.id == SUPER_ADMIN_ID:
        count = get_users_count()
        await message.reply(f"📊 Bot statistikasi:\nJami foydalanuvchilar: {count} ta")
    else:
        await message.reply("❌ Sizda bu buyruqdan foydalanish huquqi yo'q.")

@router.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    
    count = get_users_count()
    users_list = get_all_users(50)
    
    text = f"📊 Jami foydalanuvchilar: {count} ta\n\nRo'yxat (oxirgi 50 ta):\n"
    for uid, uname in users_list:
        uname_text = f"@{uname}" if uname else "Mavjud emas"
        text += f"🆔 {uid} | 👤 {uname_text}\n"
    
    await message.reply(text)

from aiogram.types import BufferedInputFile

@router.message(F.text.regexp(URL_PATTERN).as_("url_match"))
async def handle_media_url(message: Message, url_match: re.Match):
    url = url_match.group(1)
    url_hash = hashlib.md5(url.encode()).hexdigest()
    
    cached_data = await MEDIA_CACHE.get(url_hash)
    if cached_data:
        try:
            if cached_data['type'] == 'photo':
                await message.reply_photo(photo=cached_data['id'], caption=CAPTION_TEXT)
            elif cached_data['type'] == 'video':
                await message.reply_video(video=cached_data['id'], caption=CAPTION_TEXT)
            elif cached_data['type'] == 'group':
                media_group = []
                for i, item in enumerate(cached_data['items']):
                    if item['type'] == 'photo':
                        media_group.append(InputMediaPhoto(media=item['id'], caption=CAPTION_TEXT if i == 0 else None))
                    else:
                        media_group.append(InputMediaVideo(media=item['id'], caption=CAPTION_TEXT if i == 0 else None))
                await message.answer_media_group(media=media_group, reply_to_message_id=message.message_id)
            return
        except Exception:
            pass

    status_msg = await message.reply("⏳")
    results = []
    
    try:
        async with ChatActionSender.upload_video(bot=message.bot, chat_id=message.chat.id):
            results = await download_media(url)
            
            if not results:
                await message.reply("❌ Hech qanday media topilmadi yoki fayl hajmi juda katta (>50MB).")
                return
            
            if len(results) == 1:
                res = results[0]
                filepath = res['filepath']
                is_photo = res['ext'] in ['jpg', 'jpeg', 'png', 'webp']
                file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                
                # RAM Buffering for lightweight media (< 10MB)
                if file_size > 0 and file_size < 10 * 1024 * 1024:
                    with open(filepath, 'rb') as f:
                        file_bytes = f.read()
                    media = BufferedInputFile(file_bytes, filename=os.path.basename(filepath))
                    os.remove(filepath)
                else:
                    media = FSInputFile(filepath)
                
                if is_photo:
                    sent_msg = await message.reply_photo(photo=media, caption=CAPTION_TEXT)
                    if sent_msg.photo:
                        await MEDIA_CACHE.set(url_hash, {'type': 'photo', 'id': sent_msg.photo[-1].file_id})
                else:
                    sent_msg = await message.reply_video(video=media, caption=CAPTION_TEXT)
                    if sent_msg.video:
                        await MEDIA_CACHE.set(url_hash, {'type': 'video', 'id': sent_msg.video.file_id})
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
                        media_group.append(InputMediaPhoto(media=media, caption=CAPTION_TEXT if i == 0 else None))
                    else:
                        media_group.append(InputMediaVideo(media=media, caption=CAPTION_TEXT if i == 0 else None))
                
                sent_msgs = await message.answer_media_group(media=media_group, reply_to_message_id=message.message_id)
                if sent_msgs:
                    cached_items = []
                    for msg in sent_msgs:
                        if msg.photo:
                            cached_items.append({'type': 'photo', 'id': msg.photo[-1].file_id})
                        elif msg.video:
                            cached_items.append({'type': 'video', 'id': msg.video.file_id})
                    if cached_items:
                        await MEDIA_CACHE.set(url_hash, {'type': 'group', 'items': cached_items})
                    
    except Exception as e:
        await message.reply("❌ Kechirasiz, media topilmadi yoki bu post yopiq/xususiy.")
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
