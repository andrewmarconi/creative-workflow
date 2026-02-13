"""
Unit tests for ControlNet model classes and ModelFactory.

Tests:
- SDXLControlNetModel and SD15ControlNetModel configuration
- _build_pipeline_kwargs ControlNet parameter injection
- _build_metadata ControlNet info inclusion
- ModelFactory dispatching for ControlNet pipeline types
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from cw.lib.models import ModelFactory


class ModelFactoryControlNetTestCase(TestCase):
    """Test ModelFactory dispatches ControlNet pipeline types correctly."""

    def test_sdxl_controlnet_pipeline_type(self):
        """StableDiffusionXLControlNetPipeline creates SDXLControlNetModel."""
        config = {"pipeline": "StableDiffusionXLControlNetPipeline", "settings": {}}
        model = ModelFactory.create_model(config, "test-model-path")

        from cw.lib.models.sdxl_controlnet import SDXLControlNetModel

        self.assertIsInstance(model, SDXLControlNetModel)

    def test_sd15_controlnet_pipeline_type(self):
        """StableDiffusionControlNetPipeline creates SD15ControlNetModel."""
        config = {"pipeline": "StableDiffusionControlNetPipeline", "settings": {}}
        model = ModelFactory.create_model(config, "test-model-path")

        from cw.lib.models.sd15_controlnet import SD15ControlNetModel

        self.assertIsInstance(model, SD15ControlNetModel)

    def test_unknown_pipeline_raises(self):
        """Unknown pipeline type raises ValueError."""
        config = {"pipeline": "DoesNotExist", "settings": {}}

        with self.assertRaises(ValueError):
            ModelFactory.create_model(config, "test-path")

    def test_sdxl_pipeline_not_controlnet(self):
        """StableDiffusionXLPipeline creates SDXLModel, not ControlNet variant."""
        config = {"pipeline": "StableDiffusionXLPipeline", "settings": {}}
        model = ModelFactory.create_model(config, "test-path")

        from cw.lib.models.sdxl import SDXLModel

        self.assertIsInstance(model, SDXLModel)


class SDXLControlNetModelTestCase(TestCase):
    """Test SDXLControlNetModel configuration and kwargs building."""

    def _make_model(self, **extra_settings):
        from cw.lib.models.sdxl_controlnet import SDXLControlNetModel

        settings = {"controlnet_path": "test/controlnet", **extra_settings}
        config = {
            "pipeline": "StableDiffusionXLControlNetPipeline",
            "settings": settings,
        }
        return SDXLControlNetModel(config, "test/base-model")

    def test_controlnet_path_from_settings(self):
        """controlnet_path is read from model settings."""
        model = self._make_model(controlnet_path="diffusers/controlnet-canny-sdxl-1.0")
        self.assertEqual(model.controlnet_path, "diffusers/controlnet-canny-sdxl-1.0")

    def test_build_pipeline_kwargs_injects_control_image(self):
        """_build_pipeline_kwargs adds control image to kwargs."""
        model = self._make_model()
        model.pipeline = MagicMock()  # Fake loaded pipeline

        control_img = MagicMock()
        params = {
            "prompt": "test prompt",
            "control_image": control_img,
            "conditioning_scale": 0.7,
            "guidance_end": 0.8,
        }

        kwargs = model._build_pipeline_kwargs(params, progress_callback=None)

        self.assertIs(kwargs["image"], control_img)
        self.assertEqual(kwargs["controlnet_conditioning_scale"], 0.7)
        self.assertEqual(kwargs["control_guidance_end"], 0.8)

    def test_build_pipeline_kwargs_without_control_image(self):
        """_build_pipeline_kwargs works without control image (text-only fallback)."""
        model = self._make_model()
        model.pipeline = MagicMock()

        params = {"prompt": "test prompt"}
        kwargs = model._build_pipeline_kwargs(params, progress_callback=None)

        self.assertNotIn("image", kwargs)
        self.assertNotIn("controlnet_conditioning_scale", kwargs)

    def test_build_metadata_includes_controlnet(self):
        """_build_metadata includes controlnet section."""
        model = self._make_model(controlnet_path="test/cn")

        params = {"conditioning_scale": 0.5, "guidance_end": 0.9}
        metadata = model._build_metadata(params)

        self.assertIn("controlnet", metadata)
        self.assertEqual(metadata["controlnet"]["path"], "test/cn")
        self.assertEqual(metadata["controlnet"]["conditioning_scale"], 0.5)
        self.assertEqual(metadata["controlnet"]["guidance_end"], 0.9)


class SD15ControlNetModelTestCase(TestCase):
    """Test SD15ControlNetModel configuration and kwargs building."""

    def _make_model(self, **extra_settings):
        from cw.lib.models.sd15_controlnet import SD15ControlNetModel

        settings = {"controlnet_path": "test/controlnet", **extra_settings}
        config = {
            "pipeline": "StableDiffusionControlNetPipeline",
            "settings": settings,
        }
        return SD15ControlNetModel(config, "test/base-model")

    def test_controlnet_path_from_settings(self):
        """controlnet_path is read from model settings."""
        model = self._make_model(controlnet_path="lllyasviel/control_v11p_sd15_lineart")
        self.assertEqual(model.controlnet_path, "lllyasviel/control_v11p_sd15_lineart")

    def test_build_pipeline_kwargs_injects_control_image(self):
        """_build_pipeline_kwargs adds control image to kwargs."""
        model = self._make_model()
        model.pipeline = MagicMock()

        control_img = MagicMock()
        params = {
            "prompt": "test prompt",
            "control_image": control_img,
            "conditioning_scale": 1.0,
        }

        kwargs = model._build_pipeline_kwargs(params, progress_callback=None)

        self.assertIs(kwargs["image"], control_img)
        self.assertEqual(kwargs["controlnet_conditioning_scale"], 1.0)
