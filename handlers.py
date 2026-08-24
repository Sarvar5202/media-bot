import os
import re
import hashlib
from aiocache import Cache
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, InputMediaVideo, InputMediaPhoto, BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.utils.chat_action import ChatActionSender
from aiogram.exceptions import TelegramForbiddenError
from locales import TEXTS
import tempfile
import shutil
from contextlib import asynccontextmanager
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from downloader import download_media, get_media_info
import asyncio
from db import add_user, get_stats, get_user_info, set_user_inactive, get_all_active_users, get_all_users, get_user_language, set_user_language, increment_platform_stat, get_platform_stats
from config import config
import io
import time
import asyncio

router = Router()

URL_PATTERN = re.compile(
    r'(https?://(?:www\.)?(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be|x\.com|twitter\.com|facebook\.com|pin\.it|pinterest\.com)[a-zA-Z0-9_\-\./\?=&%]+)'
)

USER_LANGS = {}

async def get_text(user_id: int, key: str) -> str:
    lang = USER_LANGS.get(user_id)
    if not lang:
        lang = await get_user_language(user_id)
        USER_LANGS[user_id] = lang
    return TEXTS.get(lang, TEXTS['uz'])[key]

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
URL_CACHE = SmartCache(ttl=3600, max_items=1000)

async def cache_cleanup_task():
    while True:
        await asyncio.sleep(600)
        try:
            await MEDIA_CACHE.cleanup()
            await URL_CACHE.cleanup()
        except Exception:
            pass



@asynccontextmanager
async def temporary_media_directory():
    temp_dir = tempfile.mkdtemp(prefix="vidsave_")
    try:
        yield temp_dir
    finally:
        await asyncio.to_thread(shutil.rmtree, temp_dir, ignore_errors=True)

def is_admin(user_id: int) -> bool:
    if config.admin_id and user_id == config.admin_id:
        return True
    return False

@router.message(Command("language"))
async def cmd_language(message: Message):
    text = await get_text(message.from_user.id, 'lang_prompt')
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ])
    await message.reply(text, reply_markup=markup)

@router.callback_query(F.data.startswith("lang_"))
async def process_lang(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1]
    await set_user_language(callback.from_user.id, lang_code)
    USER_LANGS[callback.from_user.id] = lang_code
    
    success_text = await get_text(callback.from_user.id, 'lang_set')
    await callback.message.edit_text(success_text)
    await callback.answer()

@router.message(CommandStart())
async def cmd_start(message: Message):
    text = await get_text(message.from_user.id, 'start')
    await message.reply(text)

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = await get_text(message.from_user.id, 'help')
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    stats = await get_stats()
    platform_stats = await get_platform_stats()
    
    text = (
        f"📊 <b>Bot statistikasi</b>:\n\n"
        f"👥 Jami foydalanuvchilar: {stats['total']}\n"
        f"✅ Faol foydalanuvchilar: {stats['active']}\n"
        f"📈 Oxirgi 24 soatda: +{stats['new_24h']}\n\n"
        f"🌐 <b>Platformalar (yuklashlar):</b>\n"
    )
    
    total_downloads = sum(platform_stats.values()) if platform_stats else 0
    if total_downloads > 0:
        for plat, count in platform_stats.items():
            pct = (count / total_downloads) * 100
            text += f"• {plat}: {count} ({pct:.1f}%)\n"
    else:
        text += "Hali ma'lumot yo'q.\n"
        
    await message.reply(text, parse_mode="HTML")

@router.message(Command("users"))
async def cmd_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    users_list = await get_all_users()
    count = len(users_list)
    
    text = f"📊 Jami foydalanuvchilar: {count} ta\n\nRo'yxat:\n"
    for u in users_list:
        uname_text = f"@{u['username']}" if u['username'] else "Mavjud emas"
        fname_text = u['full_name'] or "Mavjud emas"
        date_str = u['created_at'].strftime('%Y-%m-%d %H:%M') if u['created_at'] else "Noma'lum"
        text += f"🆔 {u['user_id']} | 👤 {uname_text} | 📝 {fname_text} | 🕒 {date_str}\n"
    
    if len(text) > 4000:
        file = BufferedInputFile(text.encode('utf-8'), filename=f"users_list_{count}.txt")
        await message.reply_document(document=file, caption=f"📊 Jami foydalanuvchilar: {count} ta")
    else:
        await message.reply(text)

@router.message(Command("user_info"))
async def cmd_user_info(message: Message):
    if not is_admin(message.from_user.id):
        return
        
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("❌ Format: /user_info <telegram_id>")
        return
        
    user_id = int(parts[1])
    info = await get_user_info(user_id)
    
    if not info:
        await message.reply("❌ Foydalanuvchi topilmadi.")
        return
        
    status = "✅ Faol" if info['is_active'] else "❌ Nofaol"
    uname = f"@{info['username']}" if info['username'] else "Mavjud emas"
    
    created_at_str = info['created_at'].strftime('%Y-%m-%d %H:%M') if info['created_at'] else "Noma'lum"
    last_active_str = info['last_active'].strftime('%Y-%m-%d %H:%M') if info['last_active'] else "Noma'lum"
    
    text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari</b>:\n\n"
        f"🆔 ID: <code>{info['user_id']}</code>\n"
        f"👤 Username: {uname}\n"
        f"Holat: {status}\n"
        f"🕒 Qo'shilgan vaqti: {created_at_str}\n"
        f"⏱ Oxirgi faollik: {last_active_str}"
    )
    await message.reply(text, parse_mode="HTML")

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not is_admin(message.from_user.id):
        return
        
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Format: /broadcast <xabar matni>")
        return
        
    text_to_send = parts[1]
    active_users = await get_all_active_users()
    
    if not active_users:
        await message.reply("❌ Faol foydalanuvchilar topilmadi.")
        return
        
    await message.reply(f"⏳ Xabar {len(active_users)} ta foydalanuvchiga yuborilmoqda...")
    
    sent_count = 0
    blocked_count = 0
    
    for uid in active_users:
        try:
            await message.bot.send_message(chat_id=uid, text=text_to_send)
            sent_count += 1
            await asyncio.sleep(0.05)
        except TelegramForbiddenError:
            blocked_count += 1
            await set_user_inactive(uid)
        except Exception:
            pass
            
    await message.reply(f"✅ Tarqatish yakunlandi!\n\nYetkazildi: {sent_count}\nBlokladi: {blocked_count}")

@router.message(F.text.regexp(URL_PATTERN).as_("url_match"))
async def handle_media_url(message: Message, url_match: re.Match):
    wait_msg = None
    try:
        url = url_match.group(1)
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        await URL_CACHE.set(url_hash, url)
        
        wait_msg = await message.reply(await get_text(message.from_user.id, "wait"))
        
        info = await get_media_info(url)
        duration = info.get('duration', None) if info else None
        
        if duration is not None and duration <= 300:
            await wait_msg.delete()
            await execute_download_and_send(url, url_hash, False, message.from_user.id, message.bot, message.chat.id, message.message_id)
        else:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Videoni yuklab olish", callback_data=f"dl_vid|{url_hash}")],
                [InlineKeyboardButton(text="🎵 MP3 (Ovozni kuchaytirish)", callback_data=f"dl_aud|{url_hash}")]
            ])
            await wait_msg.delete()
            await message.reply("Qaysi formatda yuklab olamiz? / Выберите формат: / Choose format:", reply_markup=markup)
    except ValueError as ve:
        if wait_msg:
            try:
                await wait_msg.delete()
            except:
                pass
        err_key = str(ve)
        try:
            if err_key in ["private_video", "timeout", "login_required"]:
                await message.reply(await get_text(message.from_user.id, err_key))
            else:
                await message.reply(await get_text(message.from_user.id, "error"))
        except:
            pass
    except Exception as e:
        if wait_msg:
            try:
                await wait_msg.delete()
            except:
                pass
        try:
            await message.reply(await get_text(message.from_user.id, "error"))
        except:
            pass

async def execute_download_and_send(url: str, url_hash: str, is_audio: bool, user_id: int, bot, chat_id: int, reply_to_message_id: int, status_msg_to_delete=None):
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
                caption_text = f"{caption_text}\n\n{music_detected_fmt.format(track_info=track_info)}"
                
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
                    caption_text = f"{caption_text}\n\n{music_detected_fmt.format(track_info=track_info)}"
                    
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
                        item_caption = f"{caption_text}\n\n{music_detected_fmt.format(track_info=res.get('track_info'))}"
                    
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
        try:
            if err_key in ["private_video", "timeout", "login_required"]:
                await bot.send_message(chat_id=chat_id, text=await get_text(user_id, err_key), reply_to_message_id=reply_to_message_id)
            else:
                await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "error"), reply_to_message_id=reply_to_message_id)
        except Exception:
            pass
        return False
    except TelegramForbiddenError:
        # User blocked the bot
        await set_user_inactive(user_id)
        return False
    except Exception as e:
        try:
            await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "error"), reply_to_message_id=reply_to_message_id)
        except Exception:
            pass
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

