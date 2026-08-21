import asyncio
import yt_dlp
import os
import uuid

YTDL_OPTS = {
    'format': 'bestvideo[filesize<=50M][ext=mp4]+bestaudio[ext=m4a]/best[filesize<=50M][ext=mp4]/best',
    'outtmpl': '/tmp/%(extractor)s_%(id)s_%(playlist_index|)s.%(ext)s',
    'noplaylist': False,
    'quiet': True,
    'no_warnings': True,
    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
}

async def download_media(url: str) -> list[dict]:
    def _download():
        opts = YTDL_OPTS.copy()
        
        dl_uuid = str(uuid.uuid4())[:8]
        opts['outtmpl'] = f'/tmp/{dl_uuid}_%(extractor)s_%(id)s_%(playlist_index|)s.%(ext)s'
        
        with yt_dlp.YoutubeDL(opts) as ydl:
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

    return await asyncio.to_thread(_download)
