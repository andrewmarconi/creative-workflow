"""
Object detection using YOLO v8.

Detects objects, people, and products in video frames.
"""

import logging
from pathlib import Path
from typing import Dict, List

from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger(__name__)

# Module-level model cache
_yolo_model = None


def get_yolo_model(model_name: str = "yolov8x.pt") -> YOLO:
    """
    Get or load YOLO model (cached at module level).

    Args:
        model_name: YOLO model variant (yolov8n/s/m/l/x.pt)
                   Default: yolov8x.pt (highest accuracy)

    Returns:
        Loaded YOLO model instance
    """
    global _yolo_model

    if _yolo_model is None:
        logger.info(f"Loading YOLO model: {model_name}")
        _yolo_model = YOLO(model_name)
        logger.info(f"YOLO model loaded successfully")

    return _yolo_model


def detect_objects(
    image_path: str,
    conf_threshold: float = 0.5,
    model_name: str = "yolov8x.pt",
) -> List[Dict]:
    """
    Detect objects in a single image using YOLO v8.

    Args:
        image_path: Path to image file
        conf_threshold: Minimum confidence threshold (0.0-1.0)
        model_name: YOLO model variant to use

    Returns:
        List of detected objects:
        [
            {
                "class": "person",
                "class_id": 0,
                "confidence": 0.95,
                "bbox": [x1, y1, x2, y2],  # Coordinates in pixels
            },
            ...
        ]

    Raises:
        FileNotFoundError: If image file doesn't exist
        Exception: If detection fails
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    logger.info(f"Detecting objects in: {image_path}")

    # Get cached model
    model = get_yolo_model(model_name)

    # Run inference
    results = model(image_path, conf=conf_threshold, verbose=False)

    # Extract detections from first result (single image)
    detections = []
    for result in results:
        boxes = result.boxes
        for i in range(len(boxes)):
            # Get bounding box coordinates
            box = boxes.xyxy[i].cpu().numpy()  # [x1, y1, x2, y2]

            detection = {
                "class": result.names[int(boxes.cls[i])],
                "class_id": int(boxes.cls[i]),
                "confidence": round(float(boxes.conf[i]), 3),
                "bbox": [round(float(coord), 1) for coord in box],
            }
            detections.append(detection)

    logger.info(f"Detected {len(detections)} objects")
    return detections


def detect_objects_batch(
    image_paths: List[str],
    conf_threshold: float = 0.5,
    model_name: str = "yolov8x.pt",
) -> Dict[str, List[Dict]]:
    """
    Detect objects in multiple images (batch processing).

    Args:
        image_paths: List of image file paths
        conf_threshold: Minimum confidence threshold
        model_name: YOLO model variant to use

    Returns:
        Dictionary mapping image paths to detection lists:
        {
            "frame_001.jpg": [{"class": "person", ...}, ...],
            "frame_002.jpg": [{"class": "car", ...}, ...],
            ...
        }

    Raises:
        Exception: If batch detection fails
    """
    logger.info(f"Batch detecting objects in {len(image_paths)} images")

    # Get cached model
    model = get_yolo_model(model_name)

    # Run batch inference
    results = model(image_paths, conf=conf_threshold, verbose=False)

    # Process each image's results
    detections_map = {}
    for image_path, result in zip(image_paths, results):
        detections = []
        boxes = result.boxes

        for i in range(len(boxes)):
            box = boxes.xyxy[i].cpu().numpy()
            detection = {
                "class": result.names[int(boxes.cls[i])],
                "class_id": int(boxes.cls[i]),
                "confidence": round(float(boxes.conf[i]), 3),
                "bbox": [round(float(coord), 1) for coord in box],
            }
            detections.append(detection)

        detections_map[image_path] = detections

    logger.info(f"Batch detection complete: {sum(len(d) for d in detections_map.values())} total objects")
    return detections_map


def summarize_objects(detections: List[Dict]) -> Dict:
    """
    Summarize object detections with counts and confidence scores.

    Args:
        detections: List of detections from detect_objects()

    Returns:
        Summary dictionary:
        {
            "total_objects": 15,
            "classes": {
                "person": {"count": 5, "avg_confidence": 0.92},
                "car": {"count": 2, "avg_confidence": 0.85},
                ...
            },
            "most_common": ["person", "car", "bottle"]
        }
    """
    if not detections:
        return {
            "total_objects": 0,
            "classes": {},
            "most_common": [],
        }

    # Count objects by class
    class_stats = {}
    for det in detections:
        class_name = det["class"]
        if class_name not in class_stats:
            class_stats[class_name] = {
                "count": 0,
                "confidences": [],
            }

        class_stats[class_name]["count"] += 1
        class_stats[class_name]["confidences"].append(det["confidence"])

    # Calculate average confidences
    for class_name in class_stats:
        confidences = class_stats[class_name]["confidences"]
        avg_conf = sum(confidences) / len(confidences)
        class_stats[class_name]["avg_confidence"] = round(avg_conf, 3)
        del class_stats[class_name]["confidences"]  # Remove raw list

    # Get most common classes (sorted by count)
    most_common = sorted(
        class_stats.keys(),
        key=lambda c: class_stats[c]["count"],
        reverse=True,
    )

    return {
        "total_objects": len(detections),
        "classes": class_stats,
        "most_common": most_common[:10],  # Top 10 most common
    }
