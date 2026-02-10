"""
Video metadata extraction using PyAV (FFmpeg).

Extracts technical metadata from video files including duration,
resolution, frame rate, and audio properties.
"""

import os
from typing import Dict

import av


def extract_video_metadata(video_path: str) -> Dict:
    """
    Extract metadata from a video file using PyAV.

    Args:
        video_path: Path to the video file

    Returns:
        Dictionary containing video metadata:
        {
            'duration': float (seconds),
            'width': int,
            'height': int,
            'frame_rate': float,
            'audio_channels': int,
            'sample_rate': int,
            'file_size': int (bytes)
        }

    Raises:
        FileNotFoundError: If video file doesn't exist
        av.AVError: If file cannot be opened or is not a valid video
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    metadata = {
        "duration": None,
        "width": None,
        "height": None,
        "frame_rate": None,
        "audio_channels": None,
        "sample_rate": None,
        "file_size": None,
    }

    try:
        # Get file size
        metadata["file_size"] = os.path.getsize(video_path)

        # Open video file with PyAV
        with av.open(video_path) as container:
            # Extract video stream metadata
            video_stream = None
            for stream in container.streams.video:
                video_stream = stream
                break  # Use first video stream

            if video_stream:
                metadata["width"] = video_stream.width
                metadata["height"] = video_stream.height

                # Calculate frame rate
                if video_stream.average_rate:
                    metadata["frame_rate"] = float(video_stream.average_rate)

                # Get duration from video stream or container
                if video_stream.duration:
                    # Convert from time_base to seconds
                    metadata["duration"] = float(
                        video_stream.duration * video_stream.time_base
                    )
                elif container.duration:
                    # Container duration is in microseconds
                    metadata["duration"] = float(container.duration) / 1000000.0

            # Extract audio stream metadata
            audio_stream = None
            for stream in container.streams.audio:
                audio_stream = stream
                break  # Use first audio stream

            if audio_stream:
                metadata["audio_channels"] = audio_stream.channels
                metadata["sample_rate"] = audio_stream.rate

    except av.AVError as e:
        raise av.AVError(f"Failed to extract metadata from {video_path}: {e}")

    return metadata
