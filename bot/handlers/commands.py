import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply("👋 Welcome to the Universal Media Downloader!\n\nJust send me a link from Instagram, TikTok, YouTube, X/Twitter, Pinterest, or Facebook and I'll download the media for you.")

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply("Just paste a link!\nIf a download fails, it might be due to a private account, region lock, or file size limits (Telegram bots are limited to 50MB uploads).")
