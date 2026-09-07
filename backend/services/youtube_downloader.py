import os
import yt_dlp
import imageio_ffmpeg
from services.audio_extractor import ensure_browser_compatible_video

def download_youtube_video(url: str, output_dir: str) -> dict:
    """
    Downloads a YouTube video as an MP4 file into the specified output directory.
    Guarantees browser-compatible AAC audio stream and H.264 video.
    Returns a dictionary with 'filename' and 'title'.
    """
    os.makedirs(output_dir, exist_ok=True)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Request MP4 / M4A streams whenever available for native web browser playback
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best',
        'outtmpl': os.path.join(output_dir, 'youtube_%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'recode_video': 'mp4',
        'merge_output_format': 'mp4',
        'ffmpeg_location': ffmpeg_exe,
        'postprocessor_args': {
            'Merger': ['-c:a', 'aac']
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"[YOUTUBE DOWNLOAD] Ingesting URL: {url}")
        info = ydl.extract_info(url, download=True)
        video_id = info.get('id')
        title = info.get('title', f"YouTube Video {video_id}")
        filename = f"youtube_{video_id}.mp4"
        full_path = os.path.join(output_dir, filename)
        
        description = info.get('description', '') or ''
        uploader = info.get('uploader') or info.get('channel') or ''
        artist = info.get('artist') or ''
        track = info.get('track') or ''
        album = info.get('album') or ''
        tags = info.get('tags') or []

        metadata = {
            "description": description,
            "uploader": uploader,
            "artist": artist,
            "track": track,
            "album": album,
            "tags": tags,
            "source": "youtube"
        }

        # Post-download verification: ensure browser audio compatibility (AAC)
        if os.path.exists(full_path):
            ensure_browser_compatible_video(full_path)

        print(f"[YOUTUBE DOWNLOAD] Completed! Title: '{title}' | Saved as: {filename}")
        
        return {
            "filename": filename,
            "title": title,
            "metadata": metadata
        }
