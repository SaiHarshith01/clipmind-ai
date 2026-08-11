import re
from collections import Counter
import math

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def split_sentences(text: str) -> list[str]:
    # Split by periods, exclamation marks, or question marks
    sentences = re.split(r'(?<=[.!?]) +', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]

def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    stop_words = {
        'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'to', 'for', 'of', 'or', 
        'by', 'with', 'from', 'this', 'that', 'it', 'you', 'we', 'they', 'i', 'he', 'she',
        'was', 'are', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'so', 'can', 'will',
        'just', 'about', 'like', 'there', 'what', 'so', 'all', 'would', 'up', 'out', 'if'
    }
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    filtered = [w for w in words if w not in stop_words]
    counts = Counter(filtered)
    return [w for w, _ in counts.most_common(top_n)]

def generate_summary(transcript_text: str) -> dict:
    """
    Intelligent NLP Summarizer:
    Generates a concise 2-3 sentence overview, key bullet takeaways, and keyword tags.
    Designed to process both short and long transcripts smoothly without memory crashes.
    """
    cleaned = clean_text(transcript_text)
    words = cleaned.split()
    word_count = len(words)
    
    if not cleaned or word_count < 10:
        return {
            "short_summary": cleaned or "No substantial speech detected to summarize.",
            "key_takeaways": ["Audio was brief or contained minimal dialogue."],
            "keywords": [],
            "word_count": word_count
        }

    sentences = split_sentences(cleaned)
    
    # If the transcript is very short (1-3 sentences)
    if len(sentences) <= 3:
        return {
            "short_summary": cleaned,
            "key_takeaways": [s for s in sentences if s],
            "keywords": extract_keywords(cleaned, top_n=5),
            "word_count": word_count
        }

    # Frequency-based NLP Sentence Scoring
    word_freq = Counter(re.findall(r'\b[a-zA-Z]{3,}\b', cleaned.lower()))
    sentence_scores = {}
    
    for i, sentence in enumerate(sentences):
        score = 0
        sentence_words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
        for word in sentence_words:
            score += word_freq.get(word, 0)
        
        # Normalize score by sentence length to prevent biased long sentences
        normalized_score = score / (len(sentence_words) + 1)
        
        # Give a slight boost to the first and last sentences (introduction and conclusion)
        if i == 0:
            normalized_score *= 1.3
        elif i == len(sentences) - 1:
            normalized_score *= 1.15
            
        sentence_scores[i] = normalized_score

    # Select top 2 sentences for the concise overview (preserving chronological order)
    top_summary_indices = sorted(sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:2])
    short_summary = " ".join([sentences[idx] for idx in top_summary_indices])

    # Select top 4 sentences for bullet-point key takeaways
    top_takeaway_indices = sorted(sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:4])
    key_takeaways = [sentences[idx] for idx in top_takeaway_indices]

    keywords = extract_keywords(cleaned, top_n=6)

    return {
        "short_summary": short_summary,
        "key_takeaways": key_takeaways,
        "keywords": keywords,
        "word_count": word_count
    }
