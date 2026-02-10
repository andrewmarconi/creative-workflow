"""
Tests for Phase 4: Integration with adaptation pipeline.

Tests:
- Create Origin VideoAdUnit action with comprehensive validation
- Error handling and retry logic
- Integration with adaptation workflow
- Performance optimizations
- End-to-end flow from upload to adaptation
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from cw.tvspots.admin import AdUnitMediaAdmin
from cw.tvspots.models import AdUnitMedia, AdUnitScriptRow, Campaign, VideoAdUnit, VideoProcessingResult

User = get_user_model()


@pytest.fixture
def campaign(db):
    """Create a test campaign."""
    return Campaign.objects.create(
        script_title="Test Campaign :30",
        client_name="Test Client",
        brand_name="Test Brand",
        job_id="TEST-001",
    )


@pytest.fixture
def completed_media_with_result(db, campaign):
    """Create a completed media with processing result."""
    # Create media
    media = AdUnitMedia.objects.create(
        campaign=campaign,
        status="completed",
        duration=30.0,
        resolution_width=1920,
        resolution_height=1080,
        frame_rate=30.0,
    )

    # Create processing result with valid script
    script_data = {
        "client_name": "Test Client",
        "brand_name": "Test Brand",
        "script_title": "Test Script :30",
        "total_runtime_seconds": 30.0,
        "language": "en-US",
        "job_id": "TEST-001",
        "script_rows": [
            {
                "shot_number": "01",
                "timecode_start": "00:00:00:00",
                "duration_seconds": 3.5,
                "visual_text": "Opening shot: Product on table in bright sunlight",
                "audio_text": "VO: Introducing our revolutionary new product",
            },
            {
                "shot_number": "02",
                "timecode_start": "00:00:03:15",
                "duration_seconds": 3.0,
                "visual_text": "Close-up: Product features highlighted",
                "audio_text": "Music: Upbeat jingle with energetic tempo",
            },
            {
                "shot_number": "03",
                "timecode_start": "00:00:06:15",
                "duration_seconds": 2.5,
                "visual_text": "Wide shot: Happy customer using product",
                "audio_text": "SFX: Product activation sound",
            },
        ],
    }

    result = VideoProcessingResult.objects.create(
        scenes=[
            {"scene_number": 1, "start_time": 0.0, "end_time": 3.5, "duration": 3.5},
            {"scene_number": 2, "start_time": 3.5, "end_time": 6.5, "duration": 3.0},
            {"scene_number": 3, "start_time": 6.5, "end_time": 9.0, "duration": 2.5},
        ],
        script=script_data,
        transcription={"language": "en", "segments": []},
        visual_style={"dominant_colors": ["#FF5733"]},
        objects_summary={"total_objects": 5},
        sentiment_analysis={"overall_sentiment": "positive"},
        categories={"primary_categories": ["product"]},
        audience_insights={
            "primary_audience": {
                "demographics": {"age_range": "25-45"},
                "psychographics": {"values": ["quality"]},
            }
        },
        processing_time=120.5,
    )

    media.result = result
    media.save()

    return media


@pytest.fixture
def completed_media_with_scenes_format(db, campaign):
    """Create a completed media with old 'scenes' script format (Phase 1/2 compatibility)."""
    media = AdUnitMedia.objects.create(
        campaign=campaign,
        status="completed",
        duration=30.0,
    )

    # Old format with 'scenes' array instead of 'script_rows'
    script_data = {
        "scenes": [
            {
                "scene_number": 1,
                "visual": "Opening shot",
                "audio": {"voiceover": "Introducing our product"},
            },
            {
                "scene_number": 2,
                "visual": "Product closeup",
                "audio": {"voiceover": "Features and benefits"},
            },
        ]
    }

    result = VideoProcessingResult.objects.create(
        scenes=[],
        script=script_data,
        transcription={"language": "en", "segments": []},
        visual_style={},
        objects_summary={},
        sentiment_analysis={},
        categories={},
        audience_insights={},
        processing_time=100.0,
    )

    media.result = result
    media.save()

    return media


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password",
    )


@pytest.fixture
def admin_site():
    """Create an admin site."""
    return AdminSite()


@pytest.mark.django_db
class TestCreateOriginVideoAdUnit:
    """Tests for Create Origin VideoAdUnit action."""

    def test_create_origin_from_valid_script_rows(
        self, completed_media_with_result, admin_user, admin_site
    ):
        """Test successful creation with script_rows format."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Execute action
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Verify VideoAdUnit created
        completed_media_with_result.refresh_from_db()
        assert completed_media_with_result.video_ad_unit is not None

        ad_unit = completed_media_with_result.video_ad_unit
        assert ad_unit.ad_unit_type == "VIDEO"
        assert ad_unit.origin_or_adaptation == "ORIGIN"
        assert ad_unit.code == f"ORIGIN-{completed_media_with_result.id:04d}"
        assert ad_unit.status == "completed"

        # Verify script rows created
        script_rows = AdUnitScriptRow.objects.filter(ad_unit=ad_unit).order_by("order_index")
        assert script_rows.count() == 3

        # Check first row
        row1 = script_rows[0]
        assert row1.shot_number == "01"
        assert "Opening shot" in row1.visual_text
        assert "Introducing" in row1.audio_text

        # Verify media status updated
        assert completed_media_with_result.status == "reviewed"

    def test_create_origin_from_scenes_format(
        self, completed_media_with_scenes_format, admin_user, admin_site
    ):
        """Test backward compatibility with old 'scenes' format."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Execute action
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_scenes_format.pk
        )

        # Verify VideoAdUnit created
        completed_media_with_scenes_format.refresh_from_db()
        assert completed_media_with_scenes_format.video_ad_unit is not None

        # Verify script rows created from scenes
        ad_unit = completed_media_with_scenes_format.video_ad_unit
        script_rows = AdUnitScriptRow.objects.filter(ad_unit=ad_unit)
        assert script_rows.count() == 2

    def test_cannot_create_from_non_completed_status(
        self, completed_media_with_result, admin_user, admin_site
    ):
        """Test that creation fails for media not in completed status."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Set status to processing
        completed_media_with_result.status = "processing"
        completed_media_with_result.save()

        # Try to create
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Should not create VideoAdUnit
        completed_media_with_result.refresh_from_db()
        assert completed_media_with_result.video_ad_unit is None

    def test_cannot_create_duplicate_ad_unit(
        self, completed_media_with_result, admin_user, admin_site
    ):
        """Test that duplicate creation is prevented."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Create first time
        admin.create_origin_ad_unit_action(request, completed_media_with_result.pk)

        # Try to create again
        completed_media_with_result.refresh_from_db()
        first_ad_unit_id = completed_media_with_result.video_ad_unit.pk

        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Should still have only one VideoAdUnit
        completed_media_with_result.refresh_from_db()
        assert completed_media_with_result.video_ad_unit.pk == first_ad_unit_id
        assert VideoAdUnit.objects.filter(
            origin_or_adaptation="ORIGIN",
            campaign=completed_media_with_result.campaign
        ).count() == 1

    def test_error_handling_missing_result(
        self, completed_media_with_result, admin_user, admin_site
    ):
        """Test error handling when processing result is missing."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Remove result
        completed_media_with_result.result = None
        completed_media_with_result.save()

        # Try to create
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Should not create VideoAdUnit
        completed_media_with_result.refresh_from_db()
        assert completed_media_with_result.video_ad_unit is None

    def test_error_handling_invalid_script_structure(
        self, completed_media_with_result, admin_user, admin_site
    ):
        """Test error handling when script has invalid structure."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Set invalid script structure
        completed_media_with_result.result.script = {"invalid": "structure"}
        completed_media_with_result.result.save()

        # Try to create
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Should not create VideoAdUnit
        completed_media_with_result.refresh_from_db()
        assert completed_media_with_result.video_ad_unit is None


@pytest.mark.django_db
class TestAdaptationWorkflowIntegration:
    """Tests for integration with adaptation workflow."""

    def test_success_message_includes_adaptation_link(
        self, completed_media_with_result, admin_user, admin_site
    ):
        """Test that success message includes link to create adaptation."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Execute action
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Check messages
        message_list = list(messages)
        assert len(message_list) > 0
        success_message = str(message_list[0])
        assert "Create Adaptation" in success_message
        assert "source_ad_unit=" in success_message

    def test_redirects_to_created_ad_unit(
        self, completed_media_with_result, admin_user, admin_site
    ):
        """Test that action redirects to the created VideoAdUnit."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Execute action
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Check redirect
        completed_media_with_result.refresh_from_db()
        expected_url = reverse(
            "admin:tvspots_videoadunit_change",
            args=[completed_media_with_result.video_ad_unit.pk],
        )
        assert response.url == expected_url


@pytest.mark.django_db
class TestComprehensiveLogging:
    """Tests for logging and monitoring."""

    @patch("cw.tvspots.admin.logging.getLogger")
    def test_logs_creation_success(
        self, mock_logger, completed_media_with_result, admin_user, admin_site
    ):
        """Test that successful creation is logged."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Execute action
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Verify logging calls
        logger = mock_logger.return_value
        assert logger.info.called
        # Should log start, creation, script rows, and completion

    @patch("cw.tvspots.admin.logging.getLogger")
    def test_logs_validation_errors(
        self, mock_logger, completed_media_with_result, admin_user, admin_site
    ):
        """Test that validation errors are logged."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Remove result to trigger error
        completed_media_with_result.result = None
        completed_media_with_result.save()

        # Execute action
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Verify error logging
        logger = mock_logger.return_value
        assert logger.error.called


@pytest.mark.django_db
class TestEndToEndFlow:
    """Integration tests for complete video upload to adaptation flow."""

    def test_complete_workflow(
        self, completed_media_with_result, admin_user, admin_site
    ):
        """Test complete flow: upload → process → review → create origin → ready for adaptation."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = AdUnitMediaAdmin(AdUnitMedia, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Initial state: media completed with result
        assert completed_media_with_result.status == "completed"
        assert completed_media_with_result.result is not None
        assert completed_media_with_result.video_ad_unit is None

        # Create origin VideoAdUnit
        response = admin.create_origin_ad_unit_action(
            request, completed_media_with_result.pk
        )

        # Verify final state
        completed_media_with_result.refresh_from_db()
        assert completed_media_with_result.status == "reviewed"
        assert completed_media_with_result.video_ad_unit is not None

        # Verify VideoAdUnit ready for adaptation
        ad_unit = completed_media_with_result.video_ad_unit
        assert ad_unit.origin_or_adaptation == "ORIGIN"
        assert ad_unit.status == "completed"
        assert AdUnitScriptRow.objects.filter(ad_unit=ad_unit).count() == 3

        # Verify can be used as source for adaptation
        assert ad_unit.pk is not None  # Has valid ID for FK reference
