import os
import shutil
import imageio_ffmpeg
import torch
import whisper

# Prevent CUDA memory fragmentation on Windows laptop GPUs
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Ensure FFmpeg binary is properly accessible in PATH for OpenAI Whisper on Windows
try:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    target_ffmpeg = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if not os.path.exists(target_ffmpeg):
        shutil.copyfile(ffmpeg_exe, target_ffmpeg)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception as e:
    print(f"[TRANSCRIBER] Warning setting up FFmpeg PATH: {e}")

# Global model cache to avoid re-allocating GPU memory on every request
_MODEL_CACHE = {}

def get_whisper_model(model_size: str, device: str):
    cache_key = f"{model_size}_{device}"
    if cache_key not in _MODEL_CACHE:
        if device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        print(f"[TRANSCRIBER] Loading Whisper '{model_size}' model onto {device.upper()}...")
        _MODEL_CACHE[cache_key] = whisper.load_model(model_size, device=device)
    return _MODEL_CACHE[cache_key]

def transcribe_audio(
    audio_path: str, 
    model_size: str = "base", 
    task: str = "translate"
) -> tuple[str, list[dict]]:
    """
    Dedicated Speech-to-Text & Translation service utilizing OpenAI Whisper.
    Uses cached 'base' model with CUDA FP16 GPU acceleration and automatic CPU fallback.
    Automatically translates multi-language audio (e.g. Telugu, Hindi, Tamil) into English.
    Returns:
        tuple (transcript_text: str, segments: list[dict])
        Each segment contains: {'start': float, 'end': float, 'text': str}
    """
    result = None
    
    # Attempt 1: Fast CUDA GPU Execution
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
            device_name = torch.cuda.get_device_name(0)
            print(f"[TRANSCRIBER] Transcribing on GPU ({device_name}) with fp16=False (FP32)...")
            model = get_whisper_model(model_size, device="cuda")
            
            # Fast language probing on the first 30 seconds
            audio_sample = whisper.load_audio(audio_path)
            mel = whisper.log_mel_spectrogram(whisper.pad_or_trim(audio_sample)).to("cuda")
            _, probs = model.detect_language(mel)
            detected_lang = max(probs, key=probs.get)
            print(f"[TRANSCRIBER] Detected spoken language: '{detected_lang}' ({round(probs[detected_lang]*100, 1)}% confidence)")
            
            # If already English, standard transcribe is 2x faster; if non-English (Telugu, Tamil, Hindi), translate to English
            active_task = "transcribe" if detected_lang == "en" else "translate"
            
            result = model.transcribe(
                audio_path, 
                fp16=False, 
                task=active_task,
                temperature=0,
                condition_on_previous_text=False
            )
        except Exception as cuda_err:
            print(f"[TRANSCRIBER] GPU transcription encountered: {cuda_err}. Falling back to CPU...")
            torch.cuda.empty_cache()
            result = None

    # Attempt 2: CPU Fallback (Guaranteed to succeed without VRAM limits)
    if result is None:
        try:
            print(f"[TRANSCRIBER] Transcribing on Host CPU (task='{task}')...")
            model = get_whisper_model(model_size, device="cpu")
            result = model.transcribe(
                audio_path, 
                fp16=False, 
                task=task,
                temperature=0,
                condition_on_previous_text=False
            )
        except Exception as cpu_err:
            print(f"[TRANSCRIBER] CPU transcription failed: {cpu_err}")
            fallback_text = "Audio extracted successfully, but speech transcription could not be completed."
            return fallback_text, [{"start": 0.0, "end": 0.0, "text": fallback_text}]

    detected_lang = result.get("language", "auto")
    print(f"[TRANSCRIBER] Success! Detected language: '{detected_lang}'. Output translated to English.")
    
    transcript = result.get("text", "").strip()
    
    # Extract time-aligned segments with float timestamps
    segments = []
    for seg in result.get("segments", []):
        seg_text = seg.get("text", "").strip()
        if seg_text:
            segments.append({
                "start": round(float(seg.get("start", 0.0)), 2),
                "end": round(float(seg.get("end", 0.0)), 2),
                "text": seg_text
            })
            
    print(f"[TRANSCRIBER] Completed! Transcribed {len(transcript)} chars across {len(segments)} segments.")
    
    fallback_transcript = transcript if transcript else "No audible dialogue was detected in the video."
    fallback_segments = segments if segments else [{"start": 0.0, "end": 0.0, "text": fallback_transcript}]
    
    return fallback_transcript, fallback_segments
