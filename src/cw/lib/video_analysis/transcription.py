"""
Audio transcription using OpenAI Whisper.

Transcribes spoken audio from video files with timestamps.
"""

import logging
from typing import Dict

import torch
import whisper

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: str, model_size: str = "large-v3", language: str = None
) -> Dict:
    """
    Transcribe audio using Whisper.

    Args:
        audio_path: Path to audio file (MP3, WAV, or video file)
        model_size: Whisper model size (tiny, base, small, medium, large, large-v3)
                   Recommended: large-v3 for best quality
        language: Force specific language (e.g., 'en'), or None for auto-detect

    Returns:
        Transcription dictionary:
        {
            "language": "en",
            "confidence": 0.95,
            "segments": [
                {
                    "start": 0.5,
                    "end": 3.2,
                    "text": "Transcribed text...",
                    "speaker": "narrator",
                    "confidence": 0.96
                },
                ...
            ]
        }

    Raises:
        FileNotFoundError: If audio file doesn't exist
        Exception: If transcription fails
    """
    # Determine device (CUDA > CPU)
    # Note: MPS support in Whisper is unstable and causes NaN values, so we skip it
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    # Load Whisper model, falling back to a smaller variant on OOM
    model = None
    for size in [model_size, "medium", "base"]:
        try:
            logger.info(f"Loading Whisper model: {size} on {device}")
            model = whisper.load_model(size, device=device)
            if size != model_size:
                logger.warning(
                    f"Fell back from '{model_size}' to '{size}' due to VRAM constraints"
                )
            break
        except (torch.cuda.OutOfMemoryError, RuntimeError) as e:
            if "out of memory" not in str(e).lower() and "CUDA" not in str(e):
                raise
            logger.warning(f"Whisper '{size}' OOM on {device}, trying smaller model")
            # Clear failed allocation before retrying
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    if model is None:
        raise RuntimeError(
            f"Could not load any Whisper model on {device}. "
            "Free GPU memory or use a smaller model."
        )

    logger.info(f"Transcribing audio from: {audio_path}")

    # Transcribe with word-level timestamps
    result = model.transcribe(
        audio_path,
        task="transcribe",
        language=language,  # Auto-detect if None
        word_timestamps=True,
        verbose=False,
    )

    logger.info(
        f"Transcription complete. Language detected: {result.get('language', 'unknown')}"
    )

    # Calculate average confidence from log probabilities
    total_confidence = 0.0
    segment_count = len(result["segments"])

    if segment_count > 0:
        for seg in result["segments"]:
            # Convert log probability to confidence (0-1)
            # avg_logprob is typically between -1 and 0
            logprob = seg.get("avg_logprob", -1.0)
            confidence = max(0.0, 1.0 + logprob)  # Rough conversion
            total_confidence += confidence

        avg_confidence = total_confidence / segment_count
    else:
        avg_confidence = 0.0

    # Format for our schema
    transcription = {
        "language": result.get("language", "unknown"),
        "confidence": round(avg_confidence, 3),
        "segments": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
                "speaker": "narrator",  # TODO: Add speaker diarization in future
                "confidence": round(
                    max(0.0, 1.0 + seg.get("avg_logprob", -1.0)), 3
                ),  # Convert logprob to confidence
            }
            for seg in result["segments"]
        ],
    }

    # Explicitly free Whisper model VRAM
    del model
    del result

    return transcription
