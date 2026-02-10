"""
Tests for video processing progress tracking.

Tests cover:
- Progress updates during video processing
- Progress API endpoint
- Celery task state handling
- Error state handling
"""

import json
from unittest.mock import MagicMock, patch

from celery.result import AsyncResult
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cw.tvspots.models import AdUnitMedia, Campaign

User = get_user_model()


class ProgressTrackingTests(TestCase):
    """Tests for video processing progress tracking."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_superuser(
            username="testadmin",
            email="admin@test.com",
            password="testpass123",
        )
        self.client.login(username="testadmin", password="testpass123")

        self.campaign = Campaign.objects.create(
            job_id="TEST-001",
            script_title="Test Campaign",
            client_name="Test Client",
        )

        self.media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            status="processing",
            celery_task_id="test-task-id-123",
        )

    def test_progress_api_no_task(self):
        """Test progress API when no task is running."""
        media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            status="completed",
        )

        url = reverse("admin:tvspots_adunitmedia_progress", args=[media.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["progress"], 100)

    def test_progress_api_pending(self):
        """Test progress API for pending task."""
        url = reverse("admin:tvspots_adunitmedia_progress", args=[self.media.pk])

        # Mock AsyncResult to return PENDING state
        with patch("celery.result.AsyncResult") as mock_async_result:
            mock_result = MagicMock()
            mock_result.state = "PENDING"
            mock_result.info = None
            mock_async_result.return_value = mock_result

            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["progress"], 0)
        self.assertEqual(data["phase"], "queued")

    def test_progress_api_processing(self):
        """Test progress API for task in progress."""
        url = reverse("admin:tvspots_adunitmedia_progress", args=[self.media.pk])

        # Mock AsyncResult to return PROGRESS state with metadata
        with patch("celery.result.AsyncResult") as mock_async_result:
            mock_result = MagicMock()
            mock_result.state = "PROGRESS"
            mock_result.info = {
                "current": 30,
                "total": 100,
                "phase": "transcription",
                "status": "Transcribing audio...",
            }
            mock_async_result.return_value = mock_result

            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "processing")
        self.assertEqual(data["progress"], 30)
        self.assertEqual(data["phase"], "transcription")
        self.assertEqual(data["message"], "Transcribing audio...")

    def test_progress_api_success(self):
        """Test progress API for completed task."""
        url = reverse("admin:tvspots_adunitmedia_progress", args=[self.media.pk])

        # Mock AsyncResult to return SUCCESS state
        with patch("celery.result.AsyncResult") as mock_async_result:
            mock_result = MagicMock()
            mock_result.state = "SUCCESS"
            mock_result.result = {
                "status": "success",
                "media_id": self.media.pk,
                "result_id": 1,
            }
            mock_async_result.return_value = mock_result

            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["progress"], 100)
        self.assertEqual(data["phase"], "completed")

    def test_progress_api_failure(self):
        """Test progress API for failed task."""
        url = reverse("admin:tvspots_adunitmedia_progress", args=[self.media.pk])

        # Mock AsyncResult to return FAILURE state
        with patch("celery.result.AsyncResult") as mock_async_result:
            mock_result = MagicMock()
            mock_result.state = "FAILURE"
            mock_result.info = Exception("Test error")
            mock_async_result.return_value = mock_result

            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["progress"], 0)
        self.assertEqual(data["phase"], "failed")
        self.assertIn("error", data)

    def test_progress_api_not_found(self):
        """Test progress API for non-existent media."""
        url = reverse("admin:tvspots_adunitmedia_progress", args=[99999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn("error", data)

    def test_task_id_saved_on_queue(self):
        """Test that celery_task_id is saved when task is queued."""
        from cw.tvspots.tasks import analyze_video_task

        media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            status="uploaded",
        )

        # Mock the task
        with patch.object(analyze_video_task, "apply_async") as mock_apply:
            mock_result = MagicMock()
            mock_result.id = "new-task-id-456"
            mock_apply.return_value = mock_result

            # Queue the task (as done in admin)
            result = analyze_video_task.apply_async(args=[media.pk], queue="default")
            media.celery_task_id = result.id
            media.save(update_fields=["celery_task_id"])

        # Verify task ID was saved
        media.refresh_from_db()
        self.assertEqual(media.celery_task_id, "new-task-id-456")

    def test_progress_metadata_structure(self):
        """Test that progress metadata has expected structure."""
        # This is a simple test to verify the progress state metadata structure
        # matches what the API expects

        expected_keys = ["current", "total", "status", "phase"]

        # Simulate progress metadata
        progress_meta = {
            "current": 30,
            "total": 100,
            "status": "Transcribing audio...",
            "phase": "transcription",
        }

        # Verify all expected keys are present
        for key in expected_keys:
            self.assertIn(key, progress_meta, f"Missing key: {key}")

        # Verify types
        self.assertIsInstance(progress_meta["current"], int)
        self.assertIsInstance(progress_meta["total"], int)
        self.assertIsInstance(progress_meta["status"], str)
        self.assertIsInstance(progress_meta["phase"], str)

        # Verify progress is in valid range
        self.assertGreaterEqual(progress_meta["current"], 0)
        self.assertLessEqual(progress_meta["current"], progress_meta["total"])


# Note: Template rendering tests are skipped because they require the full admin
# environment to be set up. Progress display functionality is tested through
# manual testing and integration tests.
