"""
Scene categorization for video content.

Categorizes scenes based on visual content, objects, and context.
"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


# Scene category definitions with associated object classes
CATEGORY_PATTERNS = {
    "people": {
        "required_objects": {"person"},
        "keywords": ["people", "person", "human", "group", "crowd", "family"],
        "description": "Scenes featuring people",
    },
    "product": {
        "required_objects": {"bottle", "cup", "bowl", "knife", "fork", "spoon"},
        "keywords": ["product", "package", "container", "food", "drink"],
        "description": "Product shots and demonstrations",
    },
    "food": {
        "required_objects": {"pizza", "cake", "sandwich", "hot dog", "donut", "carrot", "apple", "orange", "banana"},
        "keywords": ["food", "meal", "eat", "cook", "kitchen", "recipe"],
        "description": "Food and culinary scenes",
    },
    "lifestyle": {
        "required_objects": {"person", "couch", "bed", "dining table", "tv"},
        "keywords": ["home", "family", "relax", "comfortable", "living"],
        "description": "Lifestyle and home scenes",
    },
    "outdoor": {
        "required_objects": {"bicycle", "car", "motorcycle", "bus", "truck", "boat"},
        "keywords": ["outdoor", "outside", "nature", "park", "street", "road"],
        "description": "Outdoor and travel scenes",
    },
    "technology": {
        "required_objects": {"cell phone", "laptop", "keyboard", "mouse", "tv", "remote"},
        "keywords": ["technology", "tech", "digital", "device", "phone", "computer"],
        "description": "Technology and digital devices",
    },
    "sports": {
        "required_objects": {"sports ball", "tennis racket", "baseball bat", "skateboard", "surfboard", "skis"},
        "keywords": ["sport", "game", "play", "active", "fitness", "exercise"],
        "description": "Sports and athletic activities",
    },
    "animals": {
        "required_objects": {"bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"},
        "keywords": ["animal", "pet", "dog", "cat", "bird", "wildlife"],
        "description": "Animals and pets",
    },
    "text": {
        "required_objects": {"book", "clock"},
        "keywords": ["text", "title", "message", "words", "logo", "brand"],
        "description": "Text overlays and branding",
    },
    "abstract": {
        "required_objects": set(),  # No specific objects
        "keywords": ["abstract", "graphic", "animation", "pattern", "color"],
        "description": "Abstract visuals and graphics",
    },
}


def categorize_scene(
    scene: Dict,
    detections: List[Dict],
    transcription_text: str = "",
) -> List[str]:
    """
    Categorize a single scene based on detected objects and context.

    Args:
        scene: Scene dictionary with metadata
        detections: List of object detections for the scene
        transcription_text: Optional transcribed text from the scene

    Returns:
        List of category names (can be multiple)
        e.g., ["people", "lifestyle", "product"]
    """
    categories = []

    # Get detected object classes
    detected_classes = {det["class"] for det in detections}

    # Normalize transcription text
    text_lower = transcription_text.lower() if transcription_text else ""

    # Check each category pattern
    for category_name, pattern in CATEGORY_PATTERNS.items():
        required_objects = pattern["required_objects"]
        keywords = pattern["keywords"]

        # Check if required objects are present
        has_objects = bool(required_objects.intersection(detected_classes))

        # Check if keywords are in transcription
        has_keywords = any(keyword in text_lower for keyword in keywords)

        # Category matches if:
        # - Required objects detected (if pattern has required objects), OR
        # - Keywords found in transcription (even if pattern has required objects)
        if has_objects or has_keywords:
            categories.append(category_name)

    # Special case: if no categories matched, default to "abstract"
    if not categories:
        categories.append("abstract")

    return sorted(categories)


def categorize_scenes(
    scenes: List[Dict],
    keyframe_detections: Dict[int, List[Dict]],
    transcription: Dict,
) -> List[Dict]:
    """
    Categorize all scenes in a video.

    Args:
        scenes: List of scene dictionaries
        keyframe_detections: Dict mapping scene_number to detections
        transcription: Full transcription data

    Returns:
        List of scene dictionaries with added "categories" field:
        [
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 5.0,
                "categories": ["people", "lifestyle"],
                ...
            },
            ...
        ]
    """
    logger.info(f"Categorizing {len(scenes)} scenes")

    categorized_scenes = []

    for scene in scenes:
        scene_number = scene["scene_number"]
        start_time = scene["start_time"]
        end_time = scene["end_time"]

        # Get detections for this scene's keyframe
        detections = keyframe_detections.get(scene_number, [])

        # Get transcription text for this time range
        scene_text = " ".join(
            segment["text"]
            for segment in transcription.get("segments", [])
            if start_time <= segment["start"] < end_time
        )

        # Categorize the scene
        categories = categorize_scene(scene, detections, scene_text)

        # Add categories to scene
        scene_with_categories = scene.copy()
        scene_with_categories["categories"] = categories

        categorized_scenes.append(scene_with_categories)

    logger.info("Scene categorization complete")
    return categorized_scenes


def summarize_categories(categorized_scenes: List[Dict]) -> Dict:
    """
    Summarize category distribution across all scenes.

    Args:
        categorized_scenes: List of scenes with categories

    Returns:
        Category summary:
        {
            "total_scenes": 10,
            "category_counts": {
                "people": 6,
                "product": 4,
                "lifestyle": 3,
                ...
            },
            "primary_categories": ["people", "product"],  # Top 3
        }
    """
    category_counts = {}

    for scene in categorized_scenes:
        for category in scene.get("categories", []):
            category_counts[category] = category_counts.get(category, 0) + 1

    # Get top categories (sorted by count)
    sorted_categories = sorted(
        category_counts.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    primary_categories = [cat for cat, _ in sorted_categories[:3]]

    return {
        "total_scenes": len(categorized_scenes),
        "category_counts": category_counts,
        "primary_categories": primary_categories,
    }
