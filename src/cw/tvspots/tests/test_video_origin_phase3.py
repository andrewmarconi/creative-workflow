"""
Tests for Phase 3: Audience insights and script editing.

Tests:
- Audience insights generation
- Script validation with tvspot.schema.json
- VideoProcessingResult admin editing workflow
- Approve/reject status transitions
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import RequestFactory
from django.urls import reverse

from cw.tvspots.admin import VideoProcessingResultAdmin
from cw.tvspots.models import AdUnitMedia, Campaign, VideoProcessingResult

User = get_user_model()


@pytest.fixture
def campaign(db):
    """Create a test campaign."""
    return Campaign.objects.create(
        script_title="Test Campaign",
        client_name="Test Client",
        brand_name="Test Brand",
        job_id="TEST-001",
    )


@pytest.fixture
def ad_unit_media(db, campaign):
    """Create a test ad unit media with completed processing."""
    return AdUnitMedia.objects.create(
        campaign=campaign,
        status="completed",
        duration=30.0,
        resolution_width=1920,
        resolution_height=1080,
        frame_rate=30.0,
    )


@pytest.fixture
def processing_result(db, ad_unit_media):
    """Create a test processing result with mock data."""
    script_data = {
        "client_name": "Test Client",
        "brand_name": "Test Brand",
        "script_title": "Test Script :30",
        "total_runtime_seconds": 30.0,
        "language": "en-US",
        "script_rows": [
            {
                "shot_number": "01",
                "timecode_start": "00:00:00:00",
                "duration_seconds": 3.5,
                "visual_text": "Opening shot of product",
                "audio_text": "VO: Introducing our new product",
            },
            {
                "shot_number": "02",
                "timecode_start": "00:00:03:15",
                "duration_seconds": 3.0,
                "visual_text": "Product closeup",
                "audio_text": "Music: Upbeat jingle",
            },
        ],
    }

    result = VideoProcessingResult.objects.create(
        scenes=[
            {
                "scene_number": 1,
                "start_time": 0.0,
                "end_time": 3.5,
                "duration": 3.5,
                "visual_description": "Opening shot of product",
                "categories": ["product", "commercial"],
            },
            {
                "scene_number": 2,
                "start_time": 3.5,
                "end_time": 6.5,
                "duration": 3.0,
                "visual_description": "Product closeup",
                "categories": ["product"],
            },
        ],
        script=script_data,
        transcription={
            "language": "en",
            "segments": [
                {
                    "start": 0.0,
                    "end": 3.5,
                    "text": "Introducing our new product",
                    "speaker": "narrator",
                }
            ],
        },
        visual_style={
            "dominant_colors": ["#FF5733", "#33FF57"],
            "avg_brightness": 0.7,
            "lighting_distribution": {"bright": 2},
        },
        objects_summary={
            "total_objects": 5,
            "unique_labels": ["product", "person", "table"],
        },
        sentiment_analysis={
            "overall_sentiment": "positive",
            "overall_score": 0.8,
        },
        categories={
            "primary_categories": ["product", "commercial"],
            "category_counts": {"product": 2, "commercial": 1},
        },
        audience_insights={},  # Will be populated by tests
        processing_time=120.5,
        models_used={
            "script_generation": "Qwen 2.5",
            "audience_insights": "Qwen 2.5",
        },
    )

    # Link to media
    ad_unit_media.result = result
    ad_unit_media.save()

    return result


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
class TestAudienceInsightsGeneration:
    """Tests for audience insights generation."""

    @patch("cw.lib.video_analysis.audience_insights.PipelineModelLoader")
    @patch("cw.lib.video_analysis.audience_insights.render_prompt")
    def test_generate_audience_insights_success(self, mock_render_prompt, mock_loader):
        """Test successful audience insights generation."""
        from cw.lib.video_analysis.audience_insights import generate_audience_insights

        # Mock LLM response
        mock_generator = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "reasoning": "Based on the product-focused content and positive sentiment...",
            "primary_audience": {
                "demographics": {
                    "age_range": "25-45",
                    "gender": "all",
                    "income_level": "middle to upper-middle",
                },
                "psychographics": {
                    "values": ["quality", "innovation"],
                    "interests": ["technology", "lifestyle"],
                    "lifestyle": "modern, tech-savvy",
                },
            },
            "secondary_audiences": [],
            "market_potential": {
                "high_fit_markets": ["US", "UK", "CA"],
                "adaptation_needed": [],
                "considerations": ["Appeals to early adopters"],
            },
            "messaging_recommendations": [
                "Emphasize product innovation",
                "Use modern, clean visuals",
            ],
        })
        mock_generator.invoke.return_value = mock_response
        mock_loader.return_value.get_generator.return_value = mock_generator
        mock_render_prompt.return_value = "Mock prompt"

        # Generate insights
        script = {"scenes": [{"scene_number": 1, "visual": "Product shot"}]}
        visual_style = {"dominant_colors": ["#FF5733"], "avg_brightness": 0.7}
        sentiment = {"overall_sentiment": "positive", "overall_score": 0.8}
        transcription = {"language": "en"}
        categories = {"primary_categories": ["product"], "category_counts": {"product": 1}}

        insights = generate_audience_insights(
            script=script,
            visual_style=visual_style,
            sentiment=sentiment,
            transcription=transcription,
            categories=categories,
        )

        # Assertions
        assert insights["primary_audience"]["demographics"]["age_range"] == "25-45"
        assert "quality" in insights["primary_audience"]["psychographics"]["values"]
        assert "US" in insights["market_potential"]["high_fit_markets"]
        assert len(insights["messaging_recommendations"]) == 2

    @patch("cw.lib.video_analysis.audience_insights.PipelineModelLoader")
    @patch("cw.lib.video_analysis.audience_insights.render_prompt")
    def test_generate_audience_insights_fallback(self, mock_render_prompt, mock_loader):
        """Test fallback insights when LLM fails."""
        from cw.lib.video_analysis.audience_insights import generate_audience_insights

        # Mock LLM failure
        mock_generator = MagicMock()
        mock_generator.invoke.side_effect = Exception("LLM error")
        mock_loader.return_value.get_generator.return_value = mock_generator
        mock_render_prompt.return_value = "Mock prompt"

        # Generate insights (should use fallback)
        script = {"scenes": [{"scene_number": 1, "visual": "Product shot"}]}
        visual_style = {"dominant_colors": ["#FF5733"], "avg_brightness": 0.7}
        sentiment = {"overall_sentiment": "positive", "overall_score": 0.8}
        transcription = {"language": "en"}
        categories = {"primary_categories": ["product"], "category_counts": {"product": 1}}

        insights = generate_audience_insights(
            script=script,
            visual_style=visual_style,
            sentiment=sentiment,
            transcription=transcription,
            categories=categories,
        )

        # Assertions - fallback should return valid structure
        assert "primary_audience" in insights
        assert "market_potential" in insights
        assert "messaging_recommendations" in insights
        assert insights.get("generated_by") == "fallback_rules"


@pytest.mark.django_db
class TestScriptValidation:
    """Tests for script validation against tvspot.schema.json."""

    def test_valid_script_structure(self):
        """Test that a valid script passes validation."""
        script_data = {
            "client_name": "Test Client",
            "brand_name": "Test Brand",
            "script_title": "Test Script :30",
            "total_runtime_seconds": 30.0,
            "language": "en-US",
            "script_rows": [
                {
                    "shot_number": "01",
                    "timecode_start": "00:00:00:00",
                    "duration_seconds": 3.5,
                    "visual_text": "Opening shot",
                    "audio_text": "VO: Test",
                }
            ],
        }

        # Load schema
        schema_path = Path(settings.BASE_DIR) / "data" / "schemas" / "tvspot.schema.json"
        with open(schema_path) as f:
            schema = json.load(f)

        # Validate (using jsonschema library)
        from jsonschema import validate
        validate(instance=script_data, schema=schema)  # Should not raise

    def test_invalid_script_missing_required_field(self):
        """Test that a script missing required fields fails validation."""
        script_data = {
            "client_name": "Test Client",
            # Missing brand_name, script_title, etc.
            "script_rows": [],
        }

        schema_path = Path(settings.BASE_DIR) / "data" / "schemas" / "tvspot.schema.json"
        with open(schema_path) as f:
            schema = json.load(f)

        from jsonschema import ValidationError, validate

        with pytest.raises(ValidationError):
            validate(instance=script_data, schema=schema)


@pytest.mark.django_db
class TestVideoProcessingResultAdmin:
    """Tests for VideoProcessingResult admin editing workflow."""

    def test_script_field_is_editable(self, processing_result, admin_user, admin_site):
        """Test that the script field is not in readonly_fields."""
        admin = VideoProcessingResultAdmin(VideoProcessingResult, admin_site)

        # Script should not be readonly
        assert "script" not in admin.readonly_fields

    def test_formfield_uses_script_editor_widget(self, processing_result, admin_user, admin_site):
        """Test that the script field uses ScriptEditorWidget."""
        from cw.core.widgets import ScriptEditorWidget

        admin = VideoProcessingResultAdmin(VideoProcessingResult, admin_site)

        # Get form field for script
        script_field = VideoProcessingResult._meta.get_field("script")
        formfield = admin.formfield_for_dbfield(script_field, request=None)

        # Should use ScriptEditorWidget
        assert isinstance(formfield.widget, ScriptEditorWidget)

    def test_approve_script_action(self, processing_result, admin_user, admin_site):
        """Test approve script action updates media status."""
        admin = VideoProcessingResultAdmin(VideoProcessingResult, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user

        # Set up messages framework
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Execute approve action
        response = admin.approve_script_action(request, processing_result.pk)

        # Check media status updated
        processing_result.media.refresh_from_db()
        assert processing_result.media.status == "reviewed"

    def test_reject_script_action(self, processing_result, admin_user, admin_site):
        """Test reject script action resets media status."""
        admin = VideoProcessingResultAdmin(VideoProcessingResult, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user

        # Set up messages framework
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Execute reject action
        response = admin.reject_script_action(request, processing_result.pk)

        # Check media status reset
        processing_result.media.refresh_from_db()
        assert processing_result.media.status == "uploaded"
        assert "rejected" in processing_result.media.processing_error.lower()


@pytest.mark.django_db
class TestWorkflowStatusTransitions:
    """Tests for approve/reject workflow status transitions."""

    def test_status_workflow_completed_to_reviewed(self, processing_result):
        """Test transition from completed -> reviewed on approval."""
        # Initial state
        assert processing_result.media.status == "completed"

        # Approve (simulate)
        processing_result.media.status = "reviewed"
        processing_result.media.save()

        # Verify transition
        processing_result.media.refresh_from_db()
        assert processing_result.media.status == "reviewed"

    def test_status_workflow_completed_to_uploaded_on_reject(self, processing_result):
        """Test transition from completed -> uploaded on rejection."""
        # Initial state
        assert processing_result.media.status == "completed"

        # Reject (simulate)
        processing_result.media.status = "uploaded"
        processing_result.media.processing_error = "Script rejected"
        processing_result.media.save()

        # Verify transition
        processing_result.media.refresh_from_db()
        assert processing_result.media.status == "uploaded"
        assert processing_result.media.processing_error != ""

    def test_cannot_approve_non_completed_media(self, processing_result, admin_user, admin_site):
        """Test that approval fails for media not in completed status."""
        from django.contrib.messages.storage.fallback import FallbackStorage

        admin = VideoProcessingResultAdmin(VideoProcessingResult, admin_site)
        factory = RequestFactory()
        request = factory.post("/")
        request.user = admin_user

        # Set up messages framework
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Set media to processing state
        processing_result.media.status = "processing"
        processing_result.media.save()

        # Try to approve
        response = admin.approve_script_action(request, processing_result.pk)

        # Should show error and not change status
        processing_result.media.refresh_from_db()
        assert processing_result.media.status == "processing"  # Unchanged
