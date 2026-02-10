"""
Scene detection using PySceneDetect.

Identifies distinct scenes in video based on visual content changes.
"""

from typing import Dict, List

from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector


def detect_scenes(
    video_path: str, threshold: float = 27.0, min_scene_len: int = 15
) -> List[Dict]:
    """
    Detect scene boundaries using content-based detection.

    Uses PySceneDetect's ContentDetector which analyzes changes in content
    between frames to identify scene boundaries.

    Args:
        video_path: Path to video file
        threshold: Sensitivity threshold for scene detection (default: 27.0)
                  Lower values = more scenes detected
                  Typical range: 15-40
        min_scene_len: Minimum scene length in frames (default: 15)

    Returns:
        List of scene dictionaries:
        [
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 3.5,
                "duration": 3.5,
                "start_frame": 0,
                "end_frame": 105
            },
            ...
        ]

    Raises:
        FileNotFoundError: If video file doesn't exist
        Exception: If scene detection fails
    """
    # Open video with scenedetect
    video = open_video(video_path)

    # Create scene manager with content detector
    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(threshold=threshold, min_scene_len=min_scene_len)
    )

    # Detect scenes
    scene_manager.detect_scenes(video)

    # Get detected scene list
    scene_list = scene_manager.get_scene_list()

    # Convert to our format
    scenes = []
    for idx, (start_time, end_time) in enumerate(scene_list, 1):
        # FrameTimecode objects have get_seconds() and get_frames() methods
        scenes.append(
            {
                "scene_number": idx,
                "start_time": start_time.get_seconds(),
                "end_time": end_time.get_seconds(),
                "duration": (end_time - start_time).get_seconds(),
                "start_frame": start_time.get_frames(),
                "end_frame": end_time.get_frames(),
            }
        )

    return scenes
