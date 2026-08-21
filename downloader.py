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

from config import config

def get_base_opts():
    max_size = '2000M' if config.local_api_server_url else '50M'
    opts = {
        'format': f'bestvideo[ext=mp4][filesize<={max_size}]+bestaudio[ext=m4a]/best[ext=mp4][filesize<={max_size}]/best[filesize<={max_size}]/best',
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
            'youtube': ['player_client=android,web', 'player_skip=webpage'],
            'tiktok': ['api_hostname=api16-normal-c-useast1a.tiktokv.com', 'app_version=31.2.4']
        },
        'socket_timeout': 15,
    }
    if COOKIE_FILE:
        opts['cookiefile'] = COOKIE_FILE
    return opts

async def download_media(url: str, is_audio: bool = False, temp_dir: str = "downloads") -> list[dict]:
    def _download():
        dl_uuid = str(uuid.uuid4())[:8]
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        retries = 3
        last_error = None
        
        for attempt in range(retries):
            opts = get_base_opts()
            
            if is_audio:
                opts['format'] = 'bestaudio/best'
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
                opts['postprocessor_args'] = {
                    'ffmpeg': ['-af', 'volume=2.5,dynaudnorm', '-threads', '0']
                }
                opts['outtmpl'] = os.path.join(temp_dir, f'{dl_uuid}_%(extractor)s_%(id)s_%(playlist_index|)s.%(ext)s')
            else:
                opts['outtmpl'] = os.path.join(temp_dir, f'{dl_uuid}_%(extractor)s_%(id)s_%(playlist_index|)s.%(ext)s')
            
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
                            if is_audio:
                                filepath = os.path.splitext(filepath)[0] + '.mp3'
                            else:
                                filepath = entry.get('requested_downloads', [{}])[0].get('filepath', filepath)
                            
                            if os.path.exists(filepath):
                                results.append({
                                    'filepath': filepath,
                                    'title': entry.get('title', 'Media')[:100],
                                    'ext': 'mp3' if is_audio else entry.get('ext', 'mp4')
                                })
                    else:
                        filepath = ydl.prepare_filename(info)
                        if is_audio:
                            filepath = os.path.splitext(filepath)[0] + '.mp3'
                        else:
                            filepath = info.get('requested_downloads', [{}])[0].get('filepath', filepath)
                            
                        if os.path.exists(filepath):
                            results.append({
                                'filepath': filepath,
                                'title': info.get('title', 'Media')[:100],
                                'ext': 'mp3' if is_audio else info.get('ext', 'mp4')
                            })
                    return results
                
                except yt_dlp.utils.DownloadError as e:
                    last_error = e
                    continue
                except Exception as e:
                    last_error = e
                    break

        if last_error:
            err_msg = str(last_error).lower()
            if 'private' in err_msg or 'deleted' in err_msg or 'unavailable' in err_msg or 'not found' in err_msg:
                raise ValueError("private_video")
            elif 'timeout' in err_msg or 'network' in err_msg or 'timed out' in err_msg:
                raise ValueError("timeout")
            elif 'sign in' in err_msg or 'login' in err_msg:
                raise ValueError("login_required")
            raise last_error
        return []

    return await asyncio.to_thread(_download)
