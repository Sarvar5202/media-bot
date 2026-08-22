import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from aiogram.exceptions import TelegramForbiddenError', 
'''from aiogram.exceptions import TelegramForbiddenError
from locales import TEXTS
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery''')

content = content.replace('from db import add_user, get_stats, get_user_info, set_user_inactive, get_all_active_users, get_all_users',
'from db import add_user, get_stats, get_user_info, set_user_inactive, get_all_active_users, get_all_users, get_user_language, set_user_language, increment_platform_stat, get_platform_stats')

cache_class_block = '''USER_LANGS = {}

async def get_text(user_id: int, key: str) -> str:
    lang = USER_LANGS.get(user_id)
    if not lang:
        lang = await get_user_language(user_id)
        USER_LANGS[user_id] = lang
    return TEXTS.get(lang, TEXTS['uz'])[key]

class SmartCache:'''
content = content.replace('class SmartCache:', cache_class_block)

lang_cmd = '''@router.message(Command("language"))
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

@router.message(CommandStart())'''
content = content.replace('@router.message(CommandStart())', lang_cmd)

start_cmd_old = '''@router.message(CommandStart())
async def cmd_start(message: Message):
    await add_user(message.from_user.id, message.from_user.username)
    await message.reply("👋 Assalomu alaykum! Menga Instagram, TikTok, YouTube, X/Twitter, Pinterest yoki Facebook havolasini yuboring, uni darhol yuklab beraman. 🚀")'''
start_cmd_new = '''@router.message(CommandStart())
async def cmd_start(message: Message):
    await add_user(message.from_user.id, message.from_user.username)
    text = await get_text(message.from_user.id, 'start')
    await message.reply(text)'''
content = content.replace(start_cmd_old, start_cmd_new)

help_cmd_pattern = re.compile(r'@router\.message\(Command\("help"\)\).*?await message\.reply\(text, parse_mode="HTML"\)', re.DOTALL)
help_cmd_new = '''@router.message(Command("help"))
async def cmd_help(message: Message):
    text = await get_text(message.from_user.id, 'help')
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)'''
content = help_cmd_pattern.sub(help_cmd_new, content)

url_match_old = '''    url_hash = hashlib.md5(url.encode()).hexdigest()
    
    cached_data = await MEDIA_CACHE.get(url_hash)'''
url_match_new = '''    url_hash = hashlib.md5(url.encode()).hexdigest()
    
    platform = 'Boshqa'
    url_lower = url.lower()
    if 'instagram.com' in url_lower: platform = 'Instagram'
    elif 'tiktok.com' in url_lower: platform = 'TikTok'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower: platform = 'YouTube'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower: platform = 'X/Twitter'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower: platform = 'Facebook'
    elif 'pinterest.com' in url_lower or 'pin.it' in url_lower: platform = 'Pinterest'
    
    await increment_platform_stat(platform)
    
    caption_text = await get_text(message.from_user.id, 'caption')
    
    cached_data = await MEDIA_CACHE.get(url_hash)'''
content = content.replace(url_match_old, url_match_new)

content = content.replace('CAPTION_TEXT', 'caption_text')
content = content.replace('caption_text = "📥 @VidSaveUzBot orqali yuklab olindi"', '')

content = content.replace('await message.reply("⏳")', 'await message.reply(await get_text(message.from_user.id, "wait"))')
content = content.replace('await message.reply("❌ Hech qanday media topilmadi yoki fayl hajmi juda katta (>50MB).")', 'await message.reply(await get_text(message.from_user.id, "too_large"))')
content = content.replace('await message.reply("❌ Kechirasiz, media topilmadi yoki bu post yopiq/xususiy.")', 'await message.reply(await get_text(message.from_user.id, "error"))')

stats_old = '''    stats = await get_stats()
    text = (
        f"📊 <b>Bot statistikasi</b>:\\n\\n"
        f"👥 Jami foydalanuvchilar: {stats['total']}\\n"
        f"✅ Faol foydalanuvchilar: {stats['active']}\\n"
        f"📈 Oxirgi 24 soatda: +{stats['new_24h']}"
    )
    await message.reply(text, parse_mode="HTML")'''

stats_new = '''    stats = await get_stats()
    platform_stats = await get_platform_stats()
    
    text = (
        f"📊 <b>Bot statistikasi</b>:\\n\\n"
        f"👥 Jami foydalanuvchilar: {stats['total']}\\n"
        f"✅ Faol foydalanuvchilar: {stats['active']}\\n"
        f"📈 Oxirgi 24 soatda: +{stats['new_24h']}\\n\\n"
        f"🌐 <b>Platformalar (yuklashlar):</b>\\n"
    )
    
    total_downloads = sum(platform_stats.values()) if platform_stats else 0
    if total_downloads > 0:
        for plat, count in platform_stats.items():
            pct = (count / total_downloads) * 100
            text += f"• {plat}: {count} ({pct:.1f}%)\\n"
    else:
        text += "Hali ma'lumot yo'q.\\n"
        
    await message.reply(text, parse_mode="HTML")'''
content = content.replace(stats_old, stats_new)

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)
