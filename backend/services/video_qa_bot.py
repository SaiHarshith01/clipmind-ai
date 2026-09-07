import os
import re
import json
from dotenv import load_dotenv

# Ensure .env is loaded from both backend and root paths
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv()

def format_seconds(seconds: float) -> str:
    """Formats float seconds into MM:SS string."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def parse_timestamps_from_text(text: str) -> list[float]:
    """
    Finds timestamp patterns like [01:23] or [1:23] in text and converts them to float seconds.
    """
    matches = re.findall(r'\[(\d{1,2}):(\d{2})\]', text)
    timestamps = []
    for m, s in matches:
        sec = int(m) * 60 + int(s)
        if sec not in timestamps:
            timestamps.append(float(sec))
    return sorted(timestamps)

CANDIDATE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash"
]

def answer_video_question(
    question: str,
    video_title: str,
    transcript: str,
    segments: list = None,
    summary_data: dict = None,
    metadata: dict = None
) -> dict:
    """
    Multimodal Video Assistant:
    Answers user questions about the video, its actors, singers, plot, or dialogue.
    Utilizes Google Gemini with candidate model fallback and local lexical retrieval.
    """
    summary_data = summary_data or {}
    metadata = metadata or {}
    segments = segments or []

    # 1. Format metadata context
    meta_lines = []
    if metadata.get("uploader"):
        meta_lines.append(f"Channel / Creator: {metadata['uploader']}")
    if metadata.get("artist"):
        meta_lines.append(f"Artist / Singer: {metadata['artist']}")
    if metadata.get("track"):
        meta_lines.append(f"Track: {metadata['track']}")
    if metadata.get("album"):
        meta_lines.append(f"Album: {metadata['album']}")
    if metadata.get("description"):
        # Include first 1500 chars of description (contains cast, singers, director credits)
        desc_snippet = metadata['description'][:1500].strip()
        meta_lines.append(f"Video Description & Credits:\n{desc_snippet}")

    meta_context = "\n".join(meta_lines) if meta_lines else "No external credits available (Uploaded local file)."

    # 2. Format transcript with timestamps
    if segments:
        ts_lines = []
        for s in segments[:60]: # Cap to first 60 segments to keep prompt fast and compact
            ts_str = format_seconds(s.get("start", 0.0))
            ts_lines.append(f"[{ts_str}] {s.get('text', '')}")
        transcript_with_ts = "\n".join(ts_lines)
    else:
        transcript_with_ts = transcript[:3000]

    # 3. Call Gemini with multi-model fallback if API Key is configured
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            prompt = f"""
            You are the ClipMind AI Video Assistant.
            Your role is to answer user questions about this video accurately, helpfully, and concisely.

            === VIDEO CONTEXT ===
            Title: {video_title}
            Source: {metadata.get('source', 'Uploaded Video')}

            === DESCRIPTION & CREDITS ===
            {meta_context}

            === EXECUTIVE & DETAILED SUMMARY ===
            Overview: {summary_data.get('short_summary', 'N/A')}
            Details: {summary_data.get('detailed_summary', 'N/A')}

            === SPEECH DIALOGUE / TRANSCRIPT (WITH TIMESTAMPS) ===
            {transcript_with_ts}

            === USER QUESTION ===
            "{question}"

            === INSTRUCTIONS ===
            1. If the user asks who is the singer, actor, artist, director, or creator:
               Look thoroughly at the Video Description & Credits section and dialogue. State the singer, actor, director, or cast explicitly.
            2. If the user asks what the video is about or what is being discussed:
               Provide a clear, engaging summary of the core topic, who is talking, and the key message.
            3. Whenever relevant, cite the timestamp in square brackets (e.g. [01:15]) so the user can seek directly to that moment.
            4. Keep answers conversational, crisp, and direct. Avoid repeating the prompt.
            """

            for model_name in CANDIDATE_MODELS:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    answer_text = response.text.strip()
                    citations = parse_timestamps_from_text(answer_text)

                    return {
                        "answer": answer_text,
                        "timestamp_citations": citations
                    }
                except Exception as model_err:
                    print(f"[VIDEO QA BOT] Model '{model_name}' failed: {model_err}. Trying next candidate...")

        except Exception as e:
            print(f"[VIDEO QA BOT] Gemini API setup error: {e}. Using fallback retriever...")

    # 4. Local Lexical Search Fallback (Offline Mode)
    q_lower = question.lower()
    fallback_answer = ""
    
    # Check for singer/actor/credits query
    if any(k in q_lower for k in ["singer", "actor", "artist", "who is", "cast", "creator", "channel", "director", "music"]):
        credits_found = []
        if metadata.get("description"):
            for line in metadata["description"].split("\n"):
                line_str = line.strip()
                if any(w in line_str.lower() for w in ["starring", "singer", "cast", "music", "actor", "directed", "song", "lyrics", "producer"]):
                    credits_found.append(line_str)
        if metadata.get("artist"):
            credits_found.insert(0, f"Artist/Singer: {metadata['artist']}")
        if metadata.get("uploader"):
            credits_found.append(f"Channel/Creator: {metadata['uploader']}")

        if credits_found:
            fallback_answer = "Found in video credits:\n" + "\n".join(credits_found[:6])

    # Check for "what is it about"
    if not fallback_answer and any(k in q_lower for k in ["what is", "about", "summary", "topic", "discuss"]):
        if summary_data.get("short_summary"):
            fallback_answer = f"This video is about: {summary_data.get('short_summary')}"
        elif transcript:
            fallback_answer = f"Summary of dialogue: {transcript[:250]}..."

    if not fallback_answer:
        fallback_answer = (
            f"Based on the transcript, the video discusses: '{summary_data.get('short_summary', video_title)}'."
        )

    citations = parse_timestamps_from_text(fallback_answer)
    return {
        "answer": fallback_answer,
        "timestamp_citations": citations
    }
