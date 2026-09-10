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
    ffmpeg_dir = os.path.dirname(ffmpeg_exe) if ffmpeg_exe and os.path.exists(ffmpeg_exe) else None
    
    # Priority: Lightweight progressive MP4 (<= 720p)
    # Avoids heavy RAM usage & ffmpeg merging errors on cloud servers like Render
    ydl_opts = {
        'format': 'best[height<=720][ext=mp4]/best[height<=480][ext=mp4]/best[ext=mp4]/22/18/best',
        'outtmpl': os.path.join(output_dir, 'youtube_%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'retries': 5,
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb', 'web']
            }
        }
    }
    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir
    
    info = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"[YOUTUBE DOWNLOAD] Ingesting URL: {url}")
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        print(f"[YOUTUBE DOWNLOAD] Primary stream download notice ({e}). Attempting fallback stream...")
        fallback_opts = {
            'format': '18/22/best[ext=mp4]/best',
            'outtmpl': os.path.join(output_dir, 'youtube_%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': False,
            'retries': 5,
            'socket_timeout': 30,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web']
                }
            }
        }
        if ffmpeg_dir:
            fallback_opts['ffmpeg_location'] = ffmpeg_dir
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    
    video_id = info.get('id')
    title = info.get('title', f"YouTube Video {video_id}")
    
    # Dynamically locate the downloaded file
    actual_file = None
    for candidate in os.listdir(output_dir):
        if candidate.startswith(f"youtube_{video_id}."):
            actual_file = os.path.join(output_dir, candidate)
            break
            
    if not actual_file or not os.path.exists(actual_file):
        actual_file = os.path.join(output_dir, f"youtube_{video_id}.mp4")
        
    filename = os.path.basename(actual_file)
    full_path = actual_file
    
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
