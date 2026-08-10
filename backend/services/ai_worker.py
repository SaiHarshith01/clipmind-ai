import os
from core.database import SessionLocal
from models.schema import Video
from moviepy import VideoFileClip

def process_video_task(video_id: int):
    print(f"DEBUG: [AI WORKER] Function entered for Video ID: {video_id}")
    
    db = SessionLocal()
    video = None
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            print(f"DEBUG: [AI WORKER] Video {video_id} not found!")
            return

        # 1. Define where the video is and where the audio should go
        video_path = f"uploads/{video.filename}"
        audio_filename = video.filename.rsplit('.', 1)[0] + ".mp3"
        audio_path = f"uploads/{audio_filename}"

        print(f"DEBUG: [AI WORKER] Starting FFmpeg audio extraction for {video.filename}...")
        
        # 2. Use MoviePy (FFmpeg) to extract the audio
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path, logger=None) # logger=None keeps the terminal clean
        clip.close()
        print(f"DEBUG: [AI WORKER] Success! Audio saved as {audio_filename}")
        
        # 3. Mark video processing status as completed
        video.status = "completed"
        db.commit()
        
    except Exception as e:
        print(f"DEBUG: [AI WORKER] Error during video/audio processing: {e}")
        # If it fails, mark it as failed in the database
        if video:
            video.status = "failed"
            db.commit()
    finally:
        db.close()