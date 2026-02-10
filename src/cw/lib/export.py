"""Export utilities for JSON serialization of Django models.

Handles complex field types (DateTimeField, JSONField, FileField, etc.)
and provides helper functions for exporting video processing results.
"""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.http import HttpResponse
from django.utils import timezone


class ModelJSONEncoder(DjangoJSONEncoder):
    """Extended JSON encoder for Django models with additional field types."""

    def default(self, obj):
        """Handle additional field types."""
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


def serialize_model_instance(
    instance: Model,
    exclude_fields: Optional[List[str]] = None,
    include_related: bool = False,
) -> Dict[str, Any]:
    """Serialize a single model instance to dictionary.

    Args:
        instance: Django model instance to serialize
        exclude_fields: Field names to exclude from serialization
        include_related: Whether to include related object data (FK, M2M)

    Returns:
        Dictionary representation of the model instance
    """
    exclude_fields = exclude_fields or []
    data = {}

    # Get all fields
    for field in instance._meta.get_fields():
        if field.name in exclude_fields:
            continue

        # Skip reverse relations unless explicitly requested
        if field.is_relation and field.auto_created and not include_related:
            continue

        try:
            # Handle different field types
            if field.many_to_many:
                if include_related:
                    # Serialize M2M as list of PKs or objects
                    related_manager = getattr(instance, field.name)
                    data[field.name] = [obj.pk for obj in related_manager.all()]
            elif field.is_relation:
                if include_related:
                    # Serialize FK as PK or nested object
                    related_obj = getattr(instance, field.name, None)
                    if related_obj:
                        data[field.name] = related_obj.pk
                        # Optionally add related object's string representation
                        data[f"{field.name}_display"] = str(related_obj)
                else:
                    # Just include FK ID
                    fk_value = getattr(instance, f"{field.name}_id", None)
                    if fk_value is not None:
                        data[f"{field.name}_id"] = fk_value
            elif hasattr(field, "get_attname"):
                # Regular field
                value = getattr(instance, field.name, None)

                # Handle file fields
                if hasattr(field, "storage"):
                    if value:
                        data[field.name] = str(value)
                    else:
                        data[field.name] = None
                else:
                    data[field.name] = value

        except Exception:
            # Skip fields that can't be serialized
            continue

    return data


def export_video_processing_result(
    result,
    include_keyframes: bool = True,
    include_media_metadata: bool = True,
) -> Dict[str, Any]:
    """Export a VideoProcessingResult as JSON-serializable dict.

    Args:
        result: VideoProcessingResult instance
        include_keyframes: Whether to include keyframe data
        include_media_metadata: Whether to include video metadata from AdUnitMedia

    Returns:
        Complete export data structure
    """
    from cw.tvspots.models import VideoProcessingResult

    if not isinstance(result, VideoProcessingResult):
        raise TypeError(f"Expected VideoProcessingResult, got {type(result).__name__}")

    data = {
        "export_metadata": {
            "export_date": timezone.now().isoformat(),
            "export_version": "1.0",
            "model": "VideoProcessingResult",
        },
        "id": result.pk,
        "created_at": result.created_at.isoformat(),
        "updated_at": result.updated_at.isoformat(),
    }

    # Core processing results
    data["scenes"] = result.scenes
    data["script"] = result.script
    data["transcription"] = result.transcription
    data["visual_style"] = result.visual_style
    data["objects_summary"] = result.objects_summary
    data["sentiment_analysis"] = result.sentiment_analysis
    data["categories"] = result.categories
    data["audience_insights"] = result.audience_insights

    # Processing metadata
    data["processing_time"] = result.processing_time
    data["models_used"] = result.models_used

    # Media metadata (if requested and available)
    if include_media_metadata and hasattr(result, "media") and result.media:
        media = result.media
        data["media"] = {
            "id": media.pk,
            "campaign_id": media.campaign_id,
            "video_file": str(media.video_file) if media.video_file else None,
            "duration": float(media.duration) if media.duration else None,
            "resolution": {
                "width": media.resolution_width,
                "height": media.resolution_height,
            } if media.resolution_width and media.resolution_height else None,
            "frame_rate": float(media.frame_rate) if media.frame_rate else None,
            "audio": {
                "channels": media.audio_channels,
                "sample_rate": media.audio_sample_rate,
            } if media.audio_channels else None,
            "file_size": media.file_size,
        }

    # Keyframes (if requested)
    if include_keyframes:
        keyframes = []
        for kf in result.key_frames.all().order_by("scene_number", "timestamp"):
            keyframes.append({
                "scene_number": kf.scene_number,
                "timestamp": kf.timestamp,
                "image": str(kf.image) if kf.image else None,
                "detected_objects": kf.detected_objects,
                "colors": kf.colors,
            })
        data["keyframes"] = keyframes

    return data


def export_ad_unit_media_with_result(media) -> Dict[str, Any]:
    """Export AdUnitMedia with its processing result.

    Args:
        media: AdUnitMedia instance

    Returns:
        Complete export data structure including video metadata and processing results
    """
    from cw.tvspots.models import AdUnitMedia

    if not isinstance(media, AdUnitMedia):
        raise TypeError(f"Expected AdUnitMedia, got {type(media).__name__}")

    data = {
        "export_metadata": {
            "export_date": timezone.now().isoformat(),
            "export_version": "1.0",
            "model": "AdUnitMedia",
        },
        "id": media.pk,
        "campaign_id": media.campaign_id,
        "status": media.status,
        "video_file": str(media.video_file) if media.video_file else None,
        "duration": float(media.duration) if media.duration else None,
        "resolution": {
            "width": media.resolution_width,
            "height": media.resolution_height,
        } if media.resolution_width and media.resolution_height else None,
        "frame_rate": float(media.frame_rate) if media.frame_rate else None,
        "audio": {
            "channels": media.audio_channels,
            "sample_rate": media.audio_sample_rate,
        } if media.audio_channels else None,
        "file_size": media.file_size,
        "processing_started_at": media.processing_started_at.isoformat() if media.processing_started_at else None,
        "processing_completed_at": media.processing_completed_at.isoformat() if media.processing_completed_at else None,
        "processing_error": media.processing_error,
        "created_at": media.created_at.isoformat(),
        "updated_at": media.updated_at.isoformat(),
    }

    # Include processing result if available
    if media.result:
        data["processing_result"] = export_video_processing_result(
            media.result,
            include_keyframes=True,
            include_media_metadata=False,  # Already included above
        )

    # Include created VideoAdUnit reference if available
    if media.video_ad_unit:
        data["video_ad_unit_id"] = media.video_ad_unit.pk
        data["video_ad_unit_code"] = media.video_ad_unit.code

    return data


def export_campaign_with_results(campaign) -> Dict[str, Any]:
    """Export entire Campaign with all ad unit media and processing results.

    Args:
        campaign: Campaign instance

    Returns:
        Complete export data structure
    """
    from cw.tvspots.models import Campaign

    if not isinstance(campaign, Campaign):
        raise TypeError(f"Expected Campaign, got {type(campaign).__name__}")

    data = {
        "export_metadata": {
            "export_date": timezone.now().isoformat(),
            "export_version": "1.0",
            "model": "Campaign",
        },
        "id": campaign.pk,
        "job_id": campaign.job_id,
        "script_title": campaign.script_title,
        "client_name": campaign.client_name,
        "product_name": campaign.product_name,
        "brand_id": campaign.brand_id,
        "original_script_data": campaign.original_script_data,
        "created_at": campaign.created_at.isoformat(),
        "updated_at": campaign.updated_at.isoformat(),
    }

    # Export all ad unit media with their results
    media_list = []
    for media in campaign.ad_unit_media.all().select_related("result", "video_ad_unit"):
        media_list.append(export_ad_unit_media_with_result(media))
    data["ad_unit_media"] = media_list

    return data


def create_json_response(
    data: Union[Dict, List],
    filename: str,
    pretty: bool = True,
) -> HttpResponse:
    """Create HttpResponse with JSON data as downloadable file.

    Args:
        data: Data to serialize as JSON
        filename: Filename for download (without extension)
        pretty: Whether to pretty-print JSON

    Returns:
        HttpResponse with JSON attachment
    """
    # Ensure filename ends with .json
    if not filename.endswith(".json"):
        filename = f"{filename}.json"

    # Serialize to JSON
    if pretty:
        json_str = json.dumps(data, cls=ModelJSONEncoder, indent=2, ensure_ascii=False)
    else:
        json_str = json.dumps(data, cls=ModelJSONEncoder, ensure_ascii=False)

    # Create response
    response = HttpResponse(json_str, content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response
