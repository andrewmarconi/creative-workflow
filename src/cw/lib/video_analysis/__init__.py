"""
Video analysis utilities for extracting scenes, transcription, and insights.

This package provides tools for analyzing uploaded video files to automatically
generate structured scripts for TV spot campaigns.
"""

from .metadata import extract_video_metadata
from .scene_detection import detect_scenes
from .transcription import transcribe_audio

__all__ = [
    "extract_video_metadata",
    "detect_scenes",
    "transcribe_audio",
]
