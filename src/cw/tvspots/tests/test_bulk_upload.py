"""
Unit tests for bulk video upload functionality.

Tests cover:
- Bulk upload view access and permissions
- Multiple file validation (size, format, MIME type)
- AdUnitMedia creation for valid files
- Task queuing for video processing
- Error handling for invalid files
"""

from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse

from cw.tvspots.admin import CampaignAdmin
from cw.tvspots.models import AdUnitMedia, Campaign

User = get_user_model()


class BulkVideoUploadTestCase(TestCase):
    """Test bulk video upload functionality."""

    def setUp(self):
        """Create test campaign, admin user, and request factory."""
        self.campaign = Campaign.objects.create(
            job_id="TEST-BULK-001",
            client_name="Test Client",
            script_title="Bulk Upload Test Campaign",
        )

        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="password123",
        )

        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.campaign_admin = CampaignAdmin(Campaign, self.admin_site)

    def test_bulk_upload_action_in_detail_actions(self):
        """Test that bulk_upload_videos_action is registered in actions_detail."""
        self.assertIn("bulk_upload_videos_action", self.campaign_admin.actions_detail)

    def test_bulk_upload_url_registered(self):
        """Test that bulk upload URL is registered."""
        urls = self.campaign_admin.get_urls()
        url_names = [url.name for url in urls if hasattr(url, 'name')]
        self.assertIn("tvspots_campaign_bulk_upload_videos", url_names)

    def test_bulk_upload_action_redirects(self):
        """Test that bulk_upload_videos_action redirects to the correct URL."""
        request = self.factory.get("/")
        request.user = self.user

        response = self.campaign_admin.bulk_upload_videos_action(request, self.campaign.pk)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse(
            "admin:tvspots_campaign_bulk_upload_videos",
            args=[self.campaign.pk],
        )
        self.assertEqual(response.url, expected_url)

    def test_bulk_upload_view_renders_form(self):
        """Test that bulk upload view renders the upload form."""
        request = self.factory.get("/")
        request.user = self.user

        # Mock admin_site.each_context to return minimal context
        with patch.object(self.admin_site, 'each_context', return_value={}):
            response = self.campaign_admin.bulk_upload_videos_view(request, self.campaign.pk)

        self.assertEqual(response.status_code, 200)
        # Render the template response before accessing content
        response.render()
        self.assertIn(b"Bulk Upload Videos", response.content)
        self.assertIn(self.campaign.script_title.encode(), response.content)

    @patch("cw.tvspots.tasks.analyze_video_task")
    def test_single_valid_video_upload(self, mock_task):
        """Test uploading a single valid video file."""
        # Create a valid video file
        video_file = SimpleUploadedFile(
            "test_video.mp4",
            b"fake video content",
            content_type="video/mp4",
        )

        request = self.factory.post("/", {"video_files": [video_file]})
        request.user = self.user
        request.FILES.setlist("video_files", [video_file])
        request._messages = []  # Mock messages framework

        # Mock messages framework
        with patch("cw.tvspots.admin.messages"):
            response = self.campaign_admin.bulk_upload_videos_view(request, self.campaign.pk)

        # Check redirect to campaign change page
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/campaign/{self.campaign.pk}/change/", response.url)

        # Check AdUnitMedia was created
        media = AdUnitMedia.objects.filter(campaign=self.campaign).first()
        self.assertIsNotNone(media)
        self.assertEqual(media.status, "uploaded")

        # Check task was queued
        mock_task.apply_async.assert_called_once()
        call_args = mock_task.apply_async.call_args
        self.assertEqual(call_args[1]["args"], [media.pk])
        self.assertEqual(call_args[1]["queue"], "default")

    @patch("cw.tvspots.tasks.analyze_video_task")
    def test_multiple_valid_videos_upload(self, mock_task):
        """Test uploading multiple valid video files."""
        # Create multiple valid video files
        video_files = [
            SimpleUploadedFile(f"test_video_{i}.mp4", b"fake content", content_type="video/mp4")
            for i in range(3)
        ]

        request = self.factory.post("/")
        request.user = self.user
        request.FILES.setlist("video_files", video_files)

        with patch("cw.tvspots.admin.messages"):
            response = self.campaign_admin.bulk_upload_videos_view(request, self.campaign.pk)

        # Check all AdUnitMedia were created
        media_count = AdUnitMedia.objects.filter(campaign=self.campaign).count()
        self.assertEqual(media_count, 3)

        # Check all tasks were queued
        self.assertEqual(mock_task.apply_async.call_count, 3)

    @patch("cw.tvspots.tasks.analyze_video_task")
    def test_oversized_file_rejected(self, mock_task):
        """Test that files exceeding size limit are rejected."""
        # Create a file larger than 500 MB (mock size)
        oversized_file = SimpleUploadedFile(
            "huge_video.mp4",
            b"x" * (501 * 1024 * 1024),  # 501 MB
            content_type="video/mp4",
        )

        request = self.factory.post("/")
        request.user = self.user
        request.FILES.setlist("video_files", [oversized_file])

        with patch("cw.tvspots.admin.messages") as mock_messages:
            response = self.campaign_admin.bulk_upload_videos_view(request, self.campaign.pk)

        # Check no AdUnitMedia was created
        media_count = AdUnitMedia.objects.filter(campaign=self.campaign).count()
        self.assertEqual(media_count, 0)

        # Check no task was queued
        mock_task.apply_async.assert_not_called()

        # Check error message was shown
        mock_messages.error.assert_called()

    @patch("cw.tvspots.tasks.analyze_video_task")
    def test_invalid_extension_rejected(self, mock_task):
        """Test that files with invalid extensions are rejected."""
        invalid_file = SimpleUploadedFile(
            "test_video.txt",
            b"fake content",
            content_type="text/plain",
        )

        request = self.factory.post("/")
        request.user = self.user
        request.FILES.setlist("video_files", [invalid_file])

        with patch("cw.tvspots.admin.messages") as mock_messages:
            response = self.campaign_admin.bulk_upload_videos_view(request, self.campaign.pk)

        # Check no AdUnitMedia was created
        media_count = AdUnitMedia.objects.filter(campaign=self.campaign).count()
        self.assertEqual(media_count, 0)

        # Check error message was shown
        mock_messages.error.assert_called()

    @patch("cw.tvspots.tasks.analyze_video_task")
    def test_mixed_valid_invalid_files(self, mock_task):
        """Test uploading mix of valid and invalid files."""
        files = [
            SimpleUploadedFile("valid1.mp4", b"content", content_type="video/mp4"),
            SimpleUploadedFile("invalid.txt", b"content", content_type="text/plain"),
            SimpleUploadedFile("valid2.mp4", b"content", content_type="video/mp4"),
        ]

        request = self.factory.post("/")
        request.user = self.user
        request.FILES.setlist("video_files", files)

        with patch("cw.tvspots.admin.messages") as mock_messages:
            response = self.campaign_admin.bulk_upload_videos_view(request, self.campaign.pk)

        # Check only valid AdUnitMedia were created
        media_count = AdUnitMedia.objects.filter(campaign=self.campaign).count()
        self.assertEqual(media_count, 2)

        # Check only valid files queued tasks
        self.assertEqual(mock_task.apply_async.call_count, 2)

        # Check both error and success messages were shown
        mock_messages.error.assert_called()
        mock_messages.success.assert_called()

    def test_no_files_submitted(self):
        """Test error when no files are submitted."""
        request = self.factory.post("/")
        request.user = self.user
        request.FILES.setlist("video_files", [])

        with patch("cw.tvspots.admin.messages") as mock_messages:
            response = self.campaign_admin.bulk_upload_videos_view(request, self.campaign.pk)

        # Check redirect back to upload form
        expected_url = reverse(
            "admin:tvspots_campaign_bulk_upload_videos",
            args=[self.campaign.pk],
        )
        self.assertEqual(response.url, expected_url)

        # Check error message
        mock_messages.error.assert_called()

    @patch("cw.tvspots.tasks.analyze_video_task")
    def test_supported_video_formats(self, mock_task):
        """Test that all supported video formats are accepted."""
        formats = [
            ("video.mp4", "video/mp4"),
            ("video.mov", "video/quicktime"),
            ("video.avi", "video/x-msvideo"),
            ("video.mkv", "video/x-matroska"),
            ("video.webm", "video/webm"),
        ]

        for filename, mime_type in formats:
            video_file = SimpleUploadedFile(
                filename,
                b"fake content",
                content_type=mime_type,
            )

            request = self.factory.post("/")
            request.user = self.user
            request.FILES.setlist("video_files", [video_file])

            with patch("cw.tvspots.admin.messages"):
                response = self.campaign_admin.bulk_upload_videos_view(
                    request, self.campaign.pk
                )

        # Check all formats were accepted
        media_count = AdUnitMedia.objects.filter(campaign=self.campaign).count()
        self.assertEqual(media_count, len(formats))
