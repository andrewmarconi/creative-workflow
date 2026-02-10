"""Tests for JSON export functionality.

Tests cover:
- VideoProcessingResult export (single and bulk)
- AdUnitMedia export (with and without results)
- Campaign export (with all nested data)
- Field serialization (datetime, decimal, JSON, file fields)
- Export response format and headers
"""

import json
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from cw.lib.export import (
    ModelJSONEncoder,
    create_json_response,
    export_ad_unit_media_with_result,
    export_campaign_with_results,
    export_video_processing_result,
    serialize_model_instance,
)
from cw.tvspots.models import (
    AdUnitMedia,
    Campaign,
    KeyFrame,
    VideoProcessingResult,
)


class ModelJSONEncoderTestCase(TestCase):
    """Test custom JSON encoder for Django models."""

    def test_decimal_serialization(self):
        """Test that Decimal values are converted to float."""
        data = {"price": Decimal("19.99")}
        result = json.dumps(data, cls=ModelJSONEncoder)
        self.assertEqual(result, '{"price": 19.99}')

    def test_datetime_serialization(self):
        """Test that datetime values are serialized correctly."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        data = {"timestamp": dt}
        result = json.loads(json.dumps(data, cls=ModelJSONEncoder))
        self.assertIn("2024-01-15", result["timestamp"])


class SerializeModelInstanceTestCase(TestCase):
    """Test model instance serialization."""

    def setUp(self):
        """Create test campaign."""
        self.campaign = Campaign.objects.create(
            job_id="TEST-001",
            script_title="Test Campaign",
            client_name="Test Client",
            product_name="Test Product",
        )

    def test_basic_serialization(self):
        """Test basic model serialization."""
        data = serialize_model_instance(self.campaign)

        self.assertEqual(data["job_id"], "TEST-001")
        self.assertEqual(data["script_title"], "Test Campaign")
        self.assertEqual(data["client_name"], "Test Client")
        self.assertIsNotNone(data["created_at"])

    def test_exclude_fields(self):
        """Test field exclusion."""
        data = serialize_model_instance(
            self.campaign,
            exclude_fields=["product_name", "original_script_data"],
        )

        self.assertNotIn("product_name", data)
        self.assertNotIn("original_script_data", data)
        self.assertIn("job_id", data)

    def test_json_field_serialization(self):
        """Test that JSONField is serialized correctly."""
        self.campaign.original_script_data = {"key": "value", "nested": {"data": 123}}
        self.campaign.save()

        data = serialize_model_instance(self.campaign)
        self.assertEqual(data["original_script_data"]["key"], "value")
        self.assertEqual(data["original_script_data"]["nested"]["data"], 123)


class ExportVideoProcessingResultTestCase(TestCase):
    """Test VideoProcessingResult export."""

    def setUp(self):
        """Create test data."""
        self.campaign = Campaign.objects.create(
            job_id="TEST-002",
            script_title="Export Test",
            client_name="Test Client",
        )

        # Create dummy video file
        video_content = b"fake video content"
        video_file = SimpleUploadedFile(
            "test_video.mp4",
            video_content,
            content_type="video/mp4"
        )

        # Mock the video validator to avoid validation issues in tests
        with patch("cw.lib.security.VideoFileValidator"):
            self.media = AdUnitMedia.objects.create(
                campaign=self.campaign,
                video_file=video_file,
                status="completed",
                duration=30.5,
                resolution_width=1920,
                resolution_height=1080,
                frame_rate=29.97,
                audio_channels=2,
                audio_sample_rate=48000,
                file_size=1024000,
            )

        self.result = VideoProcessingResult.objects.create(
            scenes=[
                {
                    "scene_number": 1,
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "duration": 5.0,
                    "visual_description": "Opening scene",
                }
            ],
            script={
                "script_title": "Test Script",
                "scenes": [
                    {
                        "scene_number": 1,
                        "visual": "Opening",
                        "audio": {"voiceover": "Welcome"},
                    }
                ],
            },
            transcription={
                "language": "en-US",
                "confidence": 0.95,
                "segments": [{"start": 0.0, "end": 2.0, "text": "Hello"}],
            },
            visual_style={"dominant_colors": ["#FF0000"]},
            objects_summary={"total_objects": 5},
            sentiment_analysis={"overall_sentiment": "positive", "overall_score": 0.8},
            categories={"total_scenes": 1, "category_counts": {"people": 1}},
            audience_insights={"primary_audience": {"demographics": {}}},
            processing_time=45.2,
            models_used={"scene_detection": "PySceneDetect"},
        )

        # Link result to media
        self.media.result = self.result
        self.media.save()

    def test_basic_export(self):
        """Test basic result export."""
        data = export_video_processing_result(self.result)

        # Check metadata
        self.assertEqual(data["export_metadata"]["model"], "VideoProcessingResult")
        self.assertIn("export_date", data["export_metadata"])

        # Check core data
        self.assertEqual(data["id"], self.result.pk)
        self.assertEqual(len(data["scenes"]), 1)
        self.assertEqual(data["scenes"][0]["scene_number"], 1)
        self.assertEqual(data["script"]["script_title"], "Test Script")
        self.assertEqual(data["transcription"]["language"], "en-US")
        self.assertEqual(data["processing_time"], 45.2)

    def test_export_with_media_metadata(self):
        """Test export includes media metadata."""
        data = export_video_processing_result(
            self.result,
            include_media_metadata=True,
        )

        self.assertIn("media", data)
        self.assertEqual(data["media"]["id"], self.media.pk)
        self.assertEqual(data["media"]["duration"], 30.5)
        self.assertEqual(data["media"]["resolution"]["width"], 1920)
        self.assertEqual(data["media"]["resolution"]["height"], 1080)
        self.assertEqual(data["media"]["frame_rate"], 29.97)
        self.assertEqual(data["media"]["audio"]["channels"], 2)
        self.assertEqual(data["media"]["file_size"], 1024000)

    def test_export_with_keyframes(self):
        """Test export includes keyframe data."""
        # Create keyframes
        KeyFrame.objects.create(
            result=self.result,
            scene_number=1,
            timestamp=2.5,
            image=SimpleUploadedFile("frame.jpg", b"fake image", content_type="image/jpeg"),
            detected_objects=[{"label": "person", "confidence": 0.95}],
            colors=["#FF0000", "#00FF00"],
        )

        data = export_video_processing_result(
            self.result,
            include_keyframes=True,
        )

        self.assertIn("keyframes", data)
        self.assertEqual(len(data["keyframes"]), 1)
        self.assertEqual(data["keyframes"][0]["scene_number"], 1)
        self.assertEqual(data["keyframes"][0]["timestamp"], 2.5)
        self.assertEqual(len(data["keyframes"][0]["detected_objects"]), 1)
        self.assertEqual(len(data["keyframes"][0]["colors"]), 2)

    def test_export_without_keyframes(self):
        """Test export excludes keyframes when requested."""
        KeyFrame.objects.create(
            result=self.result,
            scene_number=1,
            timestamp=2.5,
            image=SimpleUploadedFile("frame.jpg", b"fake image", content_type="image/jpeg"),
        )

        data = export_video_processing_result(
            self.result,
            include_keyframes=False,
        )

        self.assertNotIn("keyframes", data)

    def test_export_type_validation(self):
        """Test that export raises TypeError for wrong model type."""
        with self.assertRaises(TypeError) as ctx:
            export_video_processing_result(self.campaign)

        self.assertIn("Expected VideoProcessingResult", str(ctx.exception))


class ExportAdUnitMediaTestCase(TestCase):
    """Test AdUnitMedia export."""

    def setUp(self):
        """Create test data."""
        self.campaign = Campaign.objects.create(
            job_id="TEST-003",
            script_title="Media Export Test",
            client_name="Test Client",
        )

        video_file = SimpleUploadedFile(
            "media_test.mp4",
            b"video data",
            content_type="video/mp4"
        )

        with patch("cw.lib.security.VideoFileValidator"):
            self.media = AdUnitMedia.objects.create(
                campaign=self.campaign,
                video_file=video_file,
                status="completed",
                duration=45.0,
                resolution_width=1280,
                resolution_height=720,
                file_size=2048000,
            )

        self.result = VideoProcessingResult.objects.create(
            scenes=[{"scene_number": 1, "start_time": 0.0}],
            script={"scenes": []},
            processing_time=30.0,
        )

        self.media.result = self.result
        self.media.save()

    def test_export_with_result(self):
        """Test media export includes processing result."""
        data = export_ad_unit_media_with_result(self.media)

        # Check metadata
        self.assertEqual(data["export_metadata"]["model"], "AdUnitMedia")

        # Check media fields
        self.assertEqual(data["id"], self.media.pk)
        self.assertEqual(data["campaign_id"], self.campaign.pk)
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["duration"], 45.0)
        self.assertEqual(data["resolution"]["width"], 1280)

        # Check processing result is nested
        self.assertIn("processing_result", data)
        self.assertEqual(data["processing_result"]["id"], self.result.pk)
        self.assertEqual(data["processing_result"]["processing_time"], 30.0)

    def test_export_without_result(self):
        """Test media export when no processing result exists."""
        with patch("cw.lib.security.VideoFileValidator"):
            media_no_result = AdUnitMedia.objects.create(
                campaign=self.campaign,
                video_file=SimpleUploadedFile("test2.mp4", b"data", content_type="video/mp4"),
                status="uploaded",
            )

        data = export_ad_unit_media_with_result(media_no_result)

        self.assertNotIn("processing_result", data)
        self.assertEqual(data["status"], "uploaded")

    def test_export_type_validation(self):
        """Test that export raises TypeError for wrong model type."""
        with self.assertRaises(TypeError) as ctx:
            export_ad_unit_media_with_result(self.result)

        self.assertIn("Expected AdUnitMedia", str(ctx.exception))


class ExportCampaignTestCase(TestCase):
    """Test Campaign export with all nested data."""

    def setUp(self):
        """Create test campaign with media and results."""
        self.campaign = Campaign.objects.create(
            job_id="TEST-004",
            script_title="Full Campaign Export",
            client_name="Test Client",
            product_name="Test Product",
            original_script_data={"version": 1},
        )

        # Create multiple media with results
        with patch("cw.lib.security.VideoFileValidator"):
            for i in range(2):
                video_file = SimpleUploadedFile(
                    f"video_{i}.mp4",
                    b"video data",
                    content_type="video/mp4"
                )

                media = AdUnitMedia.objects.create(
                    campaign=self.campaign,
                    video_file=video_file,
                    status="completed",
                    duration=30.0 + i,
                )

                result = VideoProcessingResult.objects.create(
                    scenes=[{"scene_number": i + 1}],
                    script={"title": f"Script {i}"},
                    processing_time=20.0 + i,
                )

                media.result = result
                media.save()

    def test_full_campaign_export(self):
        """Test complete campaign export."""
        data = export_campaign_with_results(self.campaign)

        # Check metadata
        self.assertEqual(data["export_metadata"]["model"], "Campaign")

        # Check campaign fields
        self.assertEqual(data["id"], self.campaign.pk)
        self.assertEqual(data["job_id"], "TEST-004")
        self.assertEqual(data["script_title"], "Full Campaign Export")
        self.assertEqual(data["original_script_data"]["version"], 1)

        # Check ad unit media
        self.assertIn("ad_unit_media", data)
        self.assertEqual(len(data["ad_unit_media"]), 2)

        # Check each media has its result
        for media_data in data["ad_unit_media"]:
            self.assertIn("processing_result", media_data)
            self.assertIn("scenes", media_data["processing_result"])

    def test_campaign_export_type_validation(self):
        """Test that export raises TypeError for wrong model type."""
        media = self.campaign.ad_unit_media.first()

        with self.assertRaises(TypeError) as ctx:
            export_campaign_with_results(media)

        self.assertIn("Expected Campaign", str(ctx.exception))


class CreateJSONResponseTestCase(TestCase):
    """Test JSON response creation."""

    def test_basic_response(self):
        """Test creating basic JSON response."""
        data = {"key": "value", "number": 123}
        response = create_json_response(data, "test-export")

        # Check headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("test-export.json", response["Content-Disposition"])

        # Check content
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["key"], "value")
        self.assertEqual(content["number"], 123)

    def test_pretty_printing(self):
        """Test pretty-printed JSON."""
        data = {"nested": {"key": "value"}}
        response = create_json_response(data, "pretty-test", pretty=True)

        content = response.content.decode("utf-8")
        # Pretty JSON should have newlines and indentation
        self.assertIn("\n", content)
        self.assertIn("  ", content)

    def test_compact_printing(self):
        """Test compact JSON without pretty printing."""
        data = {"nested": {"key": "value"}}
        response = create_json_response(data, "compact-test", pretty=False)

        content = response.content.decode("utf-8")
        # Compact JSON should be single line
        self.assertEqual(content.count("\n"), 0)

    def test_filename_extension(self):
        """Test that .json extension is added if missing."""
        response = create_json_response({}, "no-extension")
        self.assertIn("no-extension.json", response["Content-Disposition"])

        response = create_json_response({}, "has-extension.json")
        # Should not double-add extension
        self.assertIn("has-extension.json", response["Content-Disposition"])
        self.assertNotIn(".json.json", response["Content-Disposition"])

    def test_unicode_handling(self):
        """Test that Unicode characters are preserved."""
        data = {"message": "Hello 世界 🌍"}
        response = create_json_response(data, "unicode-test")

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["message"], "Hello 世界 🌍")


class IntegrationTestCase(TestCase):
    """Integration tests for complete export workflows."""

    def setUp(self):
        """Create complete test dataset."""
        self.campaign = Campaign.objects.create(
            job_id="INTEGRATION-001",
            script_title="Integration Test Campaign",
            client_name="Test Corp",
            product_name="Widget Pro",
        )

        video_file = SimpleUploadedFile(
            "integration.mp4",
            b"video content",
            content_type="video/mp4"
        )

        with patch("cw.lib.security.VideoFileValidator"):
            self.media = AdUnitMedia.objects.create(
                campaign=self.campaign,
                video_file=video_file,
                status="completed",
                duration=60.0,
                resolution_width=1920,
                resolution_height=1080,
                frame_rate=30.0,
                audio_channels=2,
                audio_sample_rate=48000,
                file_size=5120000,
            )

        self.result = VideoProcessingResult.objects.create(
            scenes=[
                {
                    "scene_number": 1,
                    "start_time": 0.0,
                    "end_time": 30.0,
                    "visual_description": "Product showcase",
                },
                {
                    "scene_number": 2,
                    "start_time": 30.0,
                    "end_time": 60.0,
                    "visual_description": "Call to action",
                },
            ],
            script={
                "script_title": "Widget Pro Launch",
                "scenes": [
                    {"scene_number": 1, "visual": "Product", "audio": {"voiceover": "Introducing"}},
                    {"scene_number": 2, "visual": "CTA", "audio": {"voiceover": "Buy now"}},
                ],
            },
            transcription={
                "language": "en-US",
                "segments": [
                    {"start": 0.0, "end": 30.0, "text": "Introducing Widget Pro"},
                    {"start": 30.0, "end": 60.0, "text": "Available now"},
                ],
            },
            visual_style={"dominant_colors": ["#0066CC", "#FFFFFF"]},
            sentiment_analysis={"overall_sentiment": "positive", "overall_score": 0.85},
            processing_time=120.5,
            models_used={"transcription": "Whisper", "object_detection": "YOLO"},
        )

        self.media.result = self.result
        self.media.save()

        # Create keyframes
        for i in range(2):
            KeyFrame.objects.create(
                result=self.result,
                scene_number=i + 1,
                timestamp=i * 30.0,
                image=SimpleUploadedFile(f"frame_{i}.jpg", b"image", content_type="image/jpeg"),
                detected_objects=[{"label": "product", "confidence": 0.9}],
                colors=["#0066CC"],
            )

    def test_full_export_and_reimport_structure(self):
        """Test that exported data has valid structure for re-import."""
        # Export campaign
        campaign_data = export_campaign_with_results(self.campaign)

        # Verify structure matches import expectations
        self.assertIn("job_id", campaign_data)
        self.assertIn("script_title", campaign_data)
        self.assertIn("ad_unit_media", campaign_data)

        # Verify media structure
        media_data = campaign_data["ad_unit_media"][0]
        self.assertIn("processing_result", media_data)

        # Verify processing result structure
        result_data = media_data["processing_result"]
        self.assertIn("scenes", result_data)
        self.assertIn("script", result_data)
        self.assertIn("transcription", result_data)
        self.assertIn("keyframes", result_data)

        # Verify data types are JSON-serializable
        json_str = json.dumps(campaign_data, cls=ModelJSONEncoder)
        reimported = json.loads(json_str)

        # Verify data integrity after round-trip
        self.assertEqual(reimported["job_id"], "INTEGRATION-001")
        self.assertEqual(len(reimported["ad_unit_media"][0]["processing_result"]["scenes"]), 2)
        self.assertEqual(len(reimported["ad_unit_media"][0]["processing_result"]["keyframes"]), 2)

    def test_export_response_download(self):
        """Test that export response is downloadable file."""
        data = export_video_processing_result(self.result)
        response = create_json_response(data, "test-download")

        # Verify headers for download
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])

        # Verify content is valid JSON
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["id"], self.result.pk)


@pytest.mark.django_db
class TestExportEdgeCases:
    """Test edge cases and error handling."""

    def test_export_result_with_no_media(self):
        """Test exporting result that has no associated media."""
        result = VideoProcessingResult.objects.create(
            scenes=[],
            script={},
            processing_time=0,
        )

        data = export_video_processing_result(result, include_media_metadata=True)

        # Should not fail, just omit media section
        assert "media" not in data or data["media"] is None

    def test_export_media_with_null_fields(self):
        """Test exporting media with null/blank optional fields."""
        campaign = Campaign.objects.create(
            job_id="NULL-TEST",
            script_title="Test",
            client_name="Client",
        )

        video_file = SimpleUploadedFile("test.mp4", b"data", content_type="video/mp4")

        with patch("cw.lib.security.VideoFileValidator"):
            media = AdUnitMedia.objects.create(
                campaign=campaign,
                video_file=video_file,
                status="uploaded",
                # All optional fields left as None/default
            )

        data = export_ad_unit_media_with_result(media)

        # Should handle None values gracefully
        assert data["duration"] is None
        assert data["resolution"] is None
        assert data["audio"] is None

    def test_export_empty_campaign(self):
        """Test exporting campaign with no media."""
        campaign = Campaign.objects.create(
            job_id="EMPTY",
            script_title="Empty Campaign",
            client_name="Client",
        )

        data = export_campaign_with_results(campaign)

        assert data["id"] == campaign.pk
        assert data["ad_unit_media"] == []
