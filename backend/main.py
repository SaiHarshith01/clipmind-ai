import os
from dotenv import load_dotenv

# Ensure environment variables are loaded regardless of current working directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth, videos

app = FastAPI(
    title="ClipMind AI API",
    description="Video Summarization Platform API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routing endpoints
app.include_router(auth.router)
app.include_router(videos.router)

@app.get("/api/health")
def check_health():
    return {"status": "success", "message": "Backend is securely connected to the Frontend!"}