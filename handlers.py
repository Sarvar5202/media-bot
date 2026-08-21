import os
import re
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

MEDIA_CACHE = {}
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

@router.message(F.text.regexp(URL_PATTERN).as_("url_match"))
async def handle_media_url(message: Message, url_match: re.Match):
    url = url_match.group(1)
    
    if url in MEDIA_CACHE:
        cached_id = MEDIA_CACHE[url]
        try:
            try:
                await message.reply_video(video=cached_id, caption=CAPTION_TEXT)
            except Exception:
                await message.reply_document(document=cached_id, caption=CAPTION_TEXT)
            return
        except Exception:
            pass

    status_msg = await message.reply("⏳")
    
    try:
        async with ChatActionSender.upload_video(bot=message.bot, chat_id=message.chat.id):
            results = await download_media(url)
            
            if not results:
                await message.reply("❌ Hech qanday media topilmadi yoki fayl hajmi juda katta (>50MB).")
                return
            
            if len(results) == 1:
                res = results[0]
                media = FSInputFile(res['filepath'])
                
                is_photo = res['ext'] in ['jpg', 'jpeg', 'png', 'webp']
                
                if is_photo:
                    sent_msg = await message.reply_photo(photo=media, caption=CAPTION_TEXT)
                    if sent_msg.photo:
                        MEDIA_CACHE[url] = sent_msg.photo[-1].file_id
                else:
                    sent_msg = await message.reply_video(video=media, caption=CAPTION_TEXT)
                    if sent_msg.video:
                        MEDIA_CACHE[url] = sent_msg.video.file_id
            else:
                media_group = []
                for i, res in enumerate(results[:10]):
                    media = FSInputFile(res['filepath'])
                    if res['ext'] in ['jpg', 'jpeg', 'png', 'webp']:
                        media_group.append(InputMediaPhoto(media=media, caption=CAPTION_TEXT if i == 0 else None))
                    else:
                        media_group.append(InputMediaVideo(media=media, caption=CAPTION_TEXT if i == 0 else None))
                
                await message.answer_media_group(media=media_group, reply_to_message_id=message.message_id)

            for res in results:
                if os.path.exists(res['filepath']):
                    os.remove(res['filepath'])
                    
    except Exception as e:
        await message.reply("❌ Kechirasiz, media topilmadi yoki bu post yopiq/xususiy.")
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass
