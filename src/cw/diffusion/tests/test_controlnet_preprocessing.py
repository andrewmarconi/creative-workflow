"""
Unit tests for ControlNet preprocessing utility.

Tests the preprocessing dispatcher, detector cache, and error handling.
All controlnet_aux detectors are mocked to avoid GPU/model dependencies.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from PIL import Image

from cw.lib import controlnet_preprocessing


class PreprocessImageTestCase(TestCase):
    """Test preprocess_image() dispatcher."""

    def setUp(self):
        # Clear detector cache between tests
        controlnet_preprocessing.clear_detector_cache()
        # Create a small test image
        self.test_image = Image.new("RGB", (640, 480), color="red")

    def tearDown(self):
        controlnet_preprocessing.clear_detector_cache()

    @patch("cw.lib.controlnet_preprocessing._get_detector")
    def test_preprocess_lineart(self, mock_get_detector):
        """preprocess_image dispatches to lineart detector correctly."""
        mock_detector = MagicMock()
        mock_detector.return_value = Image.new("L", (1024, 1024))
        mock_get_detector.return_value = mock_detector

        result = controlnet_preprocessing.preprocess_image(
            self.test_image, "lineart", detect_resolution=512, image_resolution=1024
        )

        mock_get_detector.assert_called_once_with("lineart")
        mock_detector.assert_called_once_with(
            self.test_image.convert("RGB"),
            detect_resolution=512,
            image_resolution=1024,
        )
        self.assertIsInstance(result, Image.Image)

    @patch("cw.lib.controlnet_preprocessing._get_detector")
    def test_preprocess_canny_uses_thresholds(self, mock_get_detector):
        """Canny preprocessing passes low/high threshold kwargs."""
        mock_detector = MagicMock()
        mock_detector.return_value = Image.new("L", (1024, 1024))
        mock_get_detector.return_value = mock_detector

        controlnet_preprocessing.preprocess_image(
            self.test_image,
            "canny",
            detect_resolution=384,
            image_resolution=768,
            low_threshold=50,
            high_threshold=150,
        )

        mock_detector.assert_called_once_with(
            self.test_image.convert("RGB"),
            low_threshold=50,
            high_threshold=150,
            detect_resolution=384,
            image_resolution=768,
        )

    @patch("cw.lib.controlnet_preprocessing._get_detector")
    def test_preprocess_depth(self, mock_get_detector):
        """Depth preprocessing dispatches correctly."""
        mock_detector = MagicMock()
        mock_detector.return_value = Image.new("L", (512, 512))
        mock_get_detector.return_value = mock_detector

        result = controlnet_preprocessing.preprocess_image(
            self.test_image, "depth"
        )

        mock_get_detector.assert_called_once_with("depth")
        self.assertIsInstance(result, Image.Image)

    def test_preprocess_converts_to_rgb(self):
        """Input images are converted to RGB before processing."""
        rgba_image = Image.new("RGBA", (100, 100))

        with patch("cw.lib.controlnet_preprocessing._get_detector") as mock_get:
            mock_det = MagicMock()
            mock_det.return_value = Image.new("L", (100, 100))
            mock_get.return_value = mock_det

            controlnet_preprocessing.preprocess_image(rgba_image, "lineart")

            # The detector should receive an RGB image
            call_args = mock_det.call_args
            input_img = call_args[0][0]
            self.assertEqual(input_img.mode, "RGB")


class GetDetectorTestCase(TestCase):
    """Test _get_detector() factory and caching."""

    def setUp(self):
        controlnet_preprocessing.clear_detector_cache()

    def tearDown(self):
        controlnet_preprocessing.clear_detector_cache()

    def test_unknown_control_type_raises(self):
        """Unknown control type raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            controlnet_preprocessing._get_detector("unknown_type")

        self.assertIn("unknown_type", str(ctx.exception))
        self.assertIn("Supported:", str(ctx.exception))

    @patch("cw.lib.controlnet_preprocessing.CannyDetector", create=True)
    def test_canny_detector_creation(self, _):
        """Canny detector is created from controlnet_aux."""
        with patch("cw.lib.controlnet_preprocessing._detector_cache", {}):
            with patch(
                "cw.lib.controlnet_preprocessing.CannyDetector",
                create=True,
            ) as mock_canny_cls:
                # Patch the import inside _get_detector
                mock_detector = MagicMock()
                with patch.dict(
                    "sys.modules",
                    {"controlnet_aux": MagicMock(CannyDetector=lambda: mock_detector)},
                ):
                    # Re-clear cache to ensure fresh state
                    controlnet_preprocessing._detector_cache.clear()
                    detector = controlnet_preprocessing._get_detector("canny")
                    self.assertIsNotNone(detector)

    def test_detector_cache_hit(self):
        """Second call for same type returns cached detector."""
        fake_detector = MagicMock()
        controlnet_preprocessing._detector_cache["lineart"] = fake_detector

        result = controlnet_preprocessing._get_detector("lineart")
        self.assertIs(result, fake_detector)


class ClearDetectorCacheTestCase(TestCase):
    """Test clear_detector_cache()."""

    def test_clear_empties_cache(self):
        """clear_detector_cache removes all cached detectors."""
        controlnet_preprocessing._detector_cache["a"] = MagicMock()
        controlnet_preprocessing._detector_cache["b"] = MagicMock()

        controlnet_preprocessing.clear_detector_cache()

        self.assertEqual(len(controlnet_preprocessing._detector_cache), 0)
