# Video Origin Extraction Feature Specification

## Overview

Automate the creation of origin VideoAdUnits by analyzing uploaded MP4 video files. This feature extracts scenes, generates structured scripts, transcribes audio, and provides creative insights to serve as the foundation for cultural adaptation workflows.

## Goals

1. **Reduce Manual Effort**: Eliminate manual script writing for origin ad units
2. **Standardize Format**: Ensure consistent script structure matching `tvspot.schema.json`
3. **Enable Automation**: Feed extracted scripts directly into the adaptation pipeline
4. **Provide Insights**: Extract creative intelligence to inform adaptation decisions

## User Stories

### Primary Flow
**As a** campaign manager
**I want to** upload an existing TV spot video
**So that** I can automatically generate an origin script and begin cultural adaptations

**Acceptance Criteria:**
- Upload MP4 file through Django admin
- Link to existing Campaign or create new one
- Automatic scene detection and script generation
- Review and edit extracted script before finalizing
- One-click transition to adaptation workflow

### Secondary Flows
**As a** creative director
**I want to** review visual style analysis and sentiment data
**So that** I can understand the creative direction and emotional tone

**As a** strategist
**I want to** see audience targeting insights
**So that** I can identify potential markets for adaptation

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Django Admin UI                          │
│  AdUnitMedia Upload → Processing Status → Review & Edit      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Celery Task Queue                         │
│             analyze_video_task(ad_unit_media_id)             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Video Processing Pipeline                   │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐           │
│  │   Scene    │→ │   Audio    │→ │   Vision    │           │
│  │ Detection  │  │ Extraction │  │  Analysis   │           │
│  └────────────┘  └────────────┘  └─────────────┘           │
│                         ↓                                    │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐           │
│  │   Frame    │  │   Speech   │  │   Object    │           │
│  │ Extraction │  │Transcription│  │ Detection   │           │
│  └────────────┘  └────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  LLM Synthesis Pipeline                      │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────┐     │
│  │ Script         │→ │ Sentiment    │→ │  Audience   │     │
│  │ Generation     │  │ Analysis     │  │  Insights   │     │
│  └────────────────┘  └──────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Data Storage                            │
│  AdUnitMedia → ProcessingResult → VideoAdUnit (origin)       │
└─────────────────────────────────────────────────────────────┘
```

## Data Models

### New Models

#### AdUnitMedia
**Purpose**: Represents an uploaded video file awaiting analysis

```python
# src/cw/tvspots/models.py

class AdUnitMedia(models.Model):
    """Uploaded video file for origin script extraction"""

    STATUS_CHOICES = [
        ('pending', 'Pending Upload'),
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reviewed', 'Reviewed'),
    ]

    # Core fields
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE,
                                  related_name='ad_unit_media')
    video_file = models.FileField(upload_to='ad_unit_media/%Y/%m/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                               default='pending')

    # Metadata (extracted from file)
    duration = models.FloatField(null=True, blank=True,
                                  help_text="Duration in seconds")
    resolution_width = models.IntegerField(null=True, blank=True)
    resolution_height = models.IntegerField(null=True, blank=True)
    frame_rate = models.FloatField(null=True, blank=True)
    audio_channels = models.IntegerField(null=True, blank=True)
    audio_sample_rate = models.IntegerField(null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True,
                                        help_text="Size in bytes")

    # Processing tracking
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)

    # Results reference
    result = models.OneToOneField('VideoProcessingResult',
                                   on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='media')

    # Generated AdUnit (once reviewed/approved)
    video_ad_unit = models.OneToOneField('VideoAdUnit',
                                          on_delete=models.SET_NULL,
                                          null=True, blank=True,
                                          related_name='source_media')

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ad Unit Media'
        verbose_name_plural = 'Ad Unit Media'

    def __str__(self):
        return f"Ad Unit Media for {self.campaign} ({self.status})"
```

#### VideoProcessingResult
**Purpose**: Stores all extracted data from video analysis

```python
class VideoProcessingResult(models.Model):
    """Complete analysis results from video processing pipeline"""

    # Scene data
    scenes = models.JSONField(default=list, help_text="""
    List of detected scenes:
    [{
        "scene_number": 1,
        "start_time": 0.0,
        "end_time": 3.5,
        "duration": 3.5,
        "key_frame_path": "media/keyframes/scene_001.jpg",
        "visual_description": "...",
        "objects_detected": ["product", "person", "table"],
        "colors": ["#FF5733", "#33FF57"],
        "lighting": "warm, golden hour",
        "camera_angle": "medium shot",
        "sentiment": "positive"
    }]
    """)

    # Generated script (tvspot.schema.json format)
    script = models.JSONField(default=dict, help_text="""
    Structured script matching tvspot.schema.json:
    {
        "scenes": [
            {
                "scene_number": 1,
                "duration": 3.5,
                "visual": "A smiling family gathered around a dinner table...",
                "audio": {
                    "voiceover": "When family comes together...",
                    "music": "Uplifting acoustic guitar",
                    "sfx": "Clinking glasses"
                },
                "action": "Camera pans across the table...",
                "products": ["Brand Product X"],
                "sentiment": "warm, joyful"
            }
        ]
    }
    """)

    # Audio transcription
    transcription = models.JSONField(default=dict, help_text="""
    Full audio transcription with timestamps:
    {
        "language": "en-US",
        "confidence": 0.95,
        "segments": [
            {
                "start": 0.5,
                "end": 3.2,
                "text": "When family comes together...",
                "speaker": "narrator",
                "confidence": 0.96
            }
        ]
    }
    """)

    # Visual analysis
    visual_style = models.JSONField(default=dict, help_text="""
    Overall visual style analysis:
    {
        "dominant_colors": ["#FF5733", "#33FF57", "#3357FF"],
        "color_palette": "warm, inviting",
        "lighting_style": "natural, golden hour",
        "camera_work": "smooth pans, static shots",
        "editing_pace": "slow, contemplative",
        "visual_themes": ["family", "togetherness", "home"]
    }
    """)

    # Object detection summary
    objects_summary = models.JSONField(default=dict, help_text="""
    Aggregated object detection across all scenes:
    {
        "products": ["Brand Product X", "Logo"],
        "people": {"count": 4, "demographics": ["adult", "child"]},
        "locations": ["kitchen", "dining room"],
        "props": ["table", "chairs", "food", "glasses"]
    }
    """)

    # Sentiment analysis
    sentiment_analysis = models.JSONField(default=dict, help_text="""
    Overall sentiment and emotional analysis:
    {
        "overall_sentiment": "positive",
        "confidence": 0.89,
        "emotional_arc": [
            {"time": 0, "emotion": "neutral"},
            {"time": 10, "emotion": "warm"},
            {"time": 20, "emotion": "joyful"}
        ],
        "dominant_emotions": ["happiness", "warmth", "connection"]
    }
    """)

    # Scene categorization
    categories = models.JSONField(default=list, help_text="""
    Scene categorization:
    ["lifestyle", "family", "product showcase", "emotional appeal"]
    """)

    # Audience insights
    audience_insights = models.JSONField(default=dict, help_text="""
    AI-generated audience targeting insights:
    {
        "primary_audience": {
            "demographics": {
                "age_range": "25-45",
                "family_status": "parents with children",
                "income_level": "middle to upper-middle"
            },
            "psychographics": {
                "values": ["family", "quality time", "tradition"],
                "interests": ["cooking", "entertaining", "home"],
                "lifestyle": "family-oriented, quality-focused"
            }
        },
        "secondary_audiences": [...],
        "market_potential": {
            "high_fit_markets": ["US", "UK", "DE", "AU"],
            "considerations": ["Strong family values", "Home-centered culture"]
        }
    }
    """)

    # Processing metadata
    processing_time = models.FloatField(null=True, blank=True,
                                         help_text="Total processing time in seconds")
    models_used = models.JSONField(default=dict, help_text="""
    Track which models/APIs were used:
    {
        "scene_detection": "PySceneDetect",
        "transcription": "Whisper Large v3",
        "object_detection": "YOLO v8",
        "script_generation": "Qwen/Qwen2.5-7B-Instruct",
        "sentiment": "distilbert-base-uncased-finetuned-sst-2-english"
    }
    """)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Video Processing Result'
        verbose_name_plural = 'Video Processing Results'

    def __str__(self):
        return f"Processing Result (created {self.created_at})"
```

#### KeyFrame
**Purpose**: Store extracted key frames with metadata

```python
class KeyFrame(models.Model):
    """Representative frame from a detected scene"""

    result = models.ForeignKey('VideoProcessingResult',
                                on_delete=models.CASCADE,
                                related_name='key_frames')
    scene_number = models.IntegerField()
    timestamp = models.FloatField(help_text="Time in seconds")
    image = models.ImageField(upload_to='keyframes/%Y/%m/')

    # Visual analysis for this specific frame
    objects = models.JSONField(default=list, help_text="""
    Objects detected in this frame:
    [
        {"label": "person", "confidence": 0.95, "bbox": [x, y, w, h]},
        {"label": "product", "confidence": 0.88, "bbox": [x, y, w, h]}
    ]
    """)

    colors = models.JSONField(default=list,
                               help_text="Dominant colors as hex codes")

    # Embeddings for similarity search (future use)
    embedding = models.JSONField(null=True, blank=True,
                                  help_text="CLIP or similar embedding vector")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scene_number', 'timestamp']
        unique_together = ['result', 'scene_number']

    def __str__(self):
        return f"KeyFrame Scene {self.scene_number} @ {self.timestamp}s"
```

### Model Relationships

```
Campaign
  ├── AdUnitMedia (1:N)
  │     ├── VideoProcessingResult (1:1)
  │     │     └── KeyFrame (1:N)
  │     └── VideoAdUnit (1:1, created after review)
  └── VideoAdUnit (1:N, existing)
```

## Processing Pipeline

### Phase 1: Video Ingestion & Metadata Extraction

**Technology**: FFmpeg + PyAV

```python
# src/cw/tvspots/tasks.py

@shared_task(bind=True, max_retries=3)
def analyze_video_task(self, ad_unit_media_id: int):
    """
    Main orchestration task for video analysis pipeline

    This task coordinates all video processing subtasks and
    aggregates results into VideoProcessingResult.
    """
    try:
        media = AdUnitMedia.objects.get(id=ad_unit_media_id)
        media.status = 'processing'
        media.processing_started_at = timezone.now()
        media.save()

        # Phase 1: Extract metadata
        metadata = extract_video_metadata(media.video_file.path)
        media.duration = metadata['duration']
        media.resolution_width = metadata['width']
        media.resolution_height = metadata['height']
        media.frame_rate = metadata['frame_rate']
        media.audio_channels = metadata['audio_channels']
        media.audio_sample_rate = metadata['sample_rate']
        media.file_size = metadata['file_size']
        media.save()

        # Phase 2: Scene detection
        scenes = detect_scenes(media.video_file.path)

        # Phase 3: Extract audio
        audio_path = extract_audio(media.video_file.path)

        # Phase 4: Transcribe audio
        transcription = transcribe_audio(audio_path)

        # Phase 5: Extract key frames and analyze
        key_frames_data = []
        for scene in scenes:
            frame_path = extract_key_frame(
                media.video_file.path,
                scene['start_time']
            )

            # Vision analysis
            objects = detect_objects(frame_path)
            colors = extract_dominant_colors(frame_path)

            key_frames_data.append({
                'scene_number': scene['scene_number'],
                'timestamp': scene['start_time'],
                'frame_path': frame_path,
                'objects': objects,
                'colors': colors
            })

        # Phase 6: Visual style analysis
        visual_style = analyze_visual_style(key_frames_data)

        # Phase 7: Sentiment analysis (audio + visual)
        sentiment = analyze_sentiment(
            transcription=transcription,
            visual_data=key_frames_data
        )

        # Phase 8: LLM-based script generation
        script = generate_script(
            scenes=scenes,
            transcription=transcription,
            key_frames=key_frames_data,
            visual_style=visual_style,
            sentiment=sentiment
        )

        # Phase 9: Audience insights generation
        audience_insights = generate_audience_insights(
            script=script,
            visual_style=visual_style,
            sentiment=sentiment
        )

        # Phase 10: Create result object
        result = VideoProcessingResult.objects.create(
            scenes=scenes,
            script=script,
            transcription=transcription,
            visual_style=visual_style,
            objects_summary=aggregate_objects(key_frames_data),
            sentiment_analysis=sentiment,
            categories=categorize_scenes(scenes, script),
            audience_insights=audience_insights,
            processing_time=(timezone.now() - media.processing_started_at).total_seconds(),
            models_used={
                'scene_detection': 'PySceneDetect',
                'transcription': 'openai/whisper-large-v3',
                'object_detection': 'ultralytics/yolov8',
                'script_generation': 'Qwen/Qwen2.5-7B-Instruct',
                'sentiment': 'distilbert-base-uncased-finetuned-sst-2-english'
            }
        )

        # Save key frames
        for kf_data in key_frames_data:
            KeyFrame.objects.create(
                result=result,
                scene_number=kf_data['scene_number'],
                timestamp=kf_data['timestamp'],
                image=kf_data['frame_path'],
                objects=kf_data['objects'],
                colors=kf_data['colors']
            )

        # Link result to media
        media.result = result
        media.status = 'completed'
        media.processing_completed_at = timezone.now()
        media.save()

        return {
            'status': 'success',
            'media_id': media.id,
            'result_id': result.id,
            'processing_time': result.processing_time
        }

    except Exception as e:
        media.status = 'failed'
        media.processing_error = str(e)
        media.save()
        raise
```

### Phase 2: Scene Detection

**Technology**: PySceneDetect or similar

```python
# src/cw/lib/video_analysis/scene_detection.py

import scenedetect
from scenedetect.detectors import ContentDetector
from scenedetect.video_manager import VideoManager

def detect_scenes(video_path: str, threshold: float = 30.0) -> List[Dict]:
    """
    Detect scene boundaries using content-based detection

    Args:
        video_path: Path to video file
        threshold: Sensitivity threshold (lower = more scenes)

    Returns:
        List of scene dictionaries with start/end times
    """
    video_manager = VideoManager([video_path])
    scene_manager = scenedetect.SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))

    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)
    scene_list = scene_manager.get_scene_list()

    scenes = []
    for idx, (start_time, end_time) in enumerate(scene_list, 1):
        scenes.append({
            'scene_number': idx,
            'start_time': start_time.get_seconds(),
            'end_time': end_time.get_seconds(),
            'duration': (end_time - start_time).get_seconds()
        })

    return scenes
```

### Phase 3: Audio Transcription

**Technology**: OpenAI Whisper (local) or AssemblyAI API

```python
# src/cw/lib/video_analysis/transcription.py

import whisper
import torch

def transcribe_audio(audio_path: str, model_size: str = 'large-v3') -> Dict:
    """
    Transcribe audio using Whisper

    Args:
        audio_path: Path to audio file (MP3/WAV)
        model_size: Whisper model size (tiny, base, small, medium, large-v3)

    Returns:
        Transcription dictionary with segments and metadata
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model(model_size, device=device)

    result = model.transcribe(
        audio_path,
        task='transcribe',
        language=None,  # Auto-detect
        word_timestamps=True,
        verbose=False
    )

    # Format for our schema
    return {
        'language': result.get('language', 'unknown'),
        'confidence': calculate_average_confidence(result['segments']),
        'segments': [
            {
                'start': seg['start'],
                'end': seg['end'],
                'text': seg['text'].strip(),
                'speaker': 'narrator',  # Could enhance with speaker diarization
                'confidence': seg.get('avg_logprob', 0.0)
            }
            for seg in result['segments']
        ]
    }
```

### Phase 4: Object Detection

**Technology**: YOLO v8 or CLIP

```python
# src/cw/lib/video_analysis/object_detection.py

from ultralytics import YOLO
from PIL import Image

def detect_objects(image_path: str, confidence_threshold: float = 0.5) -> List[Dict]:
    """
    Detect objects in a frame using YOLO v8

    Args:
        image_path: Path to image file
        confidence_threshold: Minimum confidence for detections

    Returns:
        List of detected objects with labels, confidence, and bounding boxes
    """
    model = YOLO('yolov8x.pt')  # Use largest model for accuracy
    results = model(image_path, conf=confidence_threshold)

    objects = []
    for result in results:
        for box in result.boxes:
            objects.append({
                'label': model.names[int(box.cls)],
                'confidence': float(box.conf),
                'bbox': box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            })

    return objects
```

### Phase 5: LLM Script Generation

**Technology**: Qwen 2.5 7B (local) or Claude API

```python
# src/cw/lib/video_analysis/script_generation.py

from cw.lib.pipeline.model_loader import PipelineModelLoader

SCRIPT_GENERATION_PROMPT = """
You are an expert TV commercial script writer. Given the following analysis
of a video commercial, generate a structured script in JSON format following
the tvspot.schema.json specification.

## Video Analysis Data

### Detected Scenes
{scenes_json}

### Audio Transcription
{transcription_json}

### Visual Analysis
{visual_style_json}

### Objects Detected
{objects_json}

### Sentiment Analysis
{sentiment_json}

## Task

Create a JSON script with the following structure:

{{
  "scenes": [
    {{
      "scene_number": 1,
      "duration": 3.5,
      "visual": "Detailed description of what is shown on screen",
      "audio": {{
        "voiceover": "Exact transcribed voiceover text",
        "music": "Description of background music",
        "sfx": "Sound effects description"
      }},
      "action": "Camera movements and actions taking place",
      "products": ["List of products/brands visible"],
      "sentiment": "Emotional tone of this scene"
    }}
  ]
}}

Requirements:
- One scene object per detected scene
- Visual descriptions should be specific and detailed
- Audio should match the transcription where applicable
- Include camera work and editing details in action field
- Identify all visible products/brands
- Capture the emotional tone of each scene

Generate the complete JSON script now:
"""

def generate_script(
    scenes: List[Dict],
    transcription: Dict,
    key_frames: List[Dict],
    visual_style: Dict,
    sentiment: Dict
) -> Dict:
    """
    Generate structured script using LLM analysis

    Args:
        scenes: Scene detection results
        transcription: Audio transcription
        key_frames: Key frame analysis data
        visual_style: Overall visual style analysis
        sentiment: Sentiment analysis results

    Returns:
        Structured script matching tvspot.schema.json
    """
    loader = PipelineModelLoader()

    # Use default LLM model from pipeline settings
    generator = loader.get_generator(
        state=None,  # No state needed for one-off generation
        schema=None,
        node_key='script_generation'
    )

    prompt = SCRIPT_GENERATION_PROMPT.format(
        scenes_json=json.dumps(scenes, indent=2),
        transcription_json=json.dumps(transcription, indent=2),
        visual_style_json=json.dumps(visual_style, indent=2),
        objects_json=json.dumps(aggregate_objects(key_frames), indent=2),
        sentiment_json=json.dumps(sentiment, indent=2)
    )

    response = generator.invoke(prompt)

    # Parse JSON response
    script = json.loads(response.content)

    # Validate against schema
    validate_script_schema(script)

    return script
```

### Phase 6: Audience Insights Generation

```python
# src/cw/lib/video_analysis/audience_insights.py

AUDIENCE_INSIGHTS_PROMPT = """
You are a marketing strategist analyzing a TV commercial for audience targeting.

## Commercial Analysis

### Script
{script_json}

### Visual Style
{visual_style_json}

### Sentiment
{sentiment_json}

## Task

Based on this commercial, provide detailed audience targeting insights in JSON:

{{
  "primary_audience": {{
    "demographics": {{
      "age_range": "25-45",
      "gender": "all" or specific,
      "family_status": "parents with children",
      "income_level": "middle to upper-middle",
      "education": "college educated"
    }},
    "psychographics": {{
      "values": ["family", "quality", "tradition"],
      "interests": ["cooking", "entertaining"],
      "lifestyle": "family-oriented"
    }}
  }},
  "secondary_audiences": [...],
  "market_potential": {{
    "high_fit_markets": ["US", "UK", "DE"],
    "cultural_considerations": ["Strong family values", "Home-centered culture"],
    "adaptation_opportunities": ["Consider local family structures", "Adapt meal contexts"]
  }},
  "creative_themes": ["family togetherness", "product quality", "home comfort"],
  "emotional_appeals": ["warmth", "nostalgia", "belonging"]
}}

Generate the complete audience insights JSON now:
"""

def generate_audience_insights(
    script: Dict,
    visual_style: Dict,
    sentiment: Dict
) -> Dict:
    """Generate audience targeting insights using LLM"""
    loader = PipelineModelLoader()
    generator = loader.get_generator(state=None, schema=None, node_key='audience_insights')

    prompt = AUDIENCE_INSIGHTS_PROMPT.format(
        script_json=json.dumps(script, indent=2),
        visual_style_json=json.dumps(visual_style, indent=2),
        sentiment_json=json.dumps(sentiment, indent=2)
    )

    response = generator.invoke(prompt)
    return json.loads(response.content)
```

## Technology Stack

### Video Processing
- **FFmpeg/PyAV**: Video metadata extraction, audio extraction
- **PySceneDetect**: Scene boundary detection
- **OpenCV**: Frame extraction, color analysis

### Computer Vision
- **YOLO v8** (Ultralytics): Real-time object detection
- **CLIP** (OpenAI): Vision-language embeddings (optional, for similarity search)
- **Pillow**: Image processing utilities

### Audio Processing
- **Whisper Large v3** (OpenAI): Speech-to-text transcription
- **pyannote.audio** (Optional): Speaker diarization
- **librosa**: Audio analysis utilities

### Natural Language Processing
- **Qwen 2.5 7B Instruct**: Script generation, audience insights (local inference)
- **Transformers** (HuggingFace): Sentiment analysis models
- **LangChain**: LLM orchestration utilities

### Storage & Processing
- **Celery**: Async task execution
- **PostgreSQL**: Structured data storage
- **Django Storage**: Media file management

## Implementation Phases

### Phase 1: MVP (Weeks 1-2)
**Goal**: Basic video upload → script generation

- [ ] Create Django models: `AdUnitMedia`, `VideoProcessingResult`, `KeyFrame`
- [ ] Create admin interface for video upload
- [ ] Implement basic Celery task: `analyze_video_task`
- [ ] Scene detection with PySceneDetect
- [ ] Key frame extraction with OpenCV
- [ ] Audio transcription with Whisper
- [ ] Basic script generation with Qwen 2.5 7B
- [ ] Display results in admin (read-only)

**Deliverable**: Upload MP4 → Auto-generated script in admin

### Phase 2: Enhanced Analysis (Weeks 3-4)
**Goal**: Add vision AI and richer metadata

- [ ] Integrate YOLO v8 for object detection
- [ ] Visual style analysis (colors, lighting, camera work)
- [ ] Sentiment analysis (audio + visual)
- [ ] Scene categorization
- [ ] Enhanced script generation with all data inputs
- [ ] Key frame thumbnails in admin

**Deliverable**: Comprehensive video analysis with visual insights

### Phase 3: Insights & Editing (Week 5)
**Goal**: Audience insights + script editing capability

- [ ] Audience insights generation
- [ ] Editable script interface in admin
- [ ] Script validation against tvspot.schema.json
- [ ] Side-by-side video playback with script
- [ ] Approve/Reject workflow

**Deliverable**: Full editing workflow with approval gate

### Phase 4: Integration (Week 6)
**Goal**: Seamless connection to adaptation pipeline

- [ ] One-click "Create Origin VideoAdUnit" button
- [ ] Auto-populate VideoAdUnit with approved script
- [ ] Link to adaptation workflow
- [ ] Performance optimization (parallel processing)
- [ ] Error handling and retry logic

**Deliverable**: End-to-end flow from video upload to adaptation

### Phase 5: Polish (Week 7+)
**Goal**: Production readiness

- [ ] Batch processing support (multiple videos)
- [ ] Processing progress indicators
- [ ] Video preview player in admin
- [ ] Export results to PDF/JSON
- [ ] Performance benchmarking
- [ ] Documentation and user guide

## API Design

### Django Admin Actions

```python
# src/cw/tvspots/admin.py

@admin.register(AdUnitMedia)
class AdUnitMediaAdmin(admin.ModelAdmin):
    list_display = ['id', 'campaign', 'status', 'duration', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['status', 'processing_started_at',
                       'processing_completed_at', 'result']

    fieldsets = [
        ('Video Upload', {
            'fields': ['campaign', 'video_file']
        }),
        ('Processing Status', {
            'fields': ['status', 'processing_started_at',
                      'processing_completed_at', 'processing_error']
        }),
        ('Metadata', {
            'fields': ['duration', 'resolution_width', 'resolution_height',
                      'frame_rate', 'audio_channels', 'audio_sample_rate']
        }),
        ('Results', {
            'fields': ['result', 'video_ad_unit']
        })
    ]

    def save_model(self, request, obj, form, change):
        """Auto-trigger processing when video is uploaded"""
        super().save_model(request, obj, form, change)

        if obj.status == 'uploaded' and obj.video_file:
            # Queue processing task
            analyze_video_task.delay(obj.id)

    actions = ['reprocess_videos', 'create_origin_ad_units']

    def reprocess_videos(self, request, queryset):
        """Reprocess selected videos"""
        count = 0
        for media in queryset.filter(status__in=['failed', 'completed']):
            analyze_video_task.delay(media.id)
            count += 1
        self.message_user(request, f"Queued {count} videos for reprocessing")

    def create_origin_ad_units(self, request, queryset):
        """Create VideoAdUnits from approved results"""
        count = 0
        for media in queryset.filter(status='completed', video_ad_unit__isnull=True):
            if media.result:
                # Create VideoAdUnit from result
                ad_unit = VideoAdUnit.objects.create(
                    campaign=media.campaign,
                    use_pipeline=False,  # This is the origin, not an adaptation
                    # ... populate from media.result.script
                )

                # Link back
                media.video_ad_unit = ad_unit
                media.status = 'reviewed'
                media.save()
                count += 1

        self.message_user(request, f"Created {count} origin VideoAdUnits")
```

### Celery Task Interface

```python
# Public task signatures

@shared_task
def analyze_video_task(ad_unit_media_id: int) -> Dict:
    """
    Analyze uploaded video and extract script

    Returns:
        {
            'status': 'success' | 'failed',
            'media_id': int,
            'result_id': int,
            'processing_time': float
        }
    """

@shared_task
def reprocess_failed_videos() -> Dict:
    """
    Periodic task to retry failed video processing

    Returns:
        {
            'reprocessed': int,
            'still_failed': int
        }
    """
```

## UI/UX Design

### Admin Interface Mockup

```
┌─────────────────────────────────────────────────────────────────┐
│ Django Admin / TV Spots / Ad Unit Media                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ [+ Add Ad Unit Media]                 [Search...] [Filter ▼]     │
│                                                                   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ID │ Campaign      │ Status      │ Duration │ Created       │ │
│ ├────┼───────────────┼─────────────┼──────────┼───────────────┤ │
│ │ 42 │ Nike Spring   │ ✓ Completed │ 30.0s    │ 2 hours ago   │ │
│ │ 41 │ Coca-Cola NY  │ ⏳ Processing│ 29.5s    │ 5 hours ago   │ │
│ │ 40 │ Toyota Launch │ ✗ Failed    │ -        │ 1 day ago     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

Click on row 42 (Completed) →

┌─────────────────────────────────────────────────────────────────┐
│ Ad Unit Media #42 - Nike Spring Campaign                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Video Upload                                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Campaign: [Nike Spring Campaign ▼]                           │ │
│ │ Video File: [nike_spring_30s.mp4]  [Preview ▶]              │ │
│ │                                                               │ │
│ │ ┌─────────────────────────────────────────────────────────┐ │ │
│ │ │                                                           │ │ │
│ │ │                  [Video Player]                          │ │ │
│ │ │                  1920x1080, 30fps                         │ │ │
│ │ │                  Duration: 30.0s                          │ │ │
│ │ │                                                           │ │ │
│ │ └─────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ Processing Results ✓                                              │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Scenes Detected: 8                                           │ │
│ │ Processing Time: 127.3 seconds                               │ │
│ │                                                               │ │
│ │ [View Scenes] [View Script] [View Insights]                 │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ Generated Script (Editable)                                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Scene 1 (0.0s - 3.5s)                        [🖼️ Key Frame]  │ │
│ │ ┌─────────────────────────────────────────────────────────┐ │ │
│ │ │ Visual: A runner's feet pounding the pavement at dawn,  │ │ │
│ │ │         close-up shot showing Nike shoes in detail...   │ │ │
│ │ │ Audio:                                                   │ │ │
│ │ │   VO: "Every step begins with a choice..."              │ │ │
│ │ │   Music: Uplifting electronic beat                      │ │ │
│ │ │ Action: Slow-motion tracking shot, camera pans up       │ │ │
│ │ │ Products: Nike Air Zoom Pegasus                         │ │ │
│ │ │ Sentiment: Determined, inspirational                    │ │ │
│ │ └─────────────────────────────────────────────────────────┘ │ │
│ │                                                               │ │
│ │ Scene 2 (3.5s - 7.0s)                        [🖼️ Key Frame]  │ │
│ │ ...                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ Audience Insights                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Primary Audience:                                            │ │
│ │ • Age: 18-35                                                 │ │
│ │ • Psychographics: Health-conscious, goal-driven             │ │
│ │ • Values: Personal achievement, fitness, self-improvement   │ │
│ │                                                               │ │
│ │ High-Fit Markets: US, UK, DE, AU, JP                        │ │
│ │ Creative Themes: Determination, dawn/new beginnings         │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ Actions                                                           │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ [Create Origin VideoAdUnit]  [Reprocess]  [Export JSON]     │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ [Save Changes]  [Save and Continue Editing]  [Delete]            │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Points

### Existing System Touchpoints

1. **Campaign Model**: AdUnitMedia links to existing Campaign
2. **VideoAdUnit Creation**: Results flow into existing VideoAdUnit → Storyboard workflow
3. **LLM Infrastructure**: Reuse PipelineModelLoader, Qwen models
4. **Celery Queue**: Uses existing `default` queue (sequential processing)
5. **Media Storage**: Uses Django's media file handling
6. **Admin UI**: Extends Django Unfold admin patterns

### Data Flow Integration

```
Video Upload (MP4)
  ↓
AdUnitMedia (new)
  ↓
analyze_video_task (Celery)
  ↓
VideoProcessingResult (new)
  ↓
[Manual Review & Edit]
  ↓
VideoAdUnit (existing) ← Click "Create Origin VideoAdUnit"
  ↓
Adaptation Pipeline (existing)
  ↓
Storyboard Generation (existing)
```

## Testing Strategy

### Unit Tests

```python
# tests/test_video_analysis.py

class SceneDetectionTests(TestCase):
    def test_detect_scenes_returns_valid_structure(self):
        """Scene detection returns list of dicts with required keys"""

    def test_scene_boundaries_are_sequential(self):
        """Scene end times match next scene start times"""

class TranscriptionTests(TestCase):
    def test_transcribe_audio_detects_language(self):
        """Whisper correctly identifies audio language"""

    def test_transcription_includes_timestamps(self):
        """Segments have start/end times"""

class ObjectDetectionTests(TestCase):
    def test_detect_objects_filters_by_confidence(self):
        """Low confidence detections are filtered out"""

    def test_detected_objects_have_bounding_boxes(self):
        """All objects include bbox coordinates"""

class ScriptGenerationTests(TestCase):
    def test_generated_script_matches_schema(self):
        """LLM output validates against tvspot.schema.json"""

    def test_script_scene_count_matches_detection(self):
        """Generated script has one entry per detected scene"""
```

### Integration Tests

```python
class VideoProcessingPipelineTests(TestCase):
    def test_full_pipeline_from_upload_to_result(self):
        """Complete flow: upload → processing → result"""

        # Upload video
        media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            video_file=SimpleUploadedFile('test.mp4', b'...')
        )

        # Run task
        result = analyze_video_task(media.id)

        # Verify result
        media.refresh_from_db()
        assert media.status == 'completed'
        assert media.result is not None
        assert media.result.script is not None

    def test_failed_processing_sets_error_status(self):
        """Pipeline failures are captured gracefully"""
```

### Performance Tests

```python
class PerformanceTests(TestCase):
    def test_30_second_video_processes_under_5_minutes(self):
        """Typical 30s commercial processes in reasonable time"""

    def test_parallel_uploads_dont_block(self):
        """Multiple videos can queue without blocking"""
```

## Configuration

### Settings

```python
# src/cw/settings.py

# Video Analysis Settings
VIDEO_ANALYSIS = {
    'SCENE_DETECTION_THRESHOLD': 30.0,  # PySceneDetect sensitivity
    'WHISPER_MODEL': 'large-v3',        # Whisper model size
    'OBJECT_DETECTION_MODEL': 'yolov8x.pt',  # YOLO model
    'SENTIMENT_MODEL': 'distilbert-base-uncased-finetuned-sst-2-english',
    'MAX_VIDEO_SIZE_MB': 500,           # Max upload size
    'MAX_VIDEO_DURATION_SECONDS': 120,  # Max 2 minutes
    'SCRIPT_GENERATION_MODEL': 'Qwen/Qwen2.5-7B-Instruct',
    'ENABLE_OBJECT_DETECTION': True,
    'ENABLE_SENTIMENT_ANALYSIS': True,
    'ENABLE_AUDIENCE_INSIGHTS': True,
}

# Celery task configuration
CELERY_TASK_ROUTES = {
    'cw.tvspots.tasks.analyze_video_task': {'queue': 'default'},
}
```

### Environment Variables

```bash
# .env additions

# Optional: Use cloud APIs instead of local models
ASSEMBLYAI_API_KEY=your_key_here  # Alternative to local Whisper
ROBOFLOW_API_KEY=your_key_here    # Alternative to local YOLO

# Storage
VIDEO_UPLOAD_PATH=media/ad_unit_media/
KEYFRAME_UPLOAD_PATH=media/keyframes/

# Model paths
WHISPER_MODEL_PATH=/path/to/models/whisper/
YOLO_MODEL_PATH=/path/to/models/yolo/
```

## Migration Path

### Database Migrations

```python
# migrations/0XXX_add_ad_unit_media_models.py

class Migration(migrations.Migration):
    dependencies = [
        ('tvspots', '0XXX_previous_migration'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdUnitMedia',
            fields=[...],
        ),
        migrations.CreateModel(
            name='VideoProcessingResult',
            fields=[...],
        ),
        migrations.CreateModel(
            name='KeyFrame',
            fields=[...],
        ),
        migrations.AddField(
            model_name='videoadunit',
            name='source_media',
            field=models.OneToOneField(
                null=True, blank=True,
                on_delete=models.SET_NULL,
                related_name='video_ad_unit',
                to='tvspots.AdUnitMedia'
            ),
        ),
    ]
```

### Data Migration

No data migration needed - this is a new feature with no existing data to migrate.

## Security Considerations

### File Upload Security

```python
# Validate file type and size
from django.core.exceptions import ValidationError

def validate_video_file(file):
    """Validate uploaded video file"""

    # Check file extension
    valid_extensions = ['.mp4', '.mov', '.avi']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(f'Unsupported file type: {ext}')

    # Check file size (500MB max)
    max_size = 500 * 1024 * 1024  # 500MB in bytes
    if file.size > max_size:
        raise ValidationError(f'File too large: {file.size} bytes')

    # Check MIME type
    import magic
    mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)

    valid_mimes = ['video/mp4', 'video/quicktime', 'video/x-msvideo']
    if mime not in valid_mimes:
        raise ValidationError(f'Invalid file type: {mime}')
```

### Permissions

```python
# Restrict video upload to authorized users
class AdUnitMediaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        """Only staff with 'can_upload_videos' permission"""
        return request.user.has_perm('tvspots.can_upload_videos')

    def has_change_permission(self, request, obj=None):
        """Users can only edit their own uploads"""
        if obj and obj.created_by != request.user:
            return request.user.is_superuser
        return True
```

## Open Questions

### Technical Decisions

1. **Local vs Cloud Processing?**
   - **Local**: Whisper Large v3, YOLO v8, Qwen 2.5 7B (GPU required)
   - **Cloud**: AssemblyAI (transcription), Roboflow (vision), Anthropic (LLM)
   - **Recommendation**: Start local (cost control), add cloud fallback for scale

2. **Real-time vs Batch Processing?**
   - **Real-time**: Process immediately on upload (long wait times)
   - **Batch**: Queue multiple videos, process overnight
   - **Recommendation**: Real-time with clear progress indicators

3. **Storage Strategy?**
   - Original MP4: Keep or delete after processing?
   - Key frames: Store all or just representative samples?
   - **Recommendation**: Keep originals for 30 days, store all key frames

4. **Model Selection?**
   - Whisper: large-v3 (best quality) vs medium (faster)
   - YOLO: v8x (most accurate) vs v8l (faster)
   - **Recommendation**: Quality first (large-v3 + v8x), optimize later

### Product Decisions

5. **Editing Capabilities?**
   - Should users edit the generated script before creating VideoAdUnit?
   - Allow re-running individual pipeline stages?
   - **Recommendation**: Yes, make script fully editable with validation

6. **Approval Workflow?**
   - Require explicit approval before creating VideoAdUnit?
   - Auto-create and allow edit later?
   - **Recommendation**: Explicit "Create Origin VideoAdUnit" action

7. **Batch Upload?**
   - Support uploading multiple videos at once?
   - Bulk create VideoAdUnits?
   - **Recommendation**: Phase 2 feature, start with single upload

8. **Video Preview?**
   - Embed video player in admin?
   - Show side-by-side with script?
   - **Recommendation**: Yes, embed player with scene timestamps

### Business Questions

9. **GPU Requirements?**
   - Whisper Large v3 + YOLO v8 + Qwen 2.5 7B = significant GPU memory
   - Estimated: 16GB+ VRAM for simultaneous loading
   - **Recommendation**: Sequential processing (already implemented in Celery)

10. **Processing Time Expectations?**
    - 30s video estimated processing: 2-5 minutes total
    - Scene detection: 10-20s
    - Transcription: 30-60s (Whisper large-v3)
    - Object detection: 20-30s (8 scenes × 3-4s each)
    - Script generation: 60-120s (LLM inference)
    - **Recommendation**: Set expectation of 3-5 minutes, optimize later

## Success Metrics

### Performance Metrics
- **Processing Time**: < 5 minutes for 30s video
- **Accuracy**: > 90% transcription accuracy (WER < 0.1)
- **Scene Detection**: > 85% precision (manually validated sample)
- **Object Detection**: > 80% relevant objects identified

### User Experience Metrics
- **Time Saved**: Reduce origin script creation from 2 hours → 15 minutes (review + edit)
- **Adoption**: 70%+ of new campaigns use video upload vs manual entry
- **Quality**: 90%+ of generated scripts require only minor edits

### Business Impact
- **Throughput**: Enable 3x more origin scripts per week
- **Adaptation Pipeline**: Increase adaptation requests by 40% (lower barrier to entry)
- **ROI**: Positive ROI within 3 months based on time savings

## Future Enhancements

### Phase 2+ Features

1. **Multi-language Support**: Transcribe in 50+ languages via Whisper
2. **Brand Detection**: Train custom YOLO model to recognize specific brand assets
3. **Speaker Diarization**: Identify multiple speakers in audio
4. **Shot Classification**: Classify shots (close-up, wide, product shot, etc.)
5. **Color Grading Analysis**: Extract LUTs and color grading metadata
6. **Music Recognition**: Identify background music tracks (Shazam API)
7. **Competitive Analysis**: Compare visual style to competitor ads
8. **Version Comparison**: Track changes across multiple edits of same spot
9. **Auto-tagging**: Tag scenes with keywords for search/discovery
10. **Storyboard Generation**: Auto-create storyboard images from key frames

### Advanced AI Features

1. **Scene Similarity Search**: Find similar scenes across all processed videos (CLIP embeddings)
2. **Style Transfer**: Apply visual style from one video to storyboard generation
3. **Synthetic Script Variations**: Generate alternative scripts for A/B testing
4. **Cultural Adaptation Hints**: Suggest specific scenes that may need cultural adaptation
5. **Automatic LoRA Selection**: Recommend LoRAs based on visual style analysis

## Documentation Needs

### Developer Documentation
- [ ] API reference for video analysis library
- [ ] Integration guide for adding new vision models
- [ ] Performance tuning guide
- [ ] Troubleshooting common issues

### User Documentation
- [ ] Video upload guide (supported formats, size limits)
- [ ] Script editing best practices
- [ ] Interpretation guide for audience insights
- [ ] FAQ for common questions

## Dependencies

### New Python Packages

```toml
# Add to pyproject.toml

[project]
dependencies = [
    # Existing dependencies...

    # Video processing
    "scenedetect[opencv]>=0.6.2",
    "opencv-python>=4.8.0",
    "av>=11.0.0",  # PyAV for media handling

    # Audio processing
    "openai-whisper>=20231117",
    "librosa>=0.10.0",

    # Computer vision
    "ultralytics>=8.0.0",  # YOLO v8
    "pillow>=10.0.0",

    # NLP & LLM
    "transformers>=4.35.0",
    "torch>=2.1.0",

    # Utilities
    "python-magic>=0.4.27",  # MIME type detection
]
```

### System Dependencies

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
apt-get install ffmpeg libmagic1

# NVIDIA GPU support (for production)
# Ensure CUDA 11.8+ and cuDNN are installed
```

## Conclusion

This specification provides a comprehensive blueprint for implementing automated video analysis and origin script extraction. The feature will:

1. **Accelerate workflows**: Reduce manual script writing from hours to minutes
2. **Improve consistency**: Standardize script format and structure
3. **Enable scalability**: Process more campaigns with same resources
4. **Provide insights**: Extract creative intelligence for better adaptations
5. **Integrate seamlessly**: Flow directly into existing adaptation pipeline

**Next Steps**:
1. Review and approve specification
2. Set up development environment with GPU access
3. Begin Phase 1 implementation (MVP)
4. Iterate based on user feedback

**Estimated Timeline**: 6-7 weeks from approval to production-ready feature
