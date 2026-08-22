import re

with open('downloader.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = '''async def get_media_info(url: str) -> dict:
    def _extract():
        retries = 2
        for attempt in range(retries):
            opts = get_base_opts()
            opts['extract_flat'] = False # We need duration
            
            if attempt > 0:
                opts['http_headers']['User-Agent'] = random.choice(USER_AGENTS)
                if 'instagram' in url:
                    opts['sleep_interval_requests'] = 2 * attempt
                if 'youtube' in url:
                    opts['extractor_args'] = {'youtube': ['player_client=ios,tv,web', 'player_skip=webpage']}

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        return info
                except Exception:
                    continue
        return {}

    return await asyncio.to_thread(_extract)

async def download_media(url: str, is_audio: bool = False, temp_dir: str = "downloads") -> list[dict]:'''

content = content.replace('async def download_media(url: str, is_audio: bool = False, temp_dir: str = "downloads") -> list[dict]:', new_func)

with open('downloader.py', 'w', encoding='utf-8') as f:
    f.write(content)
