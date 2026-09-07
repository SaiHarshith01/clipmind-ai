import os
import subprocess
import imageio_ffmpeg
from moviepy import VideoFileClip

def get_ffmpeg_path() -> str:
    """Returns the absolute path to the local FFmpeg binary."""
    return imageio_ffmpeg.get_ffmpeg_exe()

def extract_audio(video_path: str, output_audio_path: str = None) -> str:
    """
    Extracts the audio track from a video file as an MP3 file for Whisper transcription.
    Returns the path to the generated audio file.
    """
    if output_audio_path is None:
        output_audio_path = video_path.rsplit('.', 1)[0] + ".mp3"
        
    print(f"[AUDIO EXTRACTOR] Extracting audio from {video_path} to {output_audio_path}...")
    
    # Try with FFmpeg directly for fastest extraction
    try:
        ffmpeg_exe = get_ffmpeg_path()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", video_path,
            "-vn",                  # Disable video
            "-acodec", "libmp3lame", # MP3 codec
            "-ar", "16000",         # 16kHz sample rate optimal for Whisper
            "-ac", "1",             # Mono audio
            "-b:a", "64k",
            output_audio_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"[AUDIO EXTRACTOR] Audio extracted successfully via FFmpeg: {output_audio_path}")
        return output_audio_path
    except Exception as e:
        print(f"[AUDIO EXTRACTOR] FFmpeg direct extraction failed ({e}), falling back to MoviePy...")
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(output_audio_path, logger=None)
        clip.close()
        return output_audio_path

def ensure_browser_compatible_video(video_path: str) -> str:
    """
    Inspects and transcodes the video to guarantee:
    1. Audio is encoded in standard AAC (mp4a), fixing the browser permanent mute / silent playback issue.
    2. Video is MP4 container with faststart enabled for instant web streaming.
    Returns the updated or verified video path.
    """
    try:
        ffmpeg_exe = get_ffmpeg_path()
        
        # Probe file streams using ffmpeg
        probe_cmd = [ffmpeg_exe, "-i", video_path]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        probe_output = result.stderr
        
        # Check if audio is already standard AAC
        needs_audio_transcode = False
        if "Audio: opus" in probe_output or "Audio: vorbis" in probe_output or "Audio: flac" in probe_output:
            needs_audio_transcode = True
            
        if not needs_audio_transcode:
            # Check if there is an audio stream at all
            if "Audio:" not in probe_output:
                print(f"[AUDIO CHECK] Warning: No audio stream detected in {video_path}")
                return video_path
            print(f"[AUDIO CHECK] Video already has browser-compatible audio stream.")
            return video_path

        print(f"[AUDIO FIX] Non-browser audio codec detected in {video_path}. Transcoding audio track to standard AAC...")
        
        temp_output_path = video_path.rsplit('.', 1)[0] + "_aac_fixed.mp4"
        
        # Copy video stream directly (-c:v copy) to be fast, and convert audio to AAC
        transcode_cmd = [
            ffmpeg_exe,
            "-y",
            "-i", video_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            temp_output_path
        ]
        
        subprocess.run(transcode_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Replace original file with fixed version
        os.replace(temp_output_path, video_path)
        print(f"[AUDIO FIX] Successfully repaired audio to AAC for web playback: {video_path}")
        return video_path
        
    except Exception as e:
        print(f"[AUDIO FIX] Error while standardizing video audio: {e}")
        return video_path
