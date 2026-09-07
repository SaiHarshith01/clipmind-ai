def calculate_video_analytics(transcript_text: str, segments: list[dict]) -> dict:
    """
    Analytics & Insights Layer:
    Calculates speaker pacing, reading estimates, and productivity time saved.
    """
    words = transcript_text.split()
    word_count = len(words)
    
    # Calculate duration from segment timestamps
    duration_seconds = 0.0
    if segments:
        duration_seconds = max(seg.get("end", 0.0) for seg in segments)
        
    duration_minutes = max(0.1, duration_seconds / 60.0)
    
    # Speaking Pace (Words Per Minute)
    speaking_wpm = round(word_count / duration_minutes) if duration_minutes > 0 else 130
    
    # Estimated Reading Time (standard adult reading pace: ~220 WPM)
    reading_time_minutes = max(1, round(word_count / 220.0))
    
    # Summary Reading Time (~80-120 words summary takes ~30 seconds)
    summary_read_minutes = 0.5
    
    # Time Saved (Video Watch Duration minus Summary Reading Duration)
    time_saved_minutes = max(0.0, round(duration_minutes - summary_read_minutes, 1))
    
    return {
        "word_count": word_count,
        "duration_seconds": round(duration_seconds, 1),
        "speaking_wpm": speaking_wpm,
        "reading_time_minutes": reading_time_minutes,
        "time_saved_minutes": time_saved_minutes,
        "pacing_label": "Fast" if speaking_wpm > 160 else ("Steady" if speaking_wpm >= 120 else "Deliberate")
    }
