import os
from core.database import SessionLocal, mongo_db
from models.schema import Video

# Import modular services
from services.audio_extractor import extract_audio, ensure_browser_compatible_video
from services.transcriber import transcribe_audio
from services.summarizer import generate_abstractive_summary
from services.key_moments import detect_key_moments
from services.content_insights import extract_content_insights
from services.analytics import calculate_video_analytics
from services.youtube_downloader import download_youtube_video

def process_video_task(video_id: int, metadata: dict = None):
    """
    Modular AI Pipeline Orchestrator:
    Coordinates audio extraction, CUDA Whisper transcription, Gemini summaries,
    key moments detection with visual thumbnails, content insights, and analytics.
    """
    print(f"[AI PIPELINE] Starting end-to-end processing for Video ID: {video_id}")
    if metadata is None:
        metadata = {
            "description": "User uploaded local video file.",
            "source": "local_upload"
        }
    
    db = SessionLocal()
    video = None
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            print(f"[AI PIPELINE] Error: Video ID {video_id} not found in database!")
            return

        # 1. File Paths Setup (Absolute path to guarantee location)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_dir = os.path.join(backend_dir, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        video_path = os.path.join(upload_dir, video.filename)
        audio_filename = video.filename.rsplit('.', 1)[0] + ".mp3"
        audio_path = os.path.join(upload_dir, audio_filename)

        # 2. Standardize Video & Audio for Web Browsers (AAC transcode)
        print(f"[AI PIPELINE] 1/6 Standardizing video and checking browser audio...")
        ensure_browser_compatible_video(video_path)

        # 3. Extract Audio Track
        print(f"[AI PIPELINE] 2/6 Extracting audio track to {audio_filename}...")
        extract_audio(video_path, audio_path)

        # Update status in PostgreSQL to transcribing
        video.status = "transcribing"
        db.commit()

        # 4. Transcribe Audio with Whisper (CUDA GPU accelerated)
        print(f"[AI PIPELINE] 3/6 Running Whisper speech-to-text...")
        transcript_text, segments_list = transcribe_audio(audio_path)

        # Update status in PostgreSQL to summarizing
        video.status = "summarizing"
        db.commit()

        # 5. Generate Two-Level Abstractive Summaries
        print(f"[AI PIPELINE] 4/6 Generating Executive & Detailed Thematic Summaries...")
        summary_result = generate_abstractive_summary(transcript_text)
        short_summary = summary_result.get("short_summary", "")
        detailed_summary = summary_result.get("detailed_summary", "")

        # 6. Detect Key Moments & Extract Visual Thumbnails
        print(f"[AI PIPELINE] 5/6 Detecting Key Moments and extracting thumbnails...")
        key_moments = detect_key_moments(segments_list, video_path, video.id)

        # 7. Extract Content Insights (Sentiment & Topics) & Calculate Analytics
        print(f"[AI PIPELINE] 6/6 Extracting sentiment tone and calculating analytics...")
        insights = extract_content_insights(transcript_text)
        analytics = calculate_video_analytics(transcript_text, segments_list)

        # 8. Persist All Intelligence Data to MongoDB
        collection = mongo_db["transcripts_and_summaries"]
        collection.update_one(
            {"video_id": video.id},
            {
                "$set": {
                    "video_id": video.id,
                    "filename": video.filename,
                    "transcript": transcript_text,
                    "segments": segments_list,
                    "short_summary": short_summary,
                    "detailed_summary": detailed_summary,
                    "key_takeaways": key_moments,       # List of {"hook", "start", "thumbnail_url"}
                    "keywords": insights.get("keywords", []),
                    "sentiment": insights.get("sentiment", "Educational"),
                    "tone": insights.get("tone", "Informative"),
                    "key_entities": insights.get("key_entities", []),
                    "analytics": analytics,             # {"duration_seconds", "speaking_wpm", "reading_time_minutes", ...}
                    "metadata": metadata,               # {"description", "uploader", "artist", "track", ...}
                    "word_count": analytics.get("word_count", 0)
                }
            },
            upsert=True
        )
        print(f"[AI PIPELINE] MongoDB document saved successfully for Video ID: {video.id}!")

        # 9. Mark PostgreSQL state as completed
        video.status = "completed"
        db.commit()
        print(f"[AI PIPELINE] Video processing finished successfully for Video ID: {video.id}!")
        
    except Exception as e:
        print(f"[AI PIPELINE] Error during processing pipeline for Video ID {video_id}: {e}")
        import traceback
        traceback.print_exc()
        if video:
            video.status = "failed"
            db.commit()
    finally:
        db.close()

def process_youtube_video_task(video_id: int, youtube_url: str):
    """
    Background worker task that downloads the YouTube video,
    ensures AAC audio compatibility, and hands off to the main AI processing pipeline.
    """
    print(f"[YOUTUBE WORKER] Ingesting YouTube video: {youtube_url} (Video ID: {video_id})")
    
    db = SessionLocal()
    video = None
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            print(f"[YOUTUBE WORKER] Video ID {video_id} not found!")
            return
            
        # 1. Download YouTube Video with AAC audio into absolute upload_dir
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_dir = os.path.join(backend_dir, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        download_info = download_youtube_video(youtube_url, upload_dir)
        
        # 2. Update PostgreSQL record with filename & title
        video.filename = download_info["filename"]
        video.title = download_info["title"]
        video.status = "processing"
        db.commit()
        
        print(f"[YOUTUBE WORKER] Downloaded '{video.title}' -> {video.filename}. Starting AI Pipeline...")
        db.close()
        
        # 3. Process via standard pipeline with rich YouTube metadata
        process_video_task(video_id, metadata=download_info.get("metadata", {}))
        
    except Exception as e:
        print(f"[YOUTUBE WORKER] Error during YouTube video task: {e}")
        import traceback
        traceback.print_exc()
        if video:
            try:
                video.status = "failed"
                db.commit()
            except Exception:
                pass
    finally:
        try:
            db.close()
        except Exception:
            pass