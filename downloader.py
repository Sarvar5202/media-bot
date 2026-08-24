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
    cookie_path = os.path.abspath("cookies.txt")
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

from config import config

import shutil

def get_base_opts(url=""):
    max_size = '2000M' if config.local_api_server_url else '50M'
    has_ffmpeg = shutil.which('ffmpeg') is not None
    
    fmt = f'bestvideo[ext=mp4][filesize<={max_size}]+bestaudio[ext=m4a]/best[ext=mp4][filesize<={max_size}]/best[filesize<={max_size}]/best' if has_ffmpeg else f'b[ext=mp4][filesize<={max_size}]/best[filesize<={max_size}]/best'
    
    opts = {
        'format': fmt,
        'format_sort': ['res:1080', 'ext:mp4:m4a'], 
        'merge_output_format': 'mp4' if has_ffmpeg else None,
        'concurrent_fragment_downloads': 10,
        'sleep_interval_requests': 1, 
        'noplaylist': 'instagram' not in url.lower(),
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'writethumbnail': False,
        'http_headers': {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Dest': 'document',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        },
        'extractor_args': {
            'youtube': ['player_client=android,mweb,web', 'player_skip=webpage'],
            'tiktok': ['api_hostname=api16-normal-c-useast1a.tiktokv.com', 'app_version=31.2.4']
        },
        'socket_timeout': 15,
    }
    
    cookie_file = setup_cookies()
    if cookie_file and os.path.exists(cookie_file):
        opts['cookiefile'] = cookie_file
        
    if has_ffmpeg:
        opts['postprocessor_args'] = {
            'Merger': ['-threads', '0', '-preset', 'ultrafast']
        }
        
    return opts

async def get_media_info(url: str) -> dict:
    def _extract():
        retries = 2
        last_error = None
        for attempt in range(retries):
            opts = get_base_opts(url)
            opts['extract_flat'] = False 
            
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
                except Exception as e:
                    last_error = e
                    continue
        
        if 'instagram' in url.lower():
            # If yt-dlp fails to extract info for instagram, return a dummy fallback info
            return {"title": "Instagram Media", "duration": 0}
            
        if last_error:
            err_msg = str(last_error).lower()
            if 'private' in err_msg or 'deleted' in err_msg or 'unavailable' in err_msg or 'not found' in err_msg:
                raise ValueError("private_video")
            elif 'timeout' in err_msg or 'network' in err_msg or 'timed out' in err_msg:
                raise ValueError("timeout")
            elif 'sign in' in err_msg or 'login' in err_msg:
                raise ValueError("login_required")
            raise last_error
            
        return {}

    return await asyncio.to_thread(_extract)

async def download_media(url: str, is_audio: bool = False, temp_dir: str = "downloads") -> list[dict]:
    def _download():
        dl_uuid = str(uuid.uuid4())[:8]
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        retries = 3
        last_error = None
        has_ffmpeg = shutil.which('ffmpeg') is not None
        
        for attempt in range(retries):
            opts = get_base_opts(url)
            
            if is_audio:
                opts['format'] = 'bestaudio/best'
                if has_ffmpeg:
                    opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                    opts['postprocessor_args'] = {
                        'ffmpeg': ['-af', 'volume=2.5,dynaudnorm', '-threads', '0']
                    }
                opts['outtmpl'] = os.path.join(temp_dir, 'VidSaveUzBot.%(ext)s')
            else:
                opts['outtmpl'] = os.path.join(temp_dir, f'{dl_uuid}_%(extractor)s_%(id)s_%(playlist_index|)s.%(ext)s')
            
            if attempt > 0:
                opts['http_headers']['User-Agent'] = random.choice(USER_AGENTS)
                if 'instagram' in url:
                    opts['sleep_interval_requests'] = 2 * attempt
                if 'youtube' in url:
                    opts['extractor_args'] = {'youtube': ['player_client=ios,tv,web', 'player_skip=webpage']}

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        continue
                    
                    results = []
                    if 'entries' in info:
                        for entry in info['entries']:
                            if not entry:
                                continue
                            filepath = ydl.prepare_filename(entry)
                            if is_audio and has_ffmpeg:
                                filepath = os.path.splitext(filepath)[0] + '.mp3'
                            else:
                                req_dl = entry.get('requested_downloads')
                                if req_dl and isinstance(req_dl, list) and len(req_dl) > 0:
                                    filepath = req_dl[0].get('filepath', filepath)
                            
                            if os.path.exists(filepath):
                                track_info = entry.get('artist') and entry.get('track') and f"{entry.get('artist')} - {entry.get('track')}" or entry.get('track') or entry.get('artist')
                                results.append({
                                    'filepath': filepath,
                                    'title': entry.get('title', 'Media')[:100],
                                    'ext': 'mp3' if (is_audio and has_ffmpeg) else entry.get('ext', 'mp4'),
                                    'track_info': track_info
                                })
                    else:
                        filepath = ydl.prepare_filename(info)
                        if is_audio and has_ffmpeg:
                            filepath = os.path.splitext(filepath)[0] + '.mp3'
                        else:
                            req_dl = info.get('requested_downloads')
                            if req_dl and isinstance(req_dl, list) and len(req_dl) > 0:
                                filepath = req_dl[0].get('filepath', filepath)
                            
                        if os.path.exists(filepath):
                            track_info = info.get('artist') and info.get('track') and f"{info.get('artist')} - {info.get('track')}" or info.get('track') or info.get('artist')
                            results.append({
                                'filepath': filepath,
                                'title': info.get('title', 'Media')[:100],
                                'ext': 'mp3' if (is_audio and has_ffmpeg) else info.get('ext', 'mp4'),
                                'track_info': track_info
                            })
                    if results:
                        return results
                    elif 'instagram' in url.lower():
                        raise RuntimeError("fallback_required")
                
                except yt_dlp.utils.DownloadError as e:
                    last_error = e
                    continue
                except Exception as e:
                    last_error = e
                    break

        if 'instagram' in url.lower():
            raise RuntimeError("fallback_required")
            
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

    try:
        return await asyncio.to_thread(_download)
    except RuntimeError as e:
        if str(e) == "fallback_required":
            import aiohttp
            import json
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Origin': 'https://cobalt.tools',
                'Referer': 'https://cobalt.tools/'
            }
            payload = {
                "url": url,
                "isAudioOnly": is_audio,
                "aFormat": "mp3" if is_audio else "best"
            }
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.post("https://api.cobalt.tools/", json=payload, timeout=20) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            urls_to_download = []
                            status = data.get("status")
                            if status in ["stream", "redirect"]:
                                urls_to_download.append(data.get("url"))
                            elif status == "picker":
                                for item in data.get("picker", []):
                                    urls_to_download.append(item.get("url"))
                                    
                            results = []
                            for dl_url in urls_to_download:
                                ext = 'mp3' if is_audio else 'mp4'
                                if '.jpg' in dl_url or '.webp' in dl_url:
                                    ext = 'jpg'
                                filepath = os.path.join(temp_dir, f"{str(uuid.uuid4())[:8]}_fallback.{ext}")
                                
                                async with session.get(dl_url) as file_resp:
                                    if file_resp.status == 200:
                                        with open(filepath, 'wb') as f:
                                            f.write(await file_resp.read())
                                        results.append({
                                            'filepath': filepath,
                                            'title': 'Instagram Media',
                                            'ext': ext,
                                            'track_info': None
                                        })
                            if results:
                                return results
            except Exception:
                pass
            raise ValueError("error")
        raise e
