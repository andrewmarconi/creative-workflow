"""
Unit tests for video analysis Celery task.

Tests cover:
- analyze_video_task execution flow
- Error handling and retry logic
- Status transitions and result creation
"""

from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from cw.tvspots.models import AdUnitMedia, Campaign, VideoProcessingResult
from cw.tvspots.tasks import _generate_basic_script, analyze_video_task


class GenerateBasicScriptTestCase(TestCase):
    """Test _generate_basic_script helper function."""

    def test_generate_script_from_scenes_and_transcription(self):
        """Test basic script generation from scenes and transcription."""
        scenes = [
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 5.0,
                "duration": 5.0,
                "start_frame": 0,
                "end_frame": 150,
            },
            {
                "scene_number": 2,
                "start_time": 5.0,
                "end_time": 10.0,
                "duration": 5.0,
                "start_frame": 150,
                "end_frame": 300,
            },
        ]

        transcription = {
            "language": "en",
            "segments": [
                {"start": 0.5, "end": 3.0, "text": "First segment"},
                {"start": 3.5, "end": 4.8, "text": "Second segment"},
                {"start": 5.5, "end": 8.0, "text": "Third segment"},
            ],
        }

        script = _generate_basic_script(scenes, transcription)

        self.assertIn("scenes", script)
        self.assertEqual(len(script["scenes"]), 2)

        # First scene should have first two segments
        self.assertEqual(script["scenes"][0]["scene_number"], 1)
        self.assertIn("First segment", script["scenes"][0]["audio"]["voiceover"])
        self.assertIn("Second segment", script["scenes"][0]["audio"]["voiceover"])

        # Second scene should have third segment
        self.assertEqual(script["scenes"][1]["scene_number"], 2)
        self.assertIn("Third segment", script["scenes"][1]["audio"]["voiceover"])

    def test_generate_script_with_no_audio(self):
        """Test script generation when scene has no matching transcription."""
        scenes = [
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 5.0,
                "duration": 5.0,
                "start_frame": 0,
                "end_frame": 150,
            }
        ]

        transcription = {"language": "en", "segments": []}

        script = _generate_basic_script(scenes, transcription)

        self.assertEqual(len(script["scenes"]), 1)
        self.assertEqual(script["scenes"][0]["audio"]["voiceover"], "")

    def test_generate_script_scene_structure(self):
        """Test that generated script scenes have correct structure."""
        scenes = [
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 3.0,
                "duration": 3.0,
                "start_frame": 0,
                "end_frame": 90,
            }
        ]

        transcription = {
            "language": "en",
            "segments": [{"start": 1.0, "end": 2.0, "text": "Test"}],
        }

        script = _generate_basic_script(scenes, transcription)

        scene = script["scenes"][0]
        self.assertEqual(scene["scene_number"], 1)
        self.assertEqual(scene["duration"], 3.0)
        self.assertIn("visual", scene)
        self.assertIn("audio", scene)
        self.assertIn("voiceover", scene["audio"])
        self.assertIn("music", scene["audio"])
        self.assertIn("sfx", scene["audio"])
        self.assertEqual(scene["audio"]["music"], "")
        self.assertEqual(scene["audio"]["sfx"], "")
        self.assertIn("action", scene)
        self.assertIn("products", scene)
        self.assertIn("sentiment", scene)


class AnalyzeVideoTaskTestCase(TestCase):
    """Test analyze_video_task Celery task."""

    def setUp(self):
        """Create test campaign and media."""
        self.campaign = Campaign.objects.create(
            job_id="TEST-004",
            client_name="Test Client",
            script_title="Test Campaign",
        )

        video_file = SimpleUploadedFile("test.mp4", b"fake video content")
        self.media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            video_file=video_file,
            status="uploaded",
        )

    @patch("cw.lib.video_analysis.transcribe_audio")
    @patch("cw.lib.video_analysis.detect_scenes")
    @patch("cw.lib.video_analysis.extract_video_metadata")
    def test_analyze_video_task_success(
        self, mock_extract_metadata, mock_detect_scenes, mock_transcribe
    ):
        """Test successful video analysis task execution."""
        # Mock metadata extraction
        mock_extract_metadata.return_value = {
            "duration": 30.0,
            "width": 1920,
            "height": 1080,
            "frame_rate": 29.97,
            "audio_channels": 2,
            "sample_rate": 48000,
            "file_size": 5242880,
        }

        # Mock scene detection
        mock_detect_scenes.return_value = [
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 15.0,
                "duration": 15.0,
                "start_frame": 0,
                "end_frame": 450,
            },
            {
                "scene_number": 2,
                "start_time": 15.0,
                "end_time": 30.0,
                "duration": 15.0,
                "start_frame": 450,
                "end_frame": 900,
            },
        ]

        # Mock transcription
        mock_transcribe.return_value = {
            "language": "en",
            "confidence": 0.95,
            "segments": [
                {
                    "start": 0.5,
                    "end": 5.0,
                    "text": "Test voiceover",
                    "speaker": "narrator",
                    "confidence": 0.96,
                }
            ],
        }

        # Execute task
        result = analyze_video_task(self.media.id)

        # Verify task result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["media_id"], self.media.id)
        self.assertIn("result_id", result)
        self.assertIn("processing_time", result)

        # Verify media was updated
        self.media.refresh_from_db()
        self.assertEqual(self.media.status, "completed")
        self.assertIsNotNone(self.media.result)
        self.assertEqual(self.media.duration, 30.0)
        self.assertEqual(self.media.resolution_width, 1920)
        self.assertEqual(self.media.resolution_height, 1080)

        # Verify result was created
        processing_result = VideoProcessingResult.objects.get(id=result["result_id"])
        self.assertEqual(len(processing_result.scenes), 2)
        self.assertEqual(len(processing_result.script["scenes"]), 2)
        self.assertEqual(processing_result.transcription["language"], "en")

    @patch("cw.lib.video_analysis.extract_video_metadata")
    def test_analyze_video_task_failure(self, mock_extract_metadata):
        """Test video analysis task failure handling."""
        # Mock extraction raising an error
        mock_extract_metadata.side_effect = Exception("Test error: metadata extraction failed")

        # Mock the task request to simulate max retries reached
        # This prevents the task from trying to retry and instead returns the failure result
        mock_request = Mock()
        mock_request.retries = 3  # Equal to max_retries

        # Replace the task's request object
        original_max_retries = analyze_video_task.max_retries
        analyze_video_task.max_retries = 0  # Disable retries for this test

        try:
            # Execute task
            result = analyze_video_task(self.media.id)

            # Verify task result indicates failure
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["media_id"], self.media.id)
            self.assertIn("error", result)
            self.assertIn("metadata extraction failed", result["error"])

            # Verify media status was updated
            self.media.refresh_from_db()
            self.assertEqual(self.media.status, "failed")
            self.assertIn("metadata extraction failed", self.media.processing_error)
        finally:
            # Restore original max_retries
            analyze_video_task.max_retries = original_max_retries

    @patch("cw.lib.video_analysis.transcribe_audio")
    @patch("cw.lib.video_analysis.detect_scenes")
    @patch("cw.lib.video_analysis.extract_video_metadata")
    def test_analyze_video_task_status_transitions(
        self, mock_extract_metadata, mock_detect_scenes, mock_transcribe
    ):
        """Test that task properly updates media status through processing lifecycle."""
        # Setup mocks
        mock_extract_metadata.return_value = {
            "duration": 15.0,
            "width": 1280,
            "height": 720,
            "frame_rate": 24.0,
            "audio_channels": 2,
            "sample_rate": 44100,
            "file_size": 1048576,
        }

        mock_detect_scenes.return_value = [
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 15.0,
                "duration": 15.0,
                "start_frame": 0,
                "end_frame": 360,
            }
        ]

        mock_transcribe.return_value = {
            "language": "en",
            "confidence": 0.90,
            "segments": [],
        }

        # Initial status
        self.assertEqual(self.media.status, "uploaded")

        # Execute task
        analyze_video_task(self.media.id)

        # Verify final status
        self.media.refresh_from_db()
        self.assertEqual(self.media.status, "completed")
        self.assertIsNotNone(self.media.processing_started_at)
        self.assertIsNotNone(self.media.processing_completed_at)

    @patch("cw.lib.video_analysis.transcribe_audio")
    @patch("cw.lib.video_analysis.detect_scenes")
    @patch("cw.lib.video_analysis.extract_video_metadata")
    def test_analyze_video_task_creates_result_with_models_used(
        self, mock_extract_metadata, mock_detect_scenes, mock_transcribe
    ):
        """Test that task records which models were used for processing."""
        # Setup mocks
        mock_extract_metadata.return_value = {
            "duration": 10.0,
            "width": 1920,
            "height": 1080,
            "frame_rate": 30.0,
            "audio_channels": 2,
            "sample_rate": 48000,
            "file_size": 2097152,
        }

        mock_detect_scenes.return_value = [
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 10.0,
                "duration": 10.0,
                "start_frame": 0,
                "end_frame": 300,
            }
        ]

        mock_transcribe.return_value = {
            "language": "en",
            "confidence": 0.92,
            "segments": [],
        }

        # Execute task
        result = analyze_video_task(self.media.id)

        # Verify models_used was recorded
        processing_result = VideoProcessingResult.objects.get(id=result["result_id"])
        self.assertIn("scene_detection", processing_result.models_used)
        self.assertIn("transcription", processing_result.models_used)
        self.assertIn("script_generation", processing_result.models_used)
        self.assertEqual(processing_result.models_used["scene_detection"], "PySceneDetect")
        self.assertEqual(processing_result.models_used["transcription"], "Whisper Large v3")
        self.assertEqual(processing_result.models_used["script_generation"], "Basic (MVP)")

    @patch("cw.lib.video_analysis.transcribe_audio")
    @patch("cw.lib.video_analysis.detect_scenes")
    @patch("cw.lib.video_analysis.extract_video_metadata")
    def test_analyze_video_task_processing_time(
        self, mock_extract_metadata, mock_detect_scenes, mock_transcribe
    ):
        """Test that task calculates and stores processing time."""
        # Setup mocks
        mock_extract_metadata.return_value = {
            "duration": 5.0,
            "width": 1280,
            "height": 720,
            "frame_rate": 24.0,
            "audio_channels": 2,
            "sample_rate": 44100,
            "file_size": 524288,
        }

        mock_detect_scenes.return_value = [
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 5.0,
                "duration": 5.0,
                "start_frame": 0,
                "end_frame": 120,
            }
        ]

        mock_transcribe.return_value = {"language": "en", "confidence": 0.88, "segments": []}

        # Execute task
        result = analyze_video_task(self.media.id)

        # Verify processing time was recorded
        processing_result = VideoProcessingResult.objects.get(id=result["result_id"])
        self.assertIsNotNone(processing_result.processing_time)
        self.assertGreater(processing_result.processing_time, 0.0)
        self.assertLess(processing_result.processing_time, 60.0)  # Should be < 1 minute
