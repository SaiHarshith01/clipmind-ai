import os
import re
import json
import subprocess
import imageio_ffmpeg
from dotenv import load_dotenv

# Load key from root .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

def extract_json_from_text(text: str):
    text = text.strip()
    first_brace = text.find('{')
    first_bracket = text.find('[')
    
    start_idx = -1
    end_char = ''
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
        end_char = '}'
    elif first_bracket != -1:
        start_idx = first_bracket
        end_char = ']'
        
    if start_idx == -1:
        raise ValueError("No JSON structure found in text: " + repr(text))
        
    end_idx = text.rfind(end_char)
    if end_idx == -1:
        raise ValueError("No closing JSON bracket found in text.")
        
    return json.loads(text[start_idx:end_idx+1])


def segment_transcript_by_pauses(segments: list[dict], pause_threshold: float = 2.0) -> list[dict]:
    """
    Groups time-aligned Whisper segments into scene/topic chunks.
    A new chunk starts when a silence pause exceeds the threshold, or word/time limits are reached.
    """
    if not segments:
        return []
        
    chunks = []
    current_chunk = {
        "text": "",
        "start": segments[0]["start"],
        "end": segments[0]["end"],
        "word_count": 0
    }
    
    for i, seg in enumerate(segments):
        seg_text = seg.get("text", "").strip()
        if not seg_text:
            continue
            
        words = seg_text.split()
        seg_word_count = len(words)
        
        # Determine if we should start a new chunk
        time_gap = 0.0
        if i > 0:
            time_gap = seg["start"] - segments[i-1]["end"]
            
        should_split = (
            time_gap >= pause_threshold or
            current_chunk["word_count"] + seg_word_count > 80 or
            (seg["end"] - current_chunk["start"]) > 35.0
        )
        
        if should_split and current_chunk["text"]:
            chunks.append({
                "text": current_chunk["text"].strip(),
                "start": current_chunk["start"],
                "end": current_chunk["end"]
            })
            # Start new chunk
            current_chunk = {
                "text": seg_text,
                "start": seg["start"],
                "end": seg["end"],
                "word_count": seg_word_count
            }
        else:
            # Append to current chunk
            if current_chunk["text"]:
                current_chunk["text"] += " " + seg_text
            else:
                current_chunk["text"] = seg_text
                current_chunk["start"] = seg["start"]
            current_chunk["end"] = seg["end"]
            current_chunk["word_count"] += seg_word_count

    if current_chunk["text"]:
        chunks.append({
            "text": current_chunk["text"].strip(),
            "start": current_chunk["start"],
            "end": current_chunk["end"]
        })
        
    return chunks

def extract_frame_as_thumbnail(video_path: str, timestamp: float, output_path: str):
    """
    Invokes FFmpeg locally using imageio_ffmpeg to extract a single frame 
    at the specified timestamp and save it as a high-quality JPEG.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        # FFmpeg command to extract one frame at -ss timestamp
        cmd = [
            ffmpeg_exe,
            "-y",
            "-ss", str(round(timestamp, 2)),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",  # High quality
            output_path
        ]
        
        # Run process silently
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"[THUMBNAIL] Extracted frame at {timestamp}s to {output_path}")
    except Exception as e:
        print(f"[THUMBNAIL] Error extracting frame: {e}")

def score_and_extract_hooks(chunks: list[dict], api_key: str) -> list[dict]:
    """
    Chains chunks into a single batch query to Gemini API.
    Scores each chunk 1-10, and generates synthesized hooks under 15 words for scores >= 8.
    """
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    # Configure model to output JSON
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    You are an expert Content Strategist and Evaluator for ClipMind.
    Analyze the following list of transcription chunks.
    
    For each chunk:
    1. Score the chunk from 1-10 on its interest level, emotional hook potential, or actionable advice.
    2. If the score is 8 or higher, synthesize the text into a punchy, relatable, and highly engaging "hook" (key moment).
    
    CRITICAL RULES FOR HOOKS:
    - Keep it under 15 words.
    - DO NOT use direct word-for-word copy from the text.
    - Translate dry details into conversational, punchy concepts.
    
    Respond strictly with a JSON array of objects.
    Format:
    [
      {{"chunk_id": 0, "score": 9, "hook": "Embracing failure: The real cost of starting in public."}},
      {{"chunk_id": 1, "score": 4, "hook": null}}
    ]
    
    Here are the chunks:
    {json.dumps(chunks, indent=2)}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        results = extract_json_from_text(text)
        return results
    except Exception as e:
        print(f"[LLM SUMMARIZER] Error in scoring and hook generation: {e}")
        return []

def generate_advanced_summary(transcript_text: str, segments: list[dict], video_id: int, video_path: str) -> dict:
    """
    Advanced entry point:
    Generates a full AI overview, extracts key moments with start timestamps and visual thumbnails.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    
    # 1. Generate Executive and Detailed Thematic Summary (AI Content Editor)
    summary_prompt = f"""
    You are an expert AI Content Editor for ClipMind. Your task is to process a raw [VIDEO TRANSCRIPT] and generate two levels of abstractive summaries.

    ### CRITICAL RULES FOR ABSTRACTION:
    1. NO COPY-PASTING: Do not extract or repeat literal sentences from the transcript. You must synthesize the meaning and write it in your own words.
    2. THEMATIC, NOT CHRONOLOGICAL: Do not summarize by saying "First the speaker says X, then they say Y." Instead, group the information by core themes and concepts.
    3. CLEAR AND ENGAGING: Use a professional but conversational tone.

    ### REQUIRED OUTPUT JSON SCHEMA:
    {{
      "short_summary": "A punchy, 2-to-3 sentence hook. Tell the reader exactly what value they will get from watching this video. Make it engaging.",
      "detailed_summary": "A comprehensive breakdown of the video's core arguments. Use Markdown bullet points and bold text to make it readable. Synthesize the context deeply.",
      "keywords": ["5 to 6 extracted tag strings based on concepts"]
    }}

    Respond STRICTLY in the above JSON format.
    """
    summary_data = {
        "short_summary": "No summary generated.",
        "detailed_summary": "No detailed breakdown available.",
        "keywords": []
    }
    
    try:
        response = model.generate_content(summary_prompt + f"\n\nTranscript:\n{transcript_text}")
        text = response.text.strip()
        parsed = extract_json_from_text(text)
        summary_data["short_summary"] = parsed.get("short_summary", "")
        
        detailed = parsed.get("detailed_summary", "")
        if isinstance(detailed, list):
            detailed = "\n".join(detailed)
        summary_data["detailed_summary"] = detailed
        
        summary_data["keywords"] = parsed.get("keywords", [])
    except Exception as e:
        print(f"[LLM SUMMARIZER] Executive Summary failed: {e}")
        raise e
        
    # 2. Topic Segmentation
    chunks = segment_transcript_by_pauses(segments)
    
    # 3. Batch Scoring and Moment extraction
    moments_results = score_and_extract_hooks(chunks, api_key)
    
    key_takeaways = []
    
    # 4. Filter, Extract, and map timestamps
    moment_idx = 0
    for res in moments_results:
        chunk_id = res.get("chunk_id")
        score = res.get("score", 0)
        hook = res.get("hook")
        
        if score >= 8 and hook and chunk_id is not None and chunk_id < len(chunks):
            chunk = chunks[chunk_id]
            start_time = chunk["start"]
            
            # Save visual thumbnail at uploads/thumbnails/{video_id}_{moment_idx}.jpg
            thumb_rel_path = f"uploads/thumbnails/{video_id}_{moment_idx}.jpg"
            extract_frame_as_thumbnail(video_path, start_time, thumb_rel_path)
            
            key_takeaways.append({
                "hook": hook,
                "start": start_time,
                "thumbnail_url": f"/api/videos/{video_id}/thumbnail/{moment_idx}"
            })
            moment_idx += 1
            
    # Default if no high score moment is found
    if not key_takeaways and chunks:
        # Fallback to the first chunk as key moment
        start_time = chunks[0]["start"]
        thumb_rel_path = f"uploads/thumbnails/{video_id}_0.jpg"
        extract_frame_as_thumbnail(video_path, start_time, thumb_rel_path)
        key_takeaways.append({
            "hook": "Key moments and highlights of the video.",
            "start": start_time,
            "thumbnail_url": f"/api/videos/{video_id}/thumbnail/0"
        })
        
    return {
        "short_summary": summary_data["short_summary"],
        "detailed_summary": summary_data["detailed_summary"],
        "key_takeaways": key_takeaways, # Now a list of dicts: {"hook": str, "start": float, "thumbnail_url": str}
        "keywords": summary_data["keywords"],
        "word_count": len(transcript_text.split())
    }
