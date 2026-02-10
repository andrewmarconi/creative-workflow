# Real-Time Progress Tracking for Video Processing

## Overview

This implementation adds real-time progress tracking for video processing tasks in the tvspots app. Users can now see live progress updates as videos are analyzed through multiple stages of the pipeline.

## Features Implemented

### 1. Task Progress Reporting

Modified `analyze_video_task` in `/Users/andrew/Develop/generative-creative-lab/src/cw/tvspots/tasks.py` to report progress at each stage:

**Progress Stages:**
- **Metadata Extraction (0-10%)** - Extracts video metadata (duration, resolution, etc.)
- **Scene Detection (10-30%)** - Detects scenes using PySceneDetect
- **Transcription (30-50%)** - Transcribes audio with Whisper
- **Visual Analysis (50-70%)** - Analyzes keyframes, objects, colors, sentiment
- **Script Generation (70-90%)** - Generates enhanced script
- **Audience Insights (90-95%)** - Generates AI-powered audience insights
- **Finalization (95-100%)** - Creates result object and saves keyframes

**Implementation:**
```python
self.update_state(
    state="PROGRESS",
    meta={
        "current": 30,
        "total": 100,
        "status": "Transcribing audio...",
        "phase": "transcription",
    }
)
```

### 2. Progress API Endpoint

Added REST API endpoint at `/app/tvspots/adunitmedia/<id>/progress/` that returns:

**Response Format:**
```json
{
    "status": "processing",
    "progress": 30,
    "total": 100,
    "phase": "transcription",
    "message": "Transcribing audio..."
}
```

**Supported States:**
- `pending` - Task queued but not started
- `processing` - Task in progress
- `completed` - Task finished successfully
- `failed` - Task failed with error

### 3. Database Changes

Added `celery_task_id` field to `AdUnitMedia` model:

```python
celery_task_id = models.CharField(
    max_length=255,
    blank=True,
    help_text="Celery task ID for async video processing",
)
```

**Migration:** `src/cw/tvspots/migrations/0012_add_celery_task_id_to_adunitmedia.py`

### 4. Admin UI Updates

#### List View (`change_list.html`)
- Progress bar displayed for processing videos
- Auto-refreshes every 2 seconds
- Shows percentage and current phase
- Automatically reloads page on completion/failure

#### Detail View (`change_form.html`)
- Enhanced progress display with:
  - Progress bar with percentage
  - Current phase label
  - Status message
  - Auto-refresh on completion

**Display Logic:**
- Only shows for media with status = "processing"
- Uses data attributes for JavaScript polling
- Clean styling with color-coded states

### 5. Auto-Refresh JavaScript

Polling mechanism that:
- Fetches progress every 2 seconds
- Updates UI without page reload
- Stops polling on completion/failure
- Automatically reloads page to show final results
- Cleans up intervals on page unload

**Key Features:**
- Non-blocking updates
- Error handling with user-friendly messages
- Memory leak prevention (interval cleanup)
- Minimal server load (2-second intervals)

### 6. Error State Handling

Comprehensive error handling:
- Failed tasks show error message
- Progress bar turns red on failure
- Page auto-reloads to show full error details
- Retry functionality preserved

## Files Modified

1. **Tasks:**
   - `/Users/andrew/Develop/generative-creative-lab/src/cw/tvspots/tasks.py`
     - Added progress reporting to `analyze_video_task`
     - Stores task ID on media object

2. **Models:**
   - `/Users/andrew/Develop/generative-creative-lab/src/cw/tvspots/models.py`
     - Added `celery_task_id` field to `AdUnitMedia`

3. **Admin:**
   - `/Users/andrew/Develop/generative-creative-lab/src/cw/tvspots/admin.py`
     - Added `progress_api` endpoint
     - Updated list/detail displays with progress columns
     - Updated all task queue calls to store task IDs

4. **Templates:**
   - `/Users/andrew/Develop/generative-creative-lab/src/cw/tvspots/templates/admin/tvspots/adunitmedia/change_list.html`
     - Progress bar in list view
     - Auto-refresh JavaScript

   - `/Users/andrew/Develop/generative-creative-lab/src/cw/tvspots/templates/admin/tvspots/adunitmedia/change_form.html`
     - Enhanced progress display in detail view
     - Phase tracking
     - Auto-refresh JavaScript

5. **Tests:**
   - `/Users/andrew/Develop/generative-creative-lab/src/cw/tvspots/tests/test_progress_tracking.py`
     - API endpoint tests
     - Progress state tests
     - Task ID tracking tests
     - 8 tests total, all passing

6. **Migrations:**
   - `/Users/andrew/Develop/generative-creative-lab/src/cw/tvspots/migrations/0012_add_celery_task_id_to_adunitmedia.py`

## Usage

### For End Users

1. **Upload a video** through the Campaign admin
2. **Progress updates appear automatically** in the media list
3. **Click on the media** to see detailed progress with phase information
4. **Page auto-refreshes** when processing completes
5. **View results** after completion

### For Developers

#### Accessing Progress Programmatically

```python
from django.urls import reverse
from celery.result import AsyncResult

# Get progress via API
url = reverse("admin:tvspots_adunitmedia_progress", args=[media_id])
response = client.get(url)
data = response.json()

# Or directly via Celery
task_result = AsyncResult(media.celery_task_id)
if task_result.state == "PROGRESS":
    progress = task_result.info.get("current", 0)
    phase = task_result.info.get("phase", "unknown")
```

#### Adding Progress to New Tasks

```python
@shared_task(bind=True)
def my_task(self, item_id):
    # Report progress
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 50,
            "total": 100,
            "status": "Processing item...",
            "phase": "processing",
        }
    )

    # ... do work ...
```

## Testing

Run the test suite:

```bash
# Run all progress tracking tests
uv run python -m pytest src/cw/tvspots/tests/test_progress_tracking.py -xvs

# Run specific test
uv run python -m pytest src/cw/tvspots/tests/test_progress_tracking.py::ProgressTrackingTests::test_progress_api_processing -xvs
```

**Test Coverage:**
- API endpoint responses for all states
- Progress metadata structure
- Task ID storage
- Error handling
- State transitions

## Performance Considerations

1. **Polling Frequency:** 2-second intervals balance responsiveness with server load
2. **Progress Updates:** Minimal overhead (no database writes during task)
3. **Cleanup:** JavaScript properly cleans up intervals to prevent memory leaks
4. **Caching:** Celery result backend caches task state efficiently

## Future Enhancements

Potential improvements:

1. **WebSocket Updates:** Replace polling with WebSockets for instant updates
2. **Batch Progress:** Track progress for multiple uploads simultaneously
3. **Progress History:** Store progress snapshots for debugging
4. **Estimated Time:** Show estimated completion time based on historical data
5. **Pause/Resume:** Add ability to pause long-running tasks
6. **Progress Notifications:** Email/Slack notifications on completion

## Troubleshooting

### Progress Not Updating

1. Check Celery worker is running: `uv run celery -A cw worker -Q default`
2. Verify task ID is stored: `media.celery_task_id` should not be empty
3. Check browser console for JavaScript errors
4. Verify API endpoint is accessible: `/app/tvspots/adunitmedia/<id>/progress/`

### Page Not Auto-Refreshing

1. Check JavaScript console for errors
2. Verify interval cleanup is not triggered prematurely
3. Check network requests are succeeding (not 404/500)

### Progress Stuck at 0%

1. Task may be in queue (not started yet)
2. Worker may not be running
3. Check task state in Flower: http://localhost:5555

## Architecture Diagram

```
User Upload Video
       |
       v
Campaign Admin saves AdUnitMedia
       |
       v
analyze_video_task queued
    (task_id stored)
       |
       v
Task starts processing
       |
       +---> update_state(0%, "metadata")
       |
       +---> update_state(10%, "scene_detection")
       |
       +---> update_state(30%, "transcription")
       |
       +---> update_state(50%, "visual_analysis")
       |
       +---> update_state(70%, "script_generation")
       |
       +---> update_state(90%, "insights")
       |
       +---> update_state(95%, "finalization")
       |
       v
Task completes (100%)
       |
       v
JavaScript polls /progress/ API
       |
       +---> Fetches AsyncResult state
       |
       +---> Updates UI progress bar
       |
       +---> Auto-reloads on completion
```

## Security Considerations

1. **Authentication Required:** Progress API requires admin login
2. **CSRF Protection:** Uses Django's CSRF middleware
3. **Task ID Validation:** API validates media ownership
4. **No Sensitive Data:** Progress messages don't expose file paths or internals

## Conclusion

This implementation provides a robust, user-friendly progress tracking system that:
- Gives real-time feedback during long-running video processing
- Reduces user anxiety about task status
- Improves debugging with detailed phase information
- Maintains performance with efficient polling
- Handles errors gracefully

All code follows Django and Celery best practices and includes comprehensive test coverage.
