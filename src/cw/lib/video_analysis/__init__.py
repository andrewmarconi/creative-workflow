"""
Video analysis utilities for extracting scenes, transcription, and insights.

This package provides tools for analyzing uploaded video files to automatically
generate structured scripts for TV spot campaigns.
"""

# Phase 1: Core analysis
from .metadata import extract_video_metadata
from .scene_detection import detect_scenes
from .transcription import transcribe_audio

# Phase 2: Enhanced analysis
from .object_detection import (
    detect_objects,
    detect_objects_batch,
    summarize_objects,
)
from .visual_style import (
    analyze_camera_work,
    analyze_lighting,
    analyze_visual_style,
    extract_dominant_colors,
)
from .sentiment import analyze_sentiment
from .categorization import categorize_scenes, summarize_categories

__all__ = [
    # Phase 1
    "extract_video_metadata",
    "detect_scenes",
    "transcribe_audio",
    # Phase 2
    "detect_objects",
    "detect_objects_batch",
    "summarize_objects",
    "analyze_camera_work",
    "analyze_lighting",
    "analyze_visual_style",
    "extract_dominant_colors",
    "analyze_sentiment",
    "categorize_scenes",
    "summarize_categories",
]
