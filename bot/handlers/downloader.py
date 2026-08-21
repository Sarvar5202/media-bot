import os
import re
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, InputMediaVideo, InputMediaPhoto
from aiogram.utils.chat_action import ChatActionSender
from bot.services.media_service import download_media
from bot.services.cache import get_cached_file_id, set_cached_file_id

router = Router()

URL_PATTERN = re.compile(
    r'(https?://(?:www\.)?(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be|x\.com|twitter\.com|facebook\.com|pin\.it|pinterest\.com)[^\s]+)'
)

@router.message(F.text.regexp(URL_PATTERN).as_("url_match"))
async def handle_media_url(message: Message, url_match: re.Match):
    url = url_match.group(1)
    
    cached_id = await get_cached_file_id(url)
    if cached_id:
        try:
            # Attempt to send as video first, then fallback to document
            try:
                await message.reply_video(video=cached_id)
            except Exception:
                await message.reply_document(document=cached_id)
            return
        except Exception:
            pass # cache miss or invalid, fallback to download

    status_msg = await message.reply("⏳ Downloading media...")
    
    try:
        async with ChatActionSender.upload_video(bot=message.bot, chat_id=message.chat.id):
            results = await download_media(url)
            
            if not results:
                await message.reply("❌ No media found or file too large (>50MB).")
                return
            
            if len(results) == 1:
                res = results[0]
                media = FSInputFile(res['filepath'])
                
                is_photo = res['ext'] in ['jpg', 'jpeg', 'png', 'webp']
                
                if is_photo:
                    sent_msg = await message.reply_photo(photo=media, caption=res['title'])
                    if sent_msg.photo:
                        await set_cached_file_id(url, sent_msg.photo[-1].file_id)
                else:
                    sent_msg = await message.reply_video(video=media, caption=res['title'])
                    if sent_msg.video:
                        await set_cached_file_id(url, sent_msg.video.file_id)
            else:
                media_group = []
                for res in results[:10]:
                    media = FSInputFile(res['filepath'])
                    if res['ext'] in ['jpg', 'jpeg', 'png', 'webp']:
                        media_group.append(InputMediaPhoto(media=media))
                    else:
                        media_group.append(InputMediaVideo(media=media))
                
                await message.answer_media_group(media=media_group, reply_to_message_id=message.message_id)

            # Cleanup
            for res in results:
                if os.path.exists(res['filepath']):
                    os.remove(res['filepath'])
                    
    except Exception as e:
        await message.reply(f"❌ Failed to download media.\nError: {str(e)[:100]}")
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass
