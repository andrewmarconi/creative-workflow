# Bulk Video Upload Implementation

## Overview

This document describes the implementation of batch video upload functionality for the tvspots app. The feature allows administrators to upload multiple video files at once from the Campaign admin page.

## Implementation Summary

### Files Modified

1. **`src/cw/tvspots/admin.py`** - CampaignAdmin class
   - Added `bulk_upload_videos_action` to `actions_detail` list
   - Added URL routing for bulk upload view
   - Implemented `bulk_upload_videos_action()` redirect method
   - Implemented `bulk_upload_videos_view()` with validation and queuing logic

2. **`src/cw/tvspots/templates/admin/tvspots/campaign/bulk_upload_videos.html`** (new)
   - Created template for bulk upload form
   - Includes file validation UI
   - Shows upload requirements and processing workflow

3. **`src/cw/tvspots/tests/test_bulk_upload.py`** (new)
   - Comprehensive test suite with 11 tests
   - Tests action registration, URL routing, file validation, and task queuing

## Features

### 1. Admin Action Button

A new "Bulk Upload Videos" button appears on Campaign detail pages, alongside "Create Origin Ad Unit" and "Create Adaptation" actions.

### 2. File Validation

The implementation validates each uploaded file for:

- **File Size**: Maximum 500 MB per file
- **File Extension**: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`
- **MIME Type**: Validates against allowed video MIME types

Invalid files are rejected with clear error messages, while valid files are processed.

### 3. AdUnitMedia Creation

For each valid video file:
- Creates an `AdUnitMedia` record linked to the campaign
- Sets status to `"uploaded"`
- Stores file size metadata
- Saves video file to `media/ad_unit_media/%Y/%m/`

### 4. Automatic Task Queuing

Each successfully uploaded video is automatically queued for processing:
```python
analyze_video_task.apply_async(args=[media.pk], queue="default")
```

### 5. User Feedback

The implementation provides comprehensive feedback:
- Success message with count of uploaded videos
- Error messages for each invalid file (with reason)
- Summary message combining success and error counts
- Visual file list with size validation indicators

### 6. Error Handling

Graceful error handling for:
- No files submitted
- Files exceeding size limit
- Invalid file formats
- Invalid MIME types
- Mixed valid/invalid uploads

## Usage

### For Administrators

1. Navigate to a Campaign in the Django admin
2. Click the "Bulk Upload Videos" action button
3. Select one or more video files (up to 500 MB each)
4. Review the selected files list
5. Click "Upload Videos"
6. Videos are uploaded and automatically queued for processing

### Processing Workflow

After upload, each video goes through the analysis pipeline:
1. Scene detection identifies key moments
2. Audio transcription extracts voiceover/dialogue
3. Visual analysis detects objects, colors, and style
4. Structured script is generated from analysis
5. Results appear in the Ad Unit Media section

## Code Structure

### URL Configuration

```python
path(
    "<int:object_id>/bulk-upload-videos/",
    self.admin_site.admin_view(self.bulk_upload_videos_view),
    name="tvspots_campaign_bulk_upload_videos",
)
```

### View Method

The `bulk_upload_videos_view()` method:
- Validates each uploaded file
- Creates AdUnitMedia records for valid files
- Queues processing tasks via Celery
- Returns to campaign change page with success/error messages

### Template

The template includes:
- Multiple file input field
- JavaScript for file list preview and validation
- Upload requirements documentation
- Processing workflow explanation

## Testing

The test suite (`test_bulk_upload.py`) covers:
- ✅ Action registration in admin
- ✅ URL routing
- ✅ Action redirect behavior
- ✅ Form rendering
- ✅ Single file upload
- ✅ Multiple file upload
- ✅ Oversized file rejection
- ✅ Invalid extension rejection
- ✅ Mixed valid/invalid files
- ✅ No files submitted
- ✅ All supported video formats

Run tests:
```bash
uv run pytest src/cw/tvspots/tests/test_bulk_upload.py -v
```

## Configuration

### File Size Limit

Default: 500 MB per file

To change, modify `MAX_FILE_SIZE` in `bulk_upload_videos_view()`:
```python
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
```

### Allowed Formats

Default: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`

To change, modify `ALLOWED_EXTENSIONS` and `ALLOWED_MIME_TYPES` in `bulk_upload_videos_view()`.

## Technical Details

### Dependencies

- Django file upload handling via `request.FILES.getlist()`
- Celery task queuing for video processing
- Django messages framework for user feedback
- Django Unfold admin actions system

### Performance Considerations

- Files are uploaded synchronously (Django handles chunked uploads)
- Processing is asynchronous via Celery tasks
- No hard limit on number of files per batch
- Each file validated before AdUnitMedia creation

### Security

- File extension validation prevents non-video uploads
- MIME type validation adds additional security layer
- File size limit prevents disk space exhaustion
- Django's `FileField` handles secure file storage

## Future Enhancements

Potential improvements:
- Drag-and-drop file upload interface
- Upload progress indicators
- Bulk video metadata extraction before queuing
- Configurable file size limits via Django settings
- Support for video URL imports (YouTube, Vimeo, etc.)
- Batch operations on uploaded videos (approve/reject/delete)

## Integration with Existing Features

The bulk upload integrates seamlessly with existing single-file upload:
- Uses same `AdUnitMedia` model
- Queues same `analyze_video_task` Celery task
- Follows same processing pipeline
- Results viewable in same admin interface

## Conclusion

This implementation provides a robust, user-friendly batch upload feature that maintains consistency with the existing architecture while significantly improving the workflow for uploading multiple videos to a campaign.
