# 🎬 ClipMind AI — Automated Video Summarization & Intelligence Platform

[![Frontend Deployed](https://img.shields.io/badge/Frontend-Vercel%20Live-brightgreen?logo=vercel)](https://clipmindai-nine.vercel.app)
[![Backend Deployed](https://img.shields.io/badge/Backend-Render%20Live-blue?logo=render)](https://clipmind-backend-94k5.onrender.com/docs)
[![Database PostgreSQL](https://img.shields.io/badge/PostgreSQL-Render-336791?logo=postgresql)](https://render.com)
[![Database MongoDB](https://img.shields.io/badge/MongoDB%20Atlas-Cloud-47A248?logo=mongodb)](https://mongodb.com)
[![Branch](https://img.shields.io/badge/GitHub%20Branch-Intern--SaiHarshith-orange?logo=github)](https://github.com/springboardmentor910069x-afk/AI-VIDEO-AUTOMATION-/tree/Intern-SaiHarshith)

ClipMind AI is a full-stack, AI-powered video intelligence and summarization platform designed to transform raw video content into actionable summaries, timestamped key moments, transcriptions, and interactive question-answering bots.

---

## 🚀 Live Production Links

| Service | Platform | Production URL |
| :--- | :--- | :--- |
| **Frontend Application** | **Vercel** | 🌐 **[https://clipmindai-nine.vercel.app](https://clipmindai-nine.vercel.app)** |
| **Backend API (Swagger Docs)** | **Render** | ⚡ **[https://clipmind-backend-94k5.onrender.com/docs](https://clipmind-backend-94k5.onrender.com/docs)** |
| **Backend Health Check** | **Render** | 🩺 **[https://clipmind-backend-94k5.onrender.com/api/health](https://clipmind-backend-94k5.onrender.com/api/health)** |
| **Mentor Git Repository** | **GitHub** | 📁 **[AI-VIDEO-AUTOMATION- (Intern-SaiHarshith)](https://github.com/springboardmentor910069x-afk/AI-VIDEO-AUTOMATION-/tree/Intern-SaiHarshith)** |

---

## 🔐 Pre-seeded Demo Accounts

Use any of the following accounts to log in directly:

| Role | Email | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin@clipmind.com` | `admin123` |
| **Learner / Student** | `learner@clipmind.com` | `learner123` |

*(New user registration is also enabled directly on the login page).*

---

## 🖥️ Studio Dashboard Layout

The studio dashboard follows an intuitive 3-column layout:

```text
┌──────────────┬───────────────────┬──────────────────────────┐
│ HISTORY      │ VIDEO PLAYBACK    │ AI SUMMARY               │
│              │                   │ TRANSCRIPT               │
│ Videos       │     ▶ VIDEO       │ KEY MOMENTS              │
│              │                   │ INSIGHTS                 │
│              │                   │                          │
│              │                   │                          │
│              │                   │              🤖 Ask AI  │ ← Floating Bot
└──────────────┴───────────────────┴──────────────────────────┘
```

1. **Left Column (History & Uploads)**: Browse processed videos, check transcription/summary status, and upload new videos or paste YouTube URLs.
2. **Middle Column (Video Playback)**: Custom video player with synchronized playback, seek controls, and metadata cards.
3. **Right Column (AI Studio)**:
   - **Executive Summary**: Comprehensive TL;DR and key takeaways.
   - **Full Transcript**: Timestamp-linked transcripts synchronized with video time.
   - **Key Moments**: Clickable timestamps jumping directly to critical video segments.
   - **Educational Insights**: Core topics, action items, and technical concepts.
   - **Ask AI Floating Bot**: Context-grounded Q&A bot answering any question about the video based strictly on its transcript.

---

## 🛠️ Architecture & Tech Stack

- **Frontend**: Next.js 15 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS, Lucide Icons.
- **Backend API**: FastAPI (Python 3.11), Uvicorn, Pydantic v2.
- **AI & Audio Processing**:
  - **OpenAI Whisper**: Speech-to-text transcription with fast language probing and FP32 CUDA GPU optimization.
  - **Google Gemini API**: Large Language Model for deep video summarization, insight synthesis, and Q&A chat.
  - **yt-dlp & FFmpeg**: High-speed video downloading and audio track extraction.
- **Data Tier (Dual-Database)**:
  - **PostgreSQL (Render Managed)**: Users, roles, authentication credentials, and video catalog metadata.
  - **MongoDB Atlas (Cloud Cluster)**: Transcripts, timestamped segments, structured AI summaries, and analytics.

---

## 📦 Local Development Setup

### 1. Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL & MongoDB

### 2. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate      # On Windows
source venv/bin/activate   # On Linux/macOS

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to interact with your local environment.

---

## 👨‍💻 Author
- **Developer / Intern**: Sai Harshith
- **Branch**: `Intern-SaiHarshith`
- **Program**: Springboard AI Video Automation Internship
