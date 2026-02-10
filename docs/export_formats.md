# Video Processing Export Formats

This document describes the JSON export formats for video processing results in the tvspots app.

## Overview

The export system provides comprehensive JSON exports of video processing data, including:

- **VideoProcessingResult** - Individual processing results with scenes, transcription, visual analysis, etc.
- **AdUnitMedia** - Video metadata with associated processing results
- **Campaign** - Complete campaigns with all media and processing results

All exports include metadata, use timezone-aware timestamps, and handle complex Django field types (JSONField, FileField, etc.).

## Export Locations

### Admin UI

Exports are available via admin actions:

1. **VideoProcessingResultAdmin**
   - Detail page: "Export as JSON" button
   - List page: "Export selected results as JSON" bulk action

2. **AdUnitMediaAdmin**
   - Detail page: "Export as JSON" button
   - List page: "Export selected media as JSON" bulk action

3. **CampaignAdmin**
   - Detail page: "Export Campaign with Results" button

### Programmatic Export

```python
from cw.lib.export import (
    export_video_processing_result,
    export_ad_unit_media_with_result,
    export_campaign_with_results,
    create_json_response,
)

# Export a single result
result = VideoProcessingResult.objects.get(pk=1)
data = export_video_processing_result(result, include_keyframes=True)

# Export media with result
media = AdUnitMedia.objects.get(pk=1)
data = export_ad_unit_media_with_result(media)

# Export entire campaign
campaign = Campaign.objects.get(pk=1)
data = export_campaign_with_results(campaign)

# Create downloadable response
response = create_json_response(data, "export-filename", pretty=True)
```

## Export Formats

### VideoProcessingResult

```json
{
  "export_metadata": {
    "export_date": "2026-02-10T12:30:45.123456+00:00",
    "export_version": "1.0",
    "model": "VideoProcessingResult"
  },
  "id": 123,
  "created_at": "2026-02-10T10:15:30.000000+00:00",
  "updated_at": "2026-02-10T10:20:15.000000+00:00",
  "scenes": [
    {
      "scene_number": 1,
      "start_time": 0.0,
      "end_time": 5.5,
      "duration": 5.5,
      "visual_description": "Opening scene with product reveal",
      "objects_detected": ["product", "person"],
      "colors": ["#FF5733", "#33FF57"],
      "lighting": "warm, golden hour",
      "camera_angle": "medium shot",
      "sentiment": "positive"
    }
  ],
  "script": {
    "script_title": "Product Launch",
    "total_runtime_seconds": 30,
    "script_rows": [
      {
        "shot_number": "01",
        "visual_text": "Wide shot of product on pedestal",
        "audio_text": "VO: Introducing the future of innovation"
      }
    ]
  },
  "transcription": {
    "language": "en-US",
    "confidence": 0.95,
    "segments": [
      {
        "start": 0.5,
        "end": 3.2,
        "text": "Introducing the future of innovation",
        "speaker": "narrator",
        "confidence": 0.96
      }
    ]
  },
  "visual_style": {
    "dominant_colors": ["#FF5733", "#3357FF", "#33FF57"],
    "avg_brightness": 0.58,
    "avg_contrast": 0.45,
    "lighting_distribution": {"soft": 3, "harsh": 1, "dramatic": 1},
    "camera_work": {
      "avg_scene_duration": 4.5,
      "total_scenes": 12,
      "pacing": "fast"
    }
  },
  "objects_summary": {
    "total_objects": 15,
    "classes": {
      "person": {"count": 5, "avg_confidence": 0.92},
      "product": {"count": 3, "avg_confidence": 0.88}
    },
    "most_common": ["person", "product"]
  },
  "sentiment_analysis": {
    "overall_sentiment": "positive",
    "overall_score": 0.65,
    "confidence": 0.72,
    "text_sentiment": {
      "sentiment": "positive",
      "score": 0.75
    },
    "visual_sentiment": {
      "sentiment": "positive",
      "score": 0.6
    }
  },
  "categories": {
    "total_scenes": 10,
    "category_counts": {
      "people": 6,
      "product": 4,
      "lifestyle": 3
    },
    "primary_categories": ["people", "product", "lifestyle"]
  },
  "audience_insights": {
    "primary_audience": {
      "demographics": {"age_range": "25-45"},
      "psychographics": {"values": ["innovation", "quality"]}
    },
    "market_potential": {
      "high_fit_markets": ["US", "UK", "DE"]
    }
  },
  "processing_time": 45.2,
  "models_used": {
    "scene_detection": "PySceneDetect",
    "transcription": "Whisper Large v3",
    "object_detection": "YOLO v8x",
    "sentiment": "keyword-based"
  },
  "media": {
    "id": 456,
    "campaign_id": 789,
    "video_file": "ad_unit_media/2026/02/video.mp4",
    "duration": 30.5,
    "resolution": {
      "width": 1920,
      "height": 1080
    },
    "frame_rate": 29.97,
    "audio": {
      "channels": 2,
      "sample_rate": 48000
    },
    "file_size": 1024000
  },
  "keyframes": [
    {
      "scene_number": 1,
      "timestamp": 2.5,
      "image": "keyframes/2026/02/frame_001.jpg",
      "detected_objects": [
        {"label": "product", "confidence": 0.95, "bbox": [100, 200, 300, 400]}
      ],
      "colors": ["#FF5733", "#33FF57"]
    }
  ]
}
```

### AdUnitMedia

```json
{
  "export_metadata": {
    "export_date": "2026-02-10T12:30:45.123456+00:00",
    "export_version": "1.0",
    "model": "AdUnitMedia"
  },
  "id": 456,
  "campaign_id": 789,
  "status": "completed",
  "video_file": "ad_unit_media/2026/02/video.mp4",
  "duration": 30.5,
  "resolution": {
    "width": 1920,
    "height": 1080
  },
  "frame_rate": 29.97,
  "audio": {
    "channels": 2,
    "sample_rate": 48000
  },
  "file_size": 1024000,
  "processing_started_at": "2026-02-10T10:00:00.000000+00:00",
  "processing_completed_at": "2026-02-10T10:01:30.000000+00:00",
  "processing_error": "",
  "created_at": "2026-02-10T09:55:00.000000+00:00",
  "updated_at": "2026-02-10T10:01:30.000000+00:00",
  "processing_result": {
    "export_metadata": { "..." },
    "id": 123,
    "scenes": [...],
    "script": {...},
    "transcription": {...},
    "...": "..."
  },
  "video_ad_unit_id": 999,
  "video_ad_unit_code": "ORIGIN-0456"
}
```

### Campaign (Full Export)

```json
{
  "export_metadata": {
    "export_date": "2026-02-10T12:30:45.123456+00:00",
    "export_version": "1.0",
    "model": "Campaign"
  },
  "id": 789,
  "job_id": "ACME-2024-001",
  "script_title": "Product Launch Campaign",
  "client_name": "ACME Corp",
  "product_name": "Widget Pro",
  "brand_id": 5,
  "original_script_data": {
    "script_title": "Widget Pro Launch",
    "scenes": [...]
  },
  "created_at": "2026-02-10T09:00:00.000000+00:00",
  "updated_at": "2026-02-10T10:30:00.000000+00:00",
  "ad_unit_media": [
    {
      "export_metadata": { "..." },
      "id": 456,
      "campaign_id": 789,
      "status": "completed",
      "video_file": "...",
      "processing_result": {
        "id": 123,
        "scenes": [...],
        "script": {...},
        "...": "..."
      },
      "...": "..."
    }
  ]
}
```

### Bulk Exports

When exporting multiple results or media via admin bulk actions:

```json
{
  "export_metadata": {
    "export_date": "2026-02-10T12:30:45.123456+00:00",
    "export_version": "1.0",
    "model": "VideoProcessingResult",
    "count": 5
  },
  "results": [
    {
      "export_metadata": { "..." },
      "id": 1,
      "scenes": [...],
      "...": "..."
    },
    {
      "export_metadata": { "..." },
      "id": 2,
      "scenes": [...],
      "...": "..."
    }
  ]
}
```

## Field Types & Serialization

| Django Field Type | JSON Type | Notes |
|-------------------|-----------|-------|
| DateTimeField | string (ISO 8601) | Always timezone-aware |
| DecimalField | number (float) | Converted for JSON compatibility |
| JSONField | object/array | Preserved as-is |
| FileField | string | File path relative to MEDIA_ROOT |
| ForeignKey | number | PK of related object (if include_related) |
| IntegerField | number | Direct serialization |
| CharField/TextField | string | Direct serialization |
| BooleanField | boolean | Direct serialization |

## Configuration Options

### Export Functions

#### `export_video_processing_result(result, include_keyframes=True, include_media_metadata=True)`

- `include_keyframes` (bool): Include keyframe data (default: True)
- `include_media_metadata` (bool): Include video metadata from AdUnitMedia (default: True)

#### `export_ad_unit_media_with_result(media)`

Always includes processing result if available. No configuration needed.

#### `export_campaign_with_results(campaign)`

Always includes all ad unit media with their full processing results. No configuration needed.

#### `create_json_response(data, filename, pretty=True)`

- `data` (dict|list): Data to serialize
- `filename` (str): Download filename (without .json extension)
- `pretty` (bool): Pretty-print JSON with indentation (default: True)

## File Naming Convention

Export files follow this naming pattern:

- **Single result**: `result-{id}-{timestamp}.json`
- **Bulk results**: `results-bulk-{count}-{timestamp}.json`
- **Single media**: `media-{id}-{timestamp}.json`
- **Bulk media**: `media-bulk-{count}-{timestamp}.json`
- **Campaign**: `campaign-{job_id}-{timestamp}.json`

Timestamp format: `YYYYMMDD-HHMMSS`

## Re-importing Data

Exported JSON is structured to support future re-import functionality:

1. All required fields are included
2. Foreign keys reference IDs
3. Timestamps are ISO 8601 format
4. File paths are relative to MEDIA_ROOT
5. No circular references

**Note**: Re-import functionality is not yet implemented. Current exports are read-only backups.

## Error Handling

Export functions include type validation:

```python
# Raises TypeError if wrong model type
try:
    data = export_video_processing_result(campaign)  # Wrong type!
except TypeError as e:
    print(e)  # "Expected VideoProcessingResult, got Campaign"
```

## Examples

### Export Single Result from Admin

1. Navigate to VideoProcessingResult detail page
2. Click "Export as JSON" button
3. Browser downloads `result-123-20260210-123045.json`

### Export Campaign via Code

```python
from cw.lib.export import export_campaign_with_results
from cw.tvspots.models import Campaign

campaign = Campaign.objects.get(job_id="ACME-2024-001")
data = export_campaign_with_results(campaign)

# Save to file
import json
with open("campaign_export.json", "w") as f:
    json.dump(data, f, indent=2)
```

### Bulk Export All Completed Results

1. Navigate to VideoProcessingResult list page
2. Filter by completed status
3. Select all results
4. Choose "Export selected results as JSON" from Actions dropdown
5. Browser downloads `results-bulk-25-20260210-123045.json`

## Version History

- **v1.0** (2026-02-10): Initial export format
  - VideoProcessingResult export with scenes, script, transcription, visual analysis
  - AdUnitMedia export with processing results
  - Campaign export with nested media/results
  - Keyframe data support
  - Timezone-aware timestamps
  - Pretty-printed JSON output
