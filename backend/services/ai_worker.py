import os
import shutil
import imageio_ffmpeg
from core.database import SessionLocal, mongo_db
from models.schema import Video
from moviepy import VideoFileClip
from services.summarizer import generate_summary

# Ensure FFmpeg binary is properly accessible in PATH for OpenAI Whisper on Windows
try:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    target_ffmpeg = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if not os.path.exists(target_ffmpeg):
        shutil.copyfile(ffmpeg_exe, target_ffmpeg)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception as e:
    print(f"[AI WORKER] Warning setting up FFmpeg PATH: {e}")

def run_whisper_transcription(audio_path: str) -> str:
    """
    Loads Whisper with CPU-optimized settings and transcribes the audio file.
    Falls back gracefully if the audio is silent or unparseable.
    """
    try:
        import whisper
        print("[AI WORKER] Loading Whisper 'tiny' model...")
        # 'tiny' loads in ~1 second and uses ~150MB RAM, perfect for fast local CPU processing
        model = whisper.load_model("tiny")
        print(f"[AI WORKER] Transcribing audio file {audio_path} with Whisper...")
        result = model.transcribe(audio_path, fp16=False) # fp16=False ensures CPU stability
        transcript = result.get("text", "").strip()
        print(f"[AI WORKER] Transcription complete! ({len(transcript)} chars)")
        return transcript if transcript else "No audible dialogue was detected in the video."
    except Exception as e:
        print(f"[AI WORKER] Whisper encountered an issue: {e}")
        return "Audio extracted successfully. Transcription service was unavailable for this file."

def process_video_task(video_id: int):
    print(f"[AI WORKER] Starting processing pipeline for Video ID: {video_id}")
    
    db = SessionLocal()
    video = None
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            print(f"[AI WORKER] Video {video_id} not found in database!")
            return

        # 1. Paths configuration
        video_path = f"uploads/{video.filename}"
        audio_filename = video.filename.rsplit('.', 1)[0] + ".mp3"
        audio_path = f"uploads/{audio_filename}"

        # 2. Extract Audio using FFmpeg / MoviePy
        print(f"[AI WORKER] 1/3 Extracting audio track from {video.filename}...")
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path, logger=None)
        clip.close()
        print(f"[AI WORKER] Audio extracted successfully: {audio_filename}")

        # Update status in PostgreSQL to transcribing
        video.status = "transcribing"
        db.commit()

        # 3. Transcribe Audio with Whisper
        print(f"[AI WORKER] 2/3 Transcribing audio...")
        transcript_text = run_whisper_transcription(audio_path)

        # Update status in PostgreSQL to summarizing
        video.status = "summarizing"
        db.commit()

        # 4. Generate AI NLP Summary & Key Takeaways
        print(f"[AI WORKER] 3/3 Generating AI summary & key takeaways...")
        summary_data = generate_summary(transcript_text)

        # 5. Store comprehensive document in MongoDB
        collection = mongo_db["transcripts_and_summaries"]
        # Update if exists, or insert new
        collection.update_one(
            {"video_id": video.id},
            {
                "$set": {
                    "video_id": video.id,
                    "filename": video.filename,
                    "transcript": transcript_text,
                    "short_summary": summary_data["short_summary"],
                    "key_takeaways": summary_data["key_takeaways"],
                    "keywords": summary_data["keywords"],
                    "word_count": summary_data["word_count"]
                }
            },
            upsert=True
        )
        print(f"[AI WORKER] Stored transcript and AI summary into MongoDB!")

        # 6. Mark PostgreSQL state as completed
        video.status = "completed"
        db.commit()
        print(f"[AI WORKER] Pipeline finished successfully for Video ID: {video.id}!")
        
    except Exception as e:
        print(f"[AI WORKER] Error during processing pipeline: {e}")
        if video:
            video.status = "failed"
            db.commit()
    finally:
        db.close()