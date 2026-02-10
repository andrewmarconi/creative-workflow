"""
Unit tests for Phase 2 video analysis modules.

Tests cover:
- Object detection with YOLO v8
- Visual style analysis (colors, lighting, camera work)
- Sentiment analysis (audio + visual)
- Scene categorization
"""

from unittest.mock import Mock, patch
import tempfile
from pathlib import Path

from django.test import TestCase
from PIL import Image
import numpy as np


class ObjectDetectionTestCase(TestCase):
    """Test object detection with YOLO v8."""

    def setUp(self):
        """Create temporary test image."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = Path(self.temp_dir) / "test_frame.jpg"

        # Create a simple test image (white 100x100)
        img = Image.new("RGB", (100, 100), color="white")
        img.save(self.test_image_path)

    @patch("cw.lib.video_analysis.object_detection.YOLO")
    def test_detect_objects(self, mock_yolo_class):
        """Test basic object detection."""
        from cw.lib.video_analysis import detect_objects

        # Mock YOLO model and results
        mock_model = Mock()
        mock_yolo_class.return_value = mock_model

        # Mock detection result with torch-like tensors
        mock_result = Mock()
        mock_result.names = {0: "person", 1: "car"}
        mock_boxes = Mock()

        # Create mock tensors with cpu() and numpy() methods
        mock_tensor1 = Mock()
        mock_tensor1.cpu.return_value.numpy.return_value = np.array([10, 20, 50, 80])
        mock_tensor2 = Mock()
        mock_tensor2.cpu.return_value.numpy.return_value = np.array([60, 30, 90, 70])

        mock_boxes.xyxy = [mock_tensor1, mock_tensor2]
        mock_boxes.cls = [0, 1]  # person, car
        mock_boxes.conf = [0.95, 0.87]
        mock_boxes.__len__ = lambda self: 2
        mock_result.boxes = mock_boxes

        mock_model.return_value = [mock_result]

        # Run detection
        detections = detect_objects(str(self.test_image_path), conf_threshold=0.5)

        # Verify results
        self.assertEqual(len(detections), 2)
        self.assertEqual(detections[0]["class"], "person")
        self.assertEqual(detections[0]["confidence"], 0.95)
        self.assertEqual(detections[1]["class"], "car")
        self.assertEqual(detections[1]["confidence"], 0.87)

    @patch("cw.lib.video_analysis.object_detection.YOLO")
    def test_summarize_objects(self, mock_yolo_class):
        """Test object detection summarization."""
        from cw.lib.video_analysis import summarize_objects

        detections = [
            {"class": "person", "confidence": 0.95},
            {"class": "person", "confidence": 0.92},
            {"class": "car", "confidence": 0.87},
            {"class": "bottle", "confidence": 0.82},
            {"class": "bottle", "confidence": 0.79},
        ]

        summary = summarize_objects(detections)

        self.assertEqual(summary["total_objects"], 5)
        self.assertEqual(summary["classes"]["person"]["count"], 2)
        self.assertAlmostEqual(summary["classes"]["person"]["avg_confidence"], 0.935, places=2)
        self.assertEqual(summary["classes"]["bottle"]["count"], 2)
        self.assertEqual(summary["most_common"][0], "person")


class VisualStyleTestCase(TestCase):
    """Test visual style analysis."""

    def setUp(self):
        """Create test images."""
        self.temp_dir = tempfile.mkdtemp()

        # Create colored test images
        self.red_image = Path(self.temp_dir) / "red.jpg"
        Image.new("RGB", (100, 100), color="red").save(self.red_image)

        self.blue_image = Path(self.temp_dir) / "blue.jpg"
        Image.new("RGB", (100, 100), color="blue").save(self.blue_image)

    def test_extract_dominant_colors(self):
        """Test dominant color extraction."""
        from cw.lib.video_analysis import extract_dominant_colors

        colors = extract_dominant_colors(str(self.red_image), n_colors=3)

        self.assertEqual(len(colors), 3)
        # Colors should be hex strings
        for color in colors:
            self.assertTrue(color.startswith("#"))
            self.assertEqual(len(color), 7)

    def test_analyze_lighting(self):
        """Test lighting analysis."""
        from cw.lib.video_analysis import analyze_lighting

        lighting = analyze_lighting(str(self.red_image))

        self.assertIn("brightness", lighting)
        self.assertIn("contrast", lighting)
        self.assertIn("exposure", lighting)
        self.assertIn("lighting_style", lighting)

        # Brightness should be 0-1
        self.assertGreaterEqual(lighting["brightness"], 0.0)
        self.assertLessEqual(lighting["brightness"], 1.0)

    def test_analyze_visual_style(self):
        """Test overall visual style analysis."""
        from cw.lib.video_analysis import analyze_visual_style

        image_paths = [str(self.red_image), str(self.blue_image)]
        style = analyze_visual_style(image_paths)

        self.assertIn("dominant_colors", style)
        self.assertIn("avg_brightness", style)
        self.assertIn("avg_contrast", style)
        self.assertIn("lighting_distribution", style)

        # Should have colors from both images
        self.assertGreater(len(style["dominant_colors"]), 0)

    def test_analyze_camera_work(self):
        """Test camera work analysis."""
        from cw.lib.video_analysis import analyze_camera_work

        scenes = [
            {"scene_number": 1, "duration": 2.5},
            {"scene_number": 2, "duration": 3.0},
            {"scene_number": 3, "duration": 1.5},
        ]

        camera = analyze_camera_work(scenes)

        self.assertEqual(camera["total_scenes"], 3)
        self.assertEqual(camera["scene_transitions"], 2)
        self.assertAlmostEqual(camera["avg_scene_duration"], 2.33, places=1)
        self.assertIn(camera["pacing"], ["slow", "medium", "fast"])


class SentimentAnalysisTestCase(TestCase):
    """Test sentiment analysis."""

    def test_analyze_text_sentiment_positive(self):
        """Test positive text sentiment."""
        from cw.lib.video_analysis.sentiment import analyze_text_sentiment

        text = "This is a great product! I love how amazing and wonderful it is."
        sentiment = analyze_text_sentiment(text)

        self.assertEqual(sentiment["sentiment"], "positive")
        self.assertGreater(sentiment["score"], 0)
        self.assertGreater(sentiment["confidence"], 0)

    def test_analyze_text_sentiment_negative(self):
        """Test negative text sentiment."""
        from cw.lib.video_analysis.sentiment import analyze_text_sentiment

        text = "This is terrible. I hate how bad and awful it is."
        sentiment = analyze_text_sentiment(text)

        self.assertEqual(sentiment["sentiment"], "negative")
        self.assertLess(sentiment["score"], 0)

    def test_analyze_text_sentiment_neutral(self):
        """Test neutral text sentiment."""
        from cw.lib.video_analysis.sentiment import analyze_text_sentiment

        text = "This is a thing that exists."
        sentiment = analyze_text_sentiment(text)

        self.assertEqual(sentiment["sentiment"], "neutral")

    def test_analyze_visual_sentiment(self):
        """Test visual sentiment analysis."""
        from cw.lib.video_analysis.sentiment import analyze_visual_sentiment

        visual_style = {
            "avg_brightness": 0.7,  # Bright = positive
            "avg_contrast": 0.4,
        }

        objects = {
            "classes": {
                "person": {"count": 3, "avg_confidence": 0.9}
            },
            "total_objects": 3,
        }

        sentiment = analyze_visual_sentiment(visual_style, objects)

        self.assertIn("sentiment", sentiment)
        self.assertIn("score", sentiment)
        self.assertEqual(sentiment["sentiment"], "positive")  # Bright + people = positive

    def test_analyze_sentiment_combined(self):
        """Test combined audio + visual sentiment."""
        from cw.lib.video_analysis import analyze_sentiment

        transcription = {
            "segments": [
                {"text": "This is amazing and wonderful!"}
            ]
        }

        visual_style = {
            "avg_brightness": 0.6,
            "avg_contrast": 0.5,
        }

        objects = {
            "classes": {"person": {"count": 2}},
            "total_objects": 2,
        }

        sentiment = analyze_sentiment(transcription, visual_style, objects)

        self.assertIn("overall_sentiment", sentiment)
        self.assertIn("overall_score", sentiment)
        self.assertIn("text_sentiment", sentiment)
        self.assertIn("visual_sentiment", sentiment)
        self.assertEqual(sentiment["overall_sentiment"], "positive")


class SceneCategorizationTestCase(TestCase):
    """Test scene categorization."""

    def test_categorize_scene_with_people(self):
        """Test categorizing a scene with people."""
        from cw.lib.video_analysis.categorization import categorize_scene

        scene = {"scene_number": 1, "start_time": 0.0, "end_time": 5.0}
        detections = [
            {"class": "person", "confidence": 0.95},
            {"class": "person", "confidence": 0.92},
        ]

        categories = categorize_scene(scene, detections)

        self.assertIn("people", categories)

    def test_categorize_scene_with_products(self):
        """Test categorizing a scene with products."""
        from cw.lib.video_analysis.categorization import categorize_scene

        scene = {"scene_number": 1, "start_time": 0.0, "end_time": 5.0}
        detections = [
            {"class": "bottle", "confidence": 0.88},
        ]

        categories = categorize_scene(scene, detections)

        self.assertIn("product", categories)

    def test_categorize_scene_with_keywords(self):
        """Test categorizing a scene with transcription keywords."""
        from cw.lib.video_analysis.categorization import categorize_scene

        scene = {"scene_number": 1, "start_time": 0.0, "end_time": 5.0}
        detections = []
        text = "This delicious food is amazing"

        categories = categorize_scene(scene, detections, text)

        self.assertIn("food", categories)

    def test_summarize_categories(self):
        """Test category summarization."""
        from cw.lib.video_analysis.categorization import summarize_categories

        categorized_scenes = [
            {"scene_number": 1, "categories": ["people", "lifestyle"]},
            {"scene_number": 2, "categories": ["people", "product"]},
            {"scene_number": 3, "categories": ["product"]},
        ]

        summary = summarize_categories(categorized_scenes)

        self.assertEqual(summary["total_scenes"], 3)
        self.assertEqual(summary["category_counts"]["people"], 2)
        self.assertEqual(summary["category_counts"]["product"], 2)
        self.assertIn("people", summary["primary_categories"])
