import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from core.database import get_db
from models.schema import Video, UserRole, User  # Added UserRole and User
from services.ai_worker import process_video_task
from core.security import get_current_user



# --- RBAC SECURITY GUARD ---
# --- UPGRADED RBAC SECURITY GUARD ---
def require_role(allowed_roles: list[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        # Convert everything to raw strings so it perfectly matches, no matter what Postgres returns
        user_role_str = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
        allowed_roles_str = [r.value for r in allowed_roles]
        
        print(f"🔒 GUARD CHECK -> User: {current_user.email} | Their Role: {user_role_str} | Allowed: {allowed_roles_str}")
        
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

# 2. Setup directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 3. Now define the route using the security guard
@router.post("/upload")
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # THIS IS THE NEW GUARD: It replaces user_id=1
    # Change it to exactly this:
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.EDUCATOR, UserRole.CREATOR]))
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
    
    # Check permissions (only owner or administrator can view status)
    user_role_str = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if video.owner_id != current_user.id and user_role_str != "Administrator":
        raise HTTPException(status_code=403, detail="Access Denied: You do not own this video.")
        
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
    
    # Check permissions (only owner or administrator can view transcript)
    user_role_str = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if video.owner_id != current_user.id and user_role_str != "Administrator":
        raise HTTPException(status_code=403, detail="Access Denied: You do not own this video.")
        
    # Fetch from MongoDB transcripts collection
    from core.database import mongo_db
    transcript_doc = mongo_db["transcripts"].find_one({"video_id": video.id})
    if not transcript_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if hasattr(status, 'HTTP_404_NOT_FOUND') else 404, 
            detail="Transcript not found or still processing. Please check status."
        )
        
    return {
        "video_id": video.id,
        "transcript": transcript_doc["transcript"]
    }
