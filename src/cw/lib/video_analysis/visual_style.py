"""
Visual style analysis for video frames.

Analyzes colors, lighting, and camera work to understand visual aesthetics.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def extract_dominant_colors(
    image_path: str,
    n_colors: int = 5,
) -> List[str]:
    """
    Extract dominant colors from an image using k-means clustering.

    Args:
        image_path: Path to image file
        n_colors: Number of dominant colors to extract

    Returns:
        List of hex color codes (e.g., ['#FF5733', '#3357FF', ...])

    Raises:
        FileNotFoundError: If image file doesn't exist
        Exception: If color extraction fails
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Load image with OpenCV
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Reshape to pixels array
    pixels = img.reshape(-1, 3)

    # Reduce sample size for performance (max 10k pixels)
    if len(pixels) > 10000:
        indices = np.random.choice(len(pixels), 10000, replace=False)
        pixels = pixels[indices]

    # Convert to float32 for k-means
    pixels = np.float32(pixels)

    # K-means clustering
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(
        pixels,
        n_colors,
        None,
        criteria,
        10,
        cv2.KMEANS_PP_CENTERS,
    )

    # Convert cluster centers to hex colors
    centers = np.uint8(centers)
    hex_colors = []

    for center in centers:
        r, g, b = center
        hex_color = f"#{r:02x}{g:02x}{b:02x}".upper()
        hex_colors.append(hex_color)

    logger.info(f"Extracted {len(hex_colors)} dominant colors")
    return hex_colors


def analyze_lighting(image_path: str) -> Dict:
    """
    Analyze lighting characteristics of an image.

    Args:
        image_path: Path to image file

    Returns:
        Lighting analysis dictionary:
        {
            "brightness": 0.65,  # 0-1 scale (average luminance)
            "contrast": 0.42,    # 0-1 scale (std deviation)
            "exposure": "normal",  # underexposed | normal | overexposed
            "lighting_style": "soft",  # harsh | soft | dramatic
        }

    Raises:
        FileNotFoundError: If image file doesn't exist
        Exception: If analysis fails
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Load image and convert to grayscale
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Calculate brightness (mean luminance)
    brightness = np.mean(gray) / 255.0

    # Calculate contrast (standard deviation)
    contrast = np.std(gray) / 128.0  # Normalize to ~0-1 range

    # Determine exposure
    if brightness < 0.3:
        exposure = "underexposed"
    elif brightness > 0.7:
        exposure = "overexposed"
    else:
        exposure = "normal"

    # Determine lighting style (based on contrast)
    if contrast > 0.5:
        lighting_style = "dramatic"  # High contrast = hard lighting
    elif contrast > 0.3:
        lighting_style = "harsh"
    else:
        lighting_style = "soft"  # Low contrast = soft/flat lighting

    return {
        "brightness": round(brightness, 3),
        "contrast": round(min(contrast, 1.0), 3),  # Cap at 1.0
        "exposure": exposure,
        "lighting_style": lighting_style,
    }


def analyze_visual_style(image_paths: List[str]) -> Dict:
    """
    Analyze overall visual style across multiple frames.

    Args:
        image_paths: List of image file paths (keyframes)

    Returns:
        Visual style summary:
        {
            "dominant_colors": ['#FF5733', '#3357FF', ...],
            "avg_brightness": 0.58,
            "avg_contrast": 0.45,
            "lighting_distribution": {
                "soft": 3,
                "harsh": 1,
                "dramatic": 1
            },
            "exposure_distribution": {
                "normal": 4,
                "overexposed": 1
            }
        }

    Raises:
        Exception: If analysis fails
    """
    logger.info(f"Analyzing visual style across {len(image_paths)} frames")

    if not image_paths:
        return {
            "dominant_colors": [],
            "avg_brightness": 0.0,
            "avg_contrast": 0.0,
            "lighting_distribution": {},
            "exposure_distribution": {},
        }

    # Extract colors from all frames
    all_colors = []
    for path in image_paths:
        colors = extract_dominant_colors(path, n_colors=3)
        all_colors.extend(colors)

    # Get unique dominant colors (most common across all frames)
    # Simple approach: take first 8 unique colors
    unique_colors = []
    for color in all_colors:
        if color not in unique_colors:
            unique_colors.append(color)
        if len(unique_colors) >= 8:
            break

    # Analyze lighting for each frame
    brightness_values = []
    contrast_values = []
    lighting_styles = []
    exposure_types = []

    for path in image_paths:
        lighting = analyze_lighting(path)
        brightness_values.append(lighting["brightness"])
        contrast_values.append(lighting["contrast"])
        lighting_styles.append(lighting["lighting_style"])
        exposure_types.append(lighting["exposure"])

    # Calculate distributions
    lighting_dist = {}
    for style in lighting_styles:
        lighting_dist[style] = lighting_dist.get(style, 0) + 1

    exposure_dist = {}
    for exp_type in exposure_types:
        exposure_dist[exp_type] = exposure_dist.get(exp_type, 0) + 1

    result = {
        "dominant_colors": unique_colors,
        "avg_brightness": round(np.mean(brightness_values), 3),
        "avg_contrast": round(np.mean(contrast_values), 3),
        "lighting_distribution": lighting_dist,
        "exposure_distribution": exposure_dist,
    }

    logger.info("Visual style analysis complete")
    return result


def analyze_camera_work(scenes: List[Dict]) -> Dict:
    """
    Analyze camera work based on scene metadata.

    Args:
        scenes: List of scene dictionaries from scene detection

    Returns:
        Camera work analysis:
        {
            "avg_scene_duration": 4.5,  # seconds
            "total_scenes": 12,
            "pacing": "fast",  # slow | medium | fast
            "scene_transitions": 11,
        }
    """
    if not scenes:
        return {
            "avg_scene_duration": 0.0,
            "total_scenes": 0,
            "pacing": "unknown",
            "scene_transitions": 0,
        }

    # Calculate average scene duration
    durations = [scene["duration"] for scene in scenes]
    avg_duration = np.mean(durations)

    # Determine pacing based on average scene length
    if avg_duration < 2.0:
        pacing = "fast"  # Quick cuts
    elif avg_duration < 4.0:
        pacing = "medium"
    else:
        pacing = "slow"  # Long takes

    return {
        "avg_scene_duration": round(avg_duration, 2),
        "total_scenes": len(scenes),
        "pacing": pacing,
        "scene_transitions": len(scenes) - 1,
    }
