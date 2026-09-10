import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.database import get_db
from models.schema import Video, UserRole, User  # Added UserRole and User
from services.ai_worker import process_video_task, process_youtube_video_task
from core.security import get_current_user




# --- RBAC SECURITY GUARD ---
# --- UPGRADED RBAC SECURITY GUARD ---
def require_role(allowed_roles: list[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        # Convert everything to raw strings so it perfectly matches, no matter what Postgres returns
        user_role_str = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
        allowed_roles_str = [r.value for r in allowed_roles]
        
        print(f"[GUARD CHECK] User: {current_user.email} | Their Role: {user_role_str} | Allowed: {allowed_roles_str}")
        
        if user_role_str not in allowed_roles_str:
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Your role ({user_role_str}) does not have permission."
            )
        return current_user
    return role_checker
# ------------------------------------
# ---------------------------

# 1. Define the router FIRST
router = APIRouter(prefix="/api/videos", tags=["Videos"])

# 2. Setup absolute directory
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 2.1 List Videos Endpoint (Secured)
@router.get("/")
def list_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_role_str = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if user_role_str == "Administrator":
        videos = db.query(Video).order_by(Video.id.desc()).all()
    else:
        # Allow all roles to view completed videos (shared learning catalog) or their own uploads
        videos = db.query(Video).filter(
            (Video.status == "completed") | (Video.owner_id == current_user.id)
        ).order_by(Video.id.desc()).all()
        
    return [{
        "id": v.id,
        "title": v.title,
        "filename": v.filename,
        "status": v.status,
        "uploaded_at": v.uploaded_at
    } for v in videos]

# 3. Now define the route using the security guard
@router.post("/upload")
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # THIS IS THE NEW GUARD: It replaces user_id=1
    # Change it to exactly this:
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.EDUCATOR, UserRole.CREATOR, UserRole.LEARNER]))
):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video format.")
        
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    new_video = Video(
        title=file.filename,
        filename=file.filename,
        status="processing",
        # Use the real authenticated user's ID now!
        owner_id=current_user.id 
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    
    print(f"DEBUG: Attempting to trigger background task for Video ID: {new_video.id}")

    # Trigger background worker
    background_tasks.add_task(process_video_task, new_video.id)
    
    return {
        "message": "Video uploaded and processing started!", 
        "video_id": new_video.id
    }

class YouTubePayload(BaseModel):
    url: str

@router.post("/youtube")
def import_youtube_video(
    payload: YouTubePayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.EDUCATOR, UserRole.CREATOR, UserRole.LEARNER]))
):
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="YouTube URL cannot be empty.")
        
    # Basic URL sanity check
    if "youtube.com" not in url and "youtu.be" not in url:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL. Must contain youtube.com or youtu.be")

    # Create postgres record in downloading status
    new_video = Video(
        title="YouTube Ingestion",
        filename="pending",
        status="downloading",
        owner_id=current_user.id
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    print(f"[YOUTUBE API] Spawning background download/process task for Video ID: {new_video.id}")
    
    # Spawn background task
    background_tasks.add_task(process_youtube_video_task, new_video.id, url)

    return {
        "message": "YouTube download queued successfully!",
        "video_id": new_video.id
    }

# 4. Get Video Status Endpoint
@router.get("/{video_id}")
def get_video_status(
    video_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check permissions (allow owners, administrators, or if the video is completed)
    user_role_str = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if video.owner_id != current_user.id and video.status != "completed" and user_role_str != "Administrator":
        raise HTTPException(status_code=403, detail="Access Denied: You do not own this video and it is not completed.")
        
    return {
        "id": video.id,
        "title": video.title,
        "status": video.status,
        "filename": video.filename
    }

# 5. Get Video Transcript Endpoint
@router.get("/{video_id}/transcript")
def get_video_transcript(
    video_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check permissions (allow owners, administrators, or if the video is completed)
    user_role_str = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if video.owner_id != current_user.id and video.status != "completed" and user_role_str != "Administrator":
        raise HTTPException(status_code=403, detail="Access Denied: You do not own this video and it is not completed.")
        
    # Fetch from MongoDB
    from core.database import mongo_db
    doc = mongo_db["transcripts_and_summaries"].find_one({"video_id": video.id})
    if not doc or "transcript" not in doc:
        raise HTTPException(
            status_code=404, 
            detail="Transcript not found or still processing. Please check status."
        )
        
    return {
        "video_id": video.id,
        "filename": video.filename,
        "transcript": doc["transcript"],
        "segments": doc.get("segments", [])
    }

# 6. Get Video Summary Endpoint
@router.get("/{video_id}/summary")
def get_video_summary(
    video_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check permissions (allow owners, administrators, or if the video is completed)
    user_role_str = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if video.owner_id != current_user.id and video.status != "completed" and user_role_str != "Administrator":
        raise HTTPException(status_code=403, detail="Access Denied: You do not own this video and it is not completed.")
        
    # Fetch from MongoDB
    from core.database import mongo_db
    doc = mongo_db["transcripts_and_summaries"].find_one({"video_id": video.id})
    if not doc or "short_summary" not in doc:
        raise HTTPException(
            status_code=404, 
            detail="Summary not found or still processing. Please check status."
        )
        
    return {
        "video_id": video.id,
        "filename": video.filename,
        "short_summary": doc.get("short_summary", ""),
        "detailed_summary": doc.get("detailed_summary", ""),
        "key_takeaways": doc.get("key_takeaways", []),
        "keywords": doc.get("keywords", []),
        "sentiment": doc.get("sentiment", "Educational"),
        "tone": doc.get("tone", "Informative"),
        "key_entities": doc.get("key_entities", []),
        "analytics": doc.get("analytics", {
            "duration_seconds": 0.0,
            "speaking_wpm": 130,
            "reading_time_minutes": 1,
            "time_saved_minutes": 0.5,
            "pacing_label": "Steady"
        }),
        "metadata": doc.get("metadata", {}),
        "word_count": doc.get("word_count", 0)
    }

from pydantic import BaseModel
from fastapi.responses import PlainTextResponse, StreamingResponse
from services.exporter import export_to_txt, export_to_docx
from services.video_qa_bot import answer_video_question

class ChatRequest(BaseModel):
    question: str

# 6.0 Video Q&A Assistant Chatbot Endpoint ("Chat with Video")
@router.post("/{video_id}/chat")
def chat_with_video(
    video_id: int,
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    from core.database import mongo_db
    doc = mongo_db["transcripts_and_summaries"].find_one({"video_id": video.id})
    if not doc:
        raise HTTPException(status_code=404, detail="Video intelligence not found. Processing may still be in progress.")
        
    result = answer_video_question(
        question=req.question,
        video_title=video.title or video.filename,
        transcript=doc.get("transcript", ""),
        segments=doc.get("segments", []),
        summary_data={
            "short_summary": doc.get("short_summary", ""),
            "detailed_summary": doc.get("detailed_summary", ""),
            "key_takeaways": doc.get("key_takeaways", [])
        },
        metadata=doc.get("metadata", {})
    )
    
    return {
        "question": req.question,
        "answer": result["answer"],
        "timestamp_citations": result["timestamp_citations"]
    }

# 6.1 Export Video Summary & Transcript as Plain Text
@router.get("/{video_id}/export/txt")
def export_video_txt(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    from core.database import mongo_db
    doc = mongo_db["transcripts_and_summaries"].find_one({"video_id": video.id})
    if not doc:
        raise HTTPException(status_code=404, detail="No transcription found")
        
    txt_content = export_to_txt(
        title=video.title or video.filename,
        short_summary=doc.get("short_summary", ""),
        detailed_summary=doc.get("detailed_summary", ""),
        transcript=doc.get("transcript", ""),
        key_moments=doc.get("key_takeaways", []),
        insights={"sentiment": doc.get("sentiment"), "tone": doc.get("tone"), "keywords": doc.get("keywords", [])}
    )
    
    headers = {"Content-Disposition": f"attachment; filename=clipmind_{video_id}.txt"}
    return PlainTextResponse(content=txt_content, headers=headers)

# 6.2 Export Video Summary as Word Document (.docx)
@router.get("/{video_id}/export/docx")
def export_video_docx(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    from core.database import mongo_db
    doc = mongo_db["transcripts_and_summaries"].find_one({"video_id": video.id})
    if not doc:
        raise HTTPException(status_code=404, detail="No transcription found")
        
    docx_buf = export_to_docx(
        title=video.title or video.filename,
        short_summary=doc.get("short_summary", ""),
        detailed_summary=doc.get("detailed_summary", ""),
        transcript=doc.get("transcript", ""),
        key_moments=doc.get("key_takeaways", []),
        insights={"sentiment": doc.get("sentiment"), "tone": doc.get("tone"), "keywords": doc.get("keywords", [])}
    )
    
    headers = {
        "Content-Disposition": f"attachment; filename=clipmind_report_{video_id}.docx"
    }
    return StreamingResponse(
        docx_buf, 
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers
    )

# 6.3 Export Structured JSON Data
@router.get("/{video_id}/export/json")
def export_video_json(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    from core.database import mongo_db
    doc = mongo_db["transcripts_and_summaries"].find_one({"video_id": video.id})
    if not doc:
        raise HTTPException(status_code=404, detail="No transcription found")
        
    doc_copy = dict(doc)
    if "_id" in doc_copy:
        doc_copy["_id"] = str(doc_copy["_id"])
        
    return {
        "status": "success",
        "video": {
            "id": video.id,
            "title": video.title,
            "filename": video.filename,
            "status": video.status
        },
        "intelligence": doc_copy
    }

# 6.4 Bookmarking endpoints
@router.post("/{video_id}/bookmark")
def toggle_bookmark(
    video_id: int,
    current_user: User = Depends(get_current_user)
):
    from core.database import mongo_db
    existing = mongo_db["user_bookmarks"].find_one({"user_id": current_user.id, "video_id": video_id})
    if existing:
        mongo_db["user_bookmarks"].delete_one({"user_id": current_user.id, "video_id": video_id})
        return {"bookmarked": False, "message": "Bookmark removed"}
    else:
        mongo_db["user_bookmarks"].insert_one({"user_id": current_user.id, "video_id": video_id})
        return {"bookmarked": True, "message": "Video bookmarked successfully"}

@router.get("/{video_id}/is_bookmarked")
def check_is_bookmarked(
    video_id: int,
    current_user: User = Depends(get_current_user)
):
    from core.database import mongo_db
    existing = mongo_db["user_bookmarks"].find_one({"user_id": current_user.id, "video_id": video_id})
    return {"bookmarked": bool(existing)}

# 7. Streaming Video Player Endpoint (Secured by Query Token)
from fastapi.responses import FileResponse
from core.security import SECRET_KEY, ALGORITHM
import jwt

@router.get("/{video_id}/stream")
def stream_video(
    video_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    try:
        # Decode token passed as a query param since HTML5 video tags can't send auth headers
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User account not found")
        
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    user_role_str = user.role.value if hasattr(user.role, "value") else user.role
    if video.owner_id != user.id and video.status != "completed" and user_role_str != "Administrator":
        raise HTTPException(status_code=403, detail="Access Denied: You do not own this video and it is not completed.")
        
    video_path = f"{UPLOAD_DIR}/{video.filename}"
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")
        
    return FileResponse(video_path, media_type="video/mp4")

# 7.1 Serve visual moment thumbnail (Secured by query token)
@router.get("/{video_id}/thumbnail/{moment_idx}")
def get_video_moment_thumbnail(
    video_id: int,
    moment_idx: int,
    token: str,
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User account not found")
        
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    user_role_str = user.role.value if hasattr(user.role, "value") else user.role
    if video.owner_id != user.id and video.status != "completed" and user_role_str != "Administrator":
        raise HTTPException(status_code=403, detail="Access Denied: You do not own this video and it is not completed.")
        
    thumbnail_path = f"uploads/thumbnails/{video_id}_{moment_idx}.jpg"
    if not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
        
    return FileResponse(thumbnail_path, media_type="image/jpeg")

# 8. Delete Video & AI Data Endpoint (Secured)
@router.delete("/{video_id}")
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    user_role_str = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if video.owner_id != current_user.id and user_role_str != "Administrator":
        raise HTTPException(status_code=403, detail="Access Denied: You do not own this video.")
        
    # 1. Delete physical files from disk
    video_path = f"{UPLOAD_DIR}/{video.filename}"
    audio_filename = video.filename.rsplit('.', 1)[0] + ".mp3"
    audio_path = f"{UPLOAD_DIR}/{audio_filename}"
    
    try:
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        # Clean up moment thumbnails from disk
        thumb_dir = "uploads/thumbnails"
        if os.path.exists(thumb_dir):
            for file_name in os.listdir(thumb_dir):
                if file_name.startswith(f"{video.id}_") and file_name.endswith(".jpg"):
                    os.remove(os.path.join(thumb_dir, file_name))
    except Exception as e:
        print(f"[API] Error deleting files from disk for Video ID {video.id}: {e}")
        
    # 2. Delete NoSQL document from MongoDB
    from core.database import mongo_db
    mongo_db["transcripts_and_summaries"].delete_one({"video_id": video.id})
    
    # 3. Delete relational SQL record from PostgreSQL
    db.delete(video)
    db.commit()
    
    return {"status": "success", "message": "Video file and all AI transcription records deleted successfully."}




