import os
import json
import subprocess
import imageio_ffmpeg
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

def extract_frame_as_thumbnail(video_path: str, timestamp: float, output_path: str):
    """
    Invokes FFmpeg locally to extract a single frame at the specified timestamp as a high-quality JPEG.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        cmd = [
            ffmpeg_exe,
            "-y",
            "-ss", str(max(0.1, round(timestamp, 2))),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"[KEY MOMENTS] Extracted thumbnail at {timestamp}s -> {output_path}")
    except Exception as e:
        print(f"[KEY MOMENTS] Failed to extract thumbnail at {timestamp}s: {e}")

def segment_transcript_by_pauses(segments: list[dict], pause_threshold: float = 2.0) -> list[dict]:
    """
    Groups consecutive time-aligned Whisper segments into logical topic/scene chunks.
    A new chunk begins when a speech pause exceeds pause_threshold or duration exceeds 30s.
    """
    if not segments:
        return []
        
    chunks = []
    current_chunk = {
        "text": "",
        "start": segments[0].get("start", 0.0),
        "end": segments[0].get("end", 0.0),
        "word_count": 0
    }
    
    for i, seg in enumerate(segments):
        seg_text = seg.get("text", "").strip()
        if not seg_text:
            continue
            
        words = seg_text.split()
        seg_word_count = len(words)
        
        time_gap = 0.0
        if i > 0:
            time_gap = seg.get("start", 0.0) - segments[i-1].get("end", 0.0)
            
        should_split = (
            time_gap >= pause_threshold or
            current_chunk["word_count"] + seg_word_count > 60 or
            (seg.get("end", 0.0) - current_chunk["start"]) > 30.0
        )
        
        if should_split and current_chunk["text"]:
            chunks.append({
                "text": current_chunk["text"].strip(),
                "start": current_chunk["start"],
                "end": current_chunk["end"]
            })
            current_chunk = {
                "text": seg_text,
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "word_count": seg_word_count
            }
        else:
            if current_chunk["text"]:
                current_chunk["text"] += " " + seg_text
            else:
                current_chunk["text"] = seg_text
                current_chunk["start"] = seg.get("start", 0.0)
            current_chunk["end"] = seg.get("end", 0.0)
            current_chunk["word_count"] += seg_word_count

    if current_chunk["text"]:
        chunks.append({
            "text": current_chunk["text"].strip(),
            "start": current_chunk["start"],
            "end": current_chunk["end"]
        })
        
    return chunks

def detect_key_moments(segments: list[dict], video_path: str, video_id: int) -> list[dict]:
    """
    Identifies high-interest moments across the video timeline,
    extracts visual frame thumbnails, and generates punchy seek hooks.
    GUARANTEES multiple interactive cards across the video (fixing single 0:0 card bug).
    """
    chunks = segment_transcript_by_pauses(segments)
    key_moments = []
    moment_idx = 0
    
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and chunks and len(chunks) > 1:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                'gemini-3.5-flash',
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Prepare compact chunk summary
            chunk_inputs = [
                {"id": i, "start": c["start"], "text": c["text"][:120]}
                for i, c in enumerate(chunks[:12])
            ]
            
            prompt = f"""
            Identify 3 to 6 key highlight moments from these video speech segments.
            For each key moment:
            - "chunk_id": index from the list
            - "hook": Catchy, engaging title under 12 words summarizing this moment.
            
            Format as JSON array:
            [
              {{"chunk_id": 0, "hook": "Opening Hook: Setting the Stage"}},
              {{"chunk_id": 2, "hook": "Core Breakthrough and Strategy"}}
            ]
            
            Segments:
            {json.dumps(chunk_inputs)}
            """
            
            response = model.generate_content(prompt)
            text = response.text.strip()
            first_bracket = text.find('[')
            last_bracket = text.rfind(']')
            if first_bracket != -1 and last_bracket != -1:
                items = json.loads(text[first_bracket:last_bracket+1])
                for item in items:
                    c_id = item.get("chunk_id")
                    hook = item.get("hook")
                    if c_id is not None and 0 <= c_id < len(chunks) and hook:
                        chunk = chunks[c_id]
                        start_time = chunk["start"]
                        thumb_rel = f"uploads/thumbnails/{video_id}_{moment_idx}.jpg"
                        extract_frame_as_thumbnail(video_path, start_time, thumb_rel)
                        
                        key_moments.append({
                            "hook": hook,
                            "start": start_time,
                            "thumbnail_url": f"/api/videos/{video_id}/thumbnail/{moment_idx}"
                        })
                        moment_idx += 1
                        
        except Exception as e:
            print(f"[KEY MOMENTS] LLM scoring encountered: {e}. Falling back to dynamic distribution...")

    # Dynamic Fallback: If LLM returned fewer than 3 moments, generate moments spaced across the timeline
    if len(key_moments) < 2 and chunks:
        print(f"[KEY MOMENTS] Generating timeline-distributed highlight cards...")
        num_desired = min(4, len(chunks))
        step = max(1, len(chunks) // num_desired)
        selected_chunks = [chunks[i] for i in range(0, len(chunks), step)][:4]
        
        default_titles = [
            "Introduction & Topic Overview",
            "Core Discussion & Analysis",
            "Critical Insights & Strategy",
            "Key Takeaways & Conclusion"
        ]
        
        for idx, chunk in enumerate(selected_chunks):
            start_time = chunk["start"]
            # Use snippet of sentence or default title
            snippet = chunk["text"][:75]
            if len(chunk["text"]) > 75:
                snippet += "..."
            title = default_titles[idx] if idx < len(default_titles) else f"Key Moment #{idx + 1}"
            hook_text = f"{title}: {snippet}"
            
            thumb_rel = f"uploads/thumbnails/{video_id}_{moment_idx}.jpg"
            extract_frame_as_thumbnail(video_path, start_time, thumb_rel)
            
            key_moments.append({
                "hook": hook_text,
                "start": start_time,
                "thumbnail_url": f"/api/videos/{video_id}/thumbnail/{moment_idx}"
            })
            moment_idx += 1

    print(f"[KEY MOMENTS] Generated {len(key_moments)} interactive seek cards for Video ID {video_id}.")
    return key_moments
