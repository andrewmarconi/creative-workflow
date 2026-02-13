"""
ControlNet image preprocessing utilities.

Wraps controlnet_aux detectors for converting source images into
control signals (edges, depth maps, line art) that guide ControlNet
image generation.

Usage::

    from cw.lib.controlnet_preprocessing import preprocess_image
    from PIL import Image

    source = Image.open("keyframe.jpg")
    control_image = preprocess_image(source, "lineart", detect_resolution=512)
"""

import logging

from PIL import Image

logger = logging.getLogger(__name__)

# Lazy-loaded detector cache (avoid importing controlnet_aux at module level)
_detector_cache = {}


def _get_detector(control_type: str):
    """
    Get or create a cached detector instance.

    Args:
        control_type: One of 'canny', 'lineart', 'lineart_anime', 'depth',
                      'softedge', 'openpose'

    Returns:
        Detector instance

    Raises:
        ValueError: If control_type is not recognized
    """
    if control_type in _detector_cache:
        return _detector_cache[control_type]

    logger.info(f"Loading ControlNet preprocessor: {control_type}")

    if control_type == "canny":
        from controlnet_aux import CannyDetector

        detector = CannyDetector()

    elif control_type == "lineart":
        from controlnet_aux import LineartDetector

        detector = LineartDetector.from_pretrained("lllyasviel/Annotators")

    elif control_type == "lineart_anime":
        from controlnet_aux import LineartAnimeDetector

        detector = LineartAnimeDetector.from_pretrained("lllyasviel/Annotators")

    elif control_type == "depth":
        from controlnet_aux import MidasDetector

        detector = MidasDetector.from_pretrained("lllyasviel/Annotators")

    elif control_type == "softedge":
        from controlnet_aux import HEDdetector

        detector = HEDdetector.from_pretrained("lllyasviel/Annotators")

    elif control_type == "openpose":
        from controlnet_aux import OpenposeDetector

        detector = OpenposeDetector.from_pretrained("lllyasviel/Annotators")

    else:
        raise ValueError(
            f"Unknown control type: {control_type}. "
            f"Supported: canny, lineart, lineart_anime, depth, softedge, openpose"
        )

    _detector_cache[control_type] = detector
    logger.info(f"Preprocessor loaded: {control_type}")
    return detector


def preprocess_image(
    image: Image.Image,
    control_type: str,
    detect_resolution: int = 512,
    image_resolution: int = 1024,
    **kwargs,
) -> Image.Image:
    """
    Preprocess an image for ControlNet conditioning.

    Args:
        image: Source PIL image
        control_type: Preprocessing type ('canny', 'lineart', 'lineart_anime',
                      'depth', 'softedge', 'openpose')
        detect_resolution: Resolution for detection (higher = more detail, slower)
        image_resolution: Output resolution for the control image
        **kwargs: Additional detector-specific parameters (e.g., low_threshold,
                  high_threshold for canny)

    Returns:
        Preprocessed PIL image suitable for ControlNet conditioning
    """
    image = image.convert("RGB")

    detector = _get_detector(control_type)

    if control_type == "canny":
        # Canny uses low/high thresholds instead of resolution params
        low_threshold = kwargs.get("low_threshold", 100)
        high_threshold = kwargs.get("high_threshold", 200)
        result = detector(
            image,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
            detect_resolution=detect_resolution,
            image_resolution=image_resolution,
        )
    else:
        result = detector(
            image,
            detect_resolution=detect_resolution,
            image_resolution=image_resolution,
        )

    logger.debug(
        f"Preprocessed image: {control_type}, "
        f"detect_res={detect_resolution}, image_res={image_resolution}, "
        f"output_size={result.size}"
    )

    return result


def clear_detector_cache():
    """Free memory by clearing all cached detectors."""
    _detector_cache.clear()
    logger.debug("Cleared ControlNet detector cache")
