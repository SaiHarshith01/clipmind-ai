import os
import re
import json
from collections import Counter
from dotenv import load_dotenv

# Load env variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def split_sentences(text: str) -> list[str]:
    # Split by periods, exclamation marks, or question marks
    sentences = re.split(r'(?<=[.!?]) +', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]

def generate_heuristic_summary(transcript_text: str) -> dict:
    """
    Local extractive sentence-ranking algorithm (works completely offline without any API key).
    """
    cleaned = clean_text(transcript_text)
    words = cleaned.split()
    word_count = len(words)
    
    if not cleaned or word_count < 10:
        return {
            "short_summary": cleaned or "No substantial speech detected to summarize.",
            "detailed_summary": "Audio was brief or contained minimal dialogue."
        }

    sentences = split_sentences(cleaned)
    
    # If the transcript is very short (1-3 sentences)
    if len(sentences) <= 3:
        return {
            "short_summary": cleaned,
            "detailed_summary": "\n".join([f"* {s}" for s in sentences if s])
        }

    stop_words = {
        'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'to', 'for', 'of', 'or', 
        'by', 'with', 'from', 'this', 'that', 'it', 'you', 'we', 'they', 'i', 'he', 'she',
        'was', 'are', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'so', 'can', 'will',
        'just', 'about', 'like', 'there', 'what', 'all', 'would', 'up', 'out', 'if'
    }
    
    words_filtered = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', cleaned.lower()) if w not in stop_words]
    word_freq = Counter(words_filtered)
    sentence_scores = {}
    
    for i, sentence in enumerate(sentences):
        score = 0
        sentence_words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
        for word in sentence_words:
            score += word_freq.get(word, 0)
        
        normalized_score = score / (len(sentence_words) + 1)
        if i == 0:
            normalized_score *= 1.3
        elif i == len(sentences) - 1:
            normalized_score *= 1.15
            
        sentence_scores[i] = normalized_score

    # Top 2 sentences for Executive hook
    top_summary_indices = sorted(sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:2])
    short_summary = " ".join([sentences[idx] for idx in top_summary_indices])

    # Top 4 sentences for detailed bullet points
    top_takeaway_indices = sorted(sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:4])
    detailed_summary = "\n".join([f"* **Key Takeaway:** {sentences[idx]}" for idx in top_takeaway_indices])

    return {
        "short_summary": short_summary,
        "detailed_summary": detailed_summary
    }

def generate_abstractive_summary(transcript_text: str) -> dict:
    """
    Generates two-level abstractive summary using Gemini 2.5 Flash in strict JSON Mode.
    Falls back gracefully to heuristic extractive summarizer if the API key is missing or calls fail.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[SUMMARIZER] No GEMINI_API_KEY found. Using heuristic summarizer...")
        return generate_heuristic_summary(transcript_text)
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(
            'gemini-3.5-flash',
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = f"""
        You are an expert AI Content Editor for ClipMind. Process this [VIDEO TRANSCRIPT] and produce two levels of abstractive summaries:
        
        CRITICAL RULES:
        1. NO COPY-PASTING: Do not copy literal sentences from the transcript. Synthesize the meaning in your own words.
        2. THEMATIC, NOT CHRONOLOGICAL: Group information by core concepts rather than "first speaker said X, then Y".
        3. CLEAR AND ENGAGING: Professional, insightful, and conversational tone.
        
        REQUIRED JSON SCHEMA:
        {{
            "short_summary": "A punchy, 2-to-3 sentence hook explaining the core thesis and practical value of this video.",
            "detailed_summary": "A comprehensive breakdown using Markdown bullet points (* **Topic Header**: explanation...) with bold keywords."
        }}
        
        [VIDEO TRANSCRIPT]:
        {transcript_text}
        """
        
        print("[SUMMARIZER] Generating abstractive summary via Gemini 2.5 Flash...")
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Robust JSON extraction
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1:
            data = json.loads(text[first_brace:last_brace+1])
            short_sum = data.get("short_summary", "")
            detailed_sum = data.get("detailed_summary", "")
            if isinstance(detailed_sum, list):
                detailed_sum = "\n".join(detailed_sum)
                
            if short_sum:
                return {
                    "short_summary": short_sum,
                    "detailed_summary": detailed_sum or "Detailed breakdown not available."
                }
                
    except Exception as e:
        print(f"[SUMMARIZER] Gemini API call failed: {e}. Falling back to heuristic summary...")
        
    return generate_heuristic_summary(transcript_text)
