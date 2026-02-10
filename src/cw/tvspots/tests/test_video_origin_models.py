"""
Unit tests for video origin extraction models.

Tests cover:
- AdUnitMedia model and status transitions
- VideoProcessingResult model and data validation
- KeyFrame model and relationships
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from cw.tvspots.models import AdUnitMedia, Campaign, KeyFrame, VideoProcessingResult


class AdUnitMediaModelTestCase(TestCase):
    """Test AdUnitMedia model functionality."""

    def setUp(self):
        """Create test campaign and media objects."""
        self.campaign = Campaign.objects.create(
            job_id="TEST-001",
            client_name="Test Client",
            script_title="Test Campaign",
        )

    def test_create_ad_unit_media(self):
        """Test creating AdUnitMedia with minimal fields."""
        # Create fake video file
        video_file = SimpleUploadedFile(
            "test_video.mp4",
            b"fake video content",
            content_type="video/mp4",
        )

        media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            video_file=video_file,
        )

        self.assertEqual(media.status, "pending")
        self.assertEqual(media.campaign, self.campaign)
        self.assertIsNone(media.result)
        self.assertIsNone(media.video_ad_unit)

    def test_status_transitions(self):
        """Test status field transitions through processing lifecycle."""
        video_file = SimpleUploadedFile("test.mp4", b"content")
        media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            video_file=video_file,
        )

        # Pending → Uploaded
        media.status = "uploaded"
        media.save()
        self.assertEqual(media.status, "uploaded")

        # Uploaded → Processing
        media.status = "processing"
        media.processing_started_at = timezone.now()
        media.save()
        self.assertEqual(media.status, "processing")
        self.assertIsNotNone(media.processing_started_at)

        # Processing → Completed
        media.status = "completed"
        media.processing_completed_at = timezone.now()
        media.save()
        self.assertEqual(media.status, "completed")
        self.assertIsNotNone(media.processing_completed_at)

    def test_failed_status_with_error(self):
        """Test recording processing failures."""
        video_file = SimpleUploadedFile("test.mp4", b"content")
        media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            video_file=video_file,
            status="processing",
        )

        # Mark as failed with error message
        media.status = "failed"
        media.processing_error = "Test error: scene detection failed"
        media.processing_completed_at = timezone.now()
        media.save()

        self.assertEqual(media.status, "failed")
        self.assertIn("scene detection failed", media.processing_error)
        self.assertIsNotNone(media.processing_completed_at)

    def test_metadata_fields(self):
        """Test video metadata storage."""
        video_file = SimpleUploadedFile("test.mp4", b"content")
        media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            video_file=video_file,
            duration=30.5,
            resolution_width=1920,
            resolution_height=1080,
            frame_rate=29.97,
            audio_channels=2,
            audio_sample_rate=48000,
            file_size=5242880,  # 5 MB
        )

        self.assertEqual(media.duration, 30.5)
        self.assertEqual(media.resolution_width, 1920)
        self.assertEqual(media.resolution_height, 1080)
        self.assertAlmostEqual(media.frame_rate, 29.97, places=2)
        self.assertEqual(media.audio_channels, 2)
        self.assertEqual(media.audio_sample_rate, 48000)
        self.assertEqual(media.file_size, 5242880)


class VideoProcessingResultModelTestCase(TestCase):
    """Test VideoProcessingResult model functionality."""

    def test_create_processing_result(self):
        """Test creating VideoProcessingResult with complete data."""
        result = VideoProcessingResult.objects.create(
            scenes=[
                {
                    "scene_number": 1,
                    "start_time": 0.0,
                    "end_time": 5.2,
                    "duration": 5.2,
                    "start_frame": 0,
                    "end_frame": 156,
                }
            ],
            script={
                "scenes": [
                    {
                        "scene_number": 1,
                        "duration": 5.2,
                        "visual": "Scene 1 visual description",
                        "audio": {
                            "voiceover": "Test voiceover",
                            "music": "",
                            "sfx": "",
                        },
                        "action": "",
                        "products": [],
                        "sentiment": "",
                    }
                ]
            },
            transcription={
                "language": "en",
                "confidence": 0.95,
                "segments": [
                    {
                        "start": 0.5,
                        "end": 3.2,
                        "text": "Test transcription",
                        "speaker": "narrator",
                        "confidence": 0.96,
                    }
                ],
            },
            processing_time=15.3,
            models_used={
                "scene_detection": "PySceneDetect",
                "transcription": "Whisper Large v3",
                "script_generation": "Basic (MVP)",
            },
        )

        self.assertEqual(len(result.scenes), 1)
        self.assertEqual(result.scenes[0]["scene_number"], 1)
        self.assertEqual(len(result.script["scenes"]), 1)
        self.assertEqual(result.transcription["language"], "en")
        self.assertEqual(result.processing_time, 15.3)
        self.assertIn("Whisper Large v3", result.models_used["transcription"])

    def test_optional_analysis_fields(self):
        """Test optional analysis fields can be empty."""
        result = VideoProcessingResult.objects.create(
            scenes=[],
            script={},
            transcription={},
            visual_style={},
            objects_summary={},
            sentiment_analysis={},
            categories=[],
            audience_insights={},
            processing_time=10.0,
        )

        self.assertEqual(result.scenes, [])
        self.assertEqual(result.script, {})
        self.assertEqual(result.visual_style, {})
        self.assertEqual(result.categories, [])

    def test_relationship_to_media(self):
        """Test OneToOne relationship with AdUnitMedia."""
        campaign = Campaign.objects.create(
            job_id="TEST-002",
            client_name="Test Client",
            script_title="Test Campaign",
        )
        video_file = SimpleUploadedFile("test.mp4", b"content")

        media = AdUnitMedia.objects.create(
            campaign=campaign,
            video_file=video_file,
        )

        result = VideoProcessingResult.objects.create(
            scenes=[],
            script={},
            transcription={},
            processing_time=5.0,
        )

        # Link result to media
        media.result = result
        media.save()

        # Verify relationship
        self.assertEqual(media.result, result)
        self.assertEqual(result.media, media)


class KeyFrameModelTestCase(TestCase):
    """Test KeyFrame model functionality."""

    def setUp(self):
        """Create test result and media objects."""
        campaign = Campaign.objects.create(
            job_id="TEST-003",
            client_name="Test Client",
            script_title="Test Campaign",
        )
        video_file = SimpleUploadedFile("test.mp4", b"content")

        media = AdUnitMedia.objects.create(
            campaign=campaign,
            video_file=video_file,
        )

        self.result = VideoProcessingResult.objects.create(
            scenes=[],
            script={},
            transcription={},
            processing_time=5.0,
        )

        media.result = self.result
        media.save()

    def test_create_keyframe(self):
        """Test creating KeyFrame with minimal fields."""
        # Create fake image
        image = SimpleUploadedFile(
            "frame_001.jpg",
            b"fake image content",
            content_type="image/jpeg",
        )

        keyframe = KeyFrame.objects.create(
            result=self.result,
            scene_number=1,
            timestamp=2.5,
            image=image,
        )

        self.assertEqual(keyframe.scene_number, 1)
        self.assertEqual(keyframe.timestamp, 2.5)
        self.assertEqual(keyframe.result, self.result)

    def test_keyframe_with_detected_objects(self):
        """Test KeyFrame with detected objects data."""
        image = SimpleUploadedFile("frame_002.jpg", b"content")

        keyframe = KeyFrame.objects.create(
            result=self.result,
            scene_number=1,
            timestamp=3.0,
            image=image,
            detected_objects=[
                {"class": "person", "confidence": 0.95, "bbox": [100, 200, 300, 400]},
                {"class": "bottle", "confidence": 0.87, "bbox": [500, 300, 600, 500]},
            ],
        )

        self.assertEqual(len(keyframe.detected_objects), 2)
        self.assertEqual(keyframe.detected_objects[0]["class"], "person")
        self.assertEqual(keyframe.detected_objects[1]["class"], "bottle")

    def test_keyframe_with_colors(self):
        """Test KeyFrame with dominant colors."""
        image = SimpleUploadedFile("frame_003.jpg", b"content")

        keyframe = KeyFrame.objects.create(
            result=self.result,
            scene_number=2,
            timestamp=10.5,
            image=image,
            colors=["#FF5733", "#3357FF", "#33FF57"],
        )

        self.assertEqual(len(keyframe.colors), 3)
        self.assertIn("#FF5733", keyframe.colors)

    def test_multiple_keyframes_per_result(self):
        """Test creating multiple keyframes for one result."""
        keyframes = []
        for i in range(5):
            image = SimpleUploadedFile(f"frame_{i:03d}.jpg", b"content")
            keyframe = KeyFrame.objects.create(
                result=self.result,
                scene_number=i + 1,  # Different scene_number for each (unique constraint)
                timestamp=i * 2.0,
                image=image,
            )
            keyframes.append(keyframe)

        # Verify all keyframes are linked to the same result
        result_keyframes = KeyFrame.objects.filter(result=self.result)
        self.assertEqual(result_keyframes.count(), 5)

        # Verify timestamps are correct
        timestamps = [kf.timestamp for kf in result_keyframes.order_by("timestamp")]
        self.assertEqual(timestamps, [0.0, 2.0, 4.0, 6.0, 8.0])
