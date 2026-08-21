import asyncio
import yt_dlp
import os
import uuid
import random

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
]

def setup_cookies():
    cookie_path = "cookies.txt"
    cookies_content = os.getenv("IG_COOKIES")
    if cookies_content:
        with open(cookie_path, "w") as f:
            f.write(cookies_content)
        return cookie_path
    
    session_id = os.getenv("IG_SESSIONID")
    if session_id:
        netscape_cookie = f".instagram.com\tTRUE\t/\tTRUE\t253402300799\tsessionid\t{session_id}\n"
        with open(cookie_path, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write(netscape_cookie)
        return cookie_path
        
    return None

COOKIE_FILE = setup_cookies()

def get_base_opts():
    opts = {
        'format': 'bestvideo[ext=mp4][filesize<=50M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<=50M]/best[filesize<=50M]/best',
        'format_sort': ['res:1080', 'ext:mp4:m4a'], # Prevent container mismatches and prioritize compatibility
        'merge_output_format': 'mp4',
        'concurrent_fragment_downloads': 10,
        'sleep_interval_requests': 1, # Rate-limit bypass for manifest requests
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'writethumbnail': False,
        'postprocessor_args': {
            'Merger': ['-threads', '0', '-preset', 'ultrafast']
        },
        'http_headers': {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate'
        },
        'extractor_args': {
            'youtube': ['player_client=android,web', 'player_skip=webpage']
        },
        'socket_timeout': 15,
    }
    if COOKIE_FILE:
        opts['cookiefile'] = COOKIE_FILE
    return opts

async def download_media(url: str) -> list[dict]:
    def _download():
        dl_uuid = str(uuid.uuid4())[:8]
        if not os.path.exists("downloads"):
            os.makedirs("downloads")
            
        retries = 3
        last_error = None
        
        for attempt in range(retries):
            opts = get_base_opts()
            opts['outtmpl'] = f'downloads/{dl_uuid}_%(extractor)s_%(id)s_%(playlist_index|)s.%(ext)s'
            
            if attempt > 0:
                opts['http_headers']['User-Agent'] = random.choice(USER_AGENTS)
                if 'instagram' in url:
                    opts['sleep_interval_requests'] = 2 * attempt
                if 'youtube' in url:
                    opts['extractor_args'] = {'youtube': ['player_client=ios,tv', 'player_skip=webpage']}

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    
                    results = []
                    if 'entries' in info:
                        for entry in info['entries']:
                            if not entry:
                                continue
                            filepath = ydl.prepare_filename(entry)
                            filepath = entry.get('requested_downloads', [{}])[0].get('filepath', filepath)
                            if os.path.exists(filepath):
                                results.append({
                                    'filepath': filepath,
                                    'title': entry.get('title', 'Media')[:100],
                                    'ext': entry.get('ext', 'mp4')
                                })
                    else:
                        filepath = ydl.prepare_filename(info)
                        filepath = info.get('requested_downloads', [{}])[0].get('filepath', filepath)
                        if os.path.exists(filepath):
                            results.append({
                                'filepath': filepath,
                                'title': info.get('title', 'Media')[:100],
                                'ext': info.get('ext', 'mp4')
                            })
                    return results
                
                except yt_dlp.utils.DownloadError as e:
                    last_error = e
                    continue
                except Exception as e:
                    last_error = e
                    break

        if last_error:
            raise last_error
        return []

    # Process extraction in a non-blocking asynchronous thread so the bot loop doesn't freeze
    return await asyncio.to_thread(_download)
