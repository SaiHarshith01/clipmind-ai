import os
from dotenv import load_dotenv

# Ensure environment variables are loaded regardless of current working directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth, videos
from core.database import engine, SessionLocal
from models.schema import Base, User, UserRole
from core.security import get_password_hash

app = FastAPI(
    title="ClipMind AI API",
    description="Video Summarization Platform API"
)

# Configure CORS: allow localhost + any Vercel deployment URL
frontend_url = os.getenv("FRONTEND_URL", "").strip()
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if frontend_url:
    allowed_origins.append(frontend_url)
    if frontend_url.endswith("/"):
        allowed_origins.append(frontend_url[:-1])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("ALLOW_ALL_CORS", "true").lower() == "true" else allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # 1. Automatically create PostgreSQL tables if they do not exist
    try:
        Base.metadata.create_all(bind=engine)
        print("[STARTUP] PostgreSQL database tables initialized successfully.")
    except Exception as e:
        print(f"[STARTUP] Notice initializing tables: {e}")

    # 2. Seed initial demo users if not present
    try:
        db = SessionLocal()
        admin_email = "admin@clipmind.com"
        if not db.query(User).filter(User.email == admin_email).first():
            admin = User(
                email=admin_email,
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN
            )
            db.add(admin)
            
        learner_email = "learner@clipmind.com"
        if not db.query(User).filter(User.email == learner_email).first():
            learner = User(
                email=learner_email,
                hashed_password=get_password_hash("learner123"),
                role=UserRole.LEARNER
            )
            db.add(learner)

        db.commit()
        db.close()
        print("[STARTUP] Default admin and learner accounts ready.")
    except Exception as e:
        print(f"[STARTUP] Notice seeding demo users: {e}")

# Include the routing endpoints
app.include_router(auth.router)
app.include_router(videos.router)

@app.get("/api/health")
def check_health():
    return {"status": "success", "message": "ClipMind Backend is live and healthy!"}