import os
import re
import json
from collections import Counter
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

def extract_keywords_heuristic(text: str, top_n: int = 8) -> list[str]:
    """Extracts top frequent keywords, filtering standard English stop words."""
    stop_words = {
        'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'to', 'for', 'of', 'or', 
        'by', 'with', 'from', 'this', 'that', 'it', 'you', 'we', 'they', 'i', 'he', 'she',
        'was', 'are', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'so', 'can', 'will',
        'just', 'about', 'like', 'there', 'what', 'all', 'would', 'up', 'out', 'if', 'your',
        'them', 'their', 'my', 'me', 'our', 'us', 'who', 'when', 'where', 'how', 'why'
    }
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    filtered = [w for w in words if w not in stop_words]
    counts = Counter(filtered)
    return [w for w, _ in counts.most_common(top_n)]

def analyze_sentiment_heuristic(text: str) -> dict:
    """Fast lexical sentiment & tone estimator."""
    positive_words = {
        'great', 'good', 'excellent', 'amazing', 'positive', 'success', 'benefit', 
        'growth', 'improve', 'effective', 'win', 'best', 'valuable', 'love', 'future',
        'solution', 'opportunity', 'build', 'create', 'strong', 'clear', 'help'
    }
    negative_words = {
        'bad', 'fail', 'failure', 'regret', 'poor', 'problem', 'risk', 'error', 
        'difficult', 'loss', 'crisis', 'hard', 'flaw', 'wrong', 'harm', 'struggle'
    }
    
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    pos_count = sum(1 for w in words if w in positive_words)
    neg_count = sum(1 for w in words if w in negative_words)
    
    if pos_count > neg_count + 1:
        sentiment = "Positive"
        tone = "Inspiring & Forward-Looking"
    elif neg_count > pos_count + 1:
        sentiment = "Critical"
        tone = "Reflective & Problem-Solving"
    else:
        sentiment = "Neutral"
        tone = "Educational & Analytical"
        
    return {
        "sentiment": sentiment,
        "tone": tone
    }

def extract_content_insights(transcript_text: str) -> dict:
    """
    Step 6 of AI Analytics Pipeline:
    Extracts Keywords, Sentiment Tone, and Key Topics / Named Entities.
    Uses Gemini when available, with automatic lexical fallback.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and len(transcript_text.split()) > 15:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                'gemini-3.5-flash',
                generation_config={"response_mime_type": "application/json"}
            )
            
            prompt = f"""
            Analyze the following transcript and return a JSON object with:
            1. "keywords": array of 6 to 8 relevant topic keywords/tags.
            2. "sentiment": One word ("Positive", "Constructive", "Neutral", "Inspiring", or "Analytical").
            3. "tone": A 2-to-4 word description of the overall speaking style (e.g. "Practical Tutorial", "Thought Leadership", "Personal Journey").
            4. "key_entities": array of 3 to 5 core entities, technologies, or subjects mentioned.
            
            Transcript:
            {transcript_text[:2500]}
            """
            
            response = model.generate_content(prompt)
            text = response.text.strip()
            first_brace = text.find('{')
            last_brace = text.rfind('}')
            if first_brace != -1 and last_brace != -1:
                data = json.loads(text[first_brace:last_brace+1])
                return {
                    "keywords": data.get("keywords", extract_keywords_heuristic(transcript_text)),
                    "sentiment": data.get("sentiment", "Educational"),
                    "tone": data.get("tone", "Informative & Analytical"),
                    "key_entities": data.get("key_entities", [])
                }
        except Exception as e:
            print(f"[INSIGHTS] LLM insights failed ({e}), using heuristic analysis...")

    # Heuristic fallback
    sentiment_data = analyze_sentiment_heuristic(transcript_text)
    keywords = extract_keywords_heuristic(transcript_text)
    
    return {
        "keywords": keywords,
        "sentiment": sentiment_data["sentiment"],
        "tone": sentiment_data["tone"],
        "key_entities": keywords[:4]
    }
