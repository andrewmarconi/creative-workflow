Video Upload & Analysis
=======================

This guide covers uploading video files, the security validation pipeline, and the 10-phase video analysis process.

Overview
--------

The video analysis pipeline extracts structured data from uploaded video files — scenes, transcription, objects, visual style, sentiment, and audience insights — and produces a ``VideoProcessingResult`` that can be used to create origin ad units.

.. mermaid::

   graph TD
       Upload[Upload Video] --> Validate[Security Validation]
       Validate --> Metadata[1. Extract Metadata]
       Metadata --> Scenes[2. Detect Scenes]
       Scenes --> Transcribe[3. Transcribe Audio]
       Transcribe --> Keyframes[4. Extract Keyframes]
       Keyframes --> Objects[5. Detect Objects]
       Objects --> Style[6. Analyze Visual Style]
       Style --> Sentiment[7. Analyze Sentiment]
       Sentiment --> Categories[8. Categorize Scenes]
       Categories --> Script[9. Generate Script]
       Script --> Insights[10. Audience Insights]
       Insights --> Result[VideoProcessingResult]

Uploading a Video
-----------------

Videos are uploaded via the **Ad Unit Media** model, linked to a Campaign:

1. Navigate to **TV Spots > Ad Unit Media > Add Ad Unit Media**
2. Select the **Campaign**
3. Upload an **MP4 video file**
4. Save — the ``analyze_video_task`` is automatically queued

The upload process runs security validation before saving (see below).

Security Validation
-------------------

The ``VideoFileValidator`` runs five validators in sequence on every upload:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Validator
     - What It Checks
   * - **FileSizeValidator**
     - File size between 1 byte and 500 MB (configurable via ``VIDEO_MAX_UPLOAD_SIZE_BYTES``)
   * - **FileExtensionValidator**
     - Extension in whitelist: ``.mp4``, ``.mov``, ``.avi``, ``.mkv``, ``.webm``
   * - **MimeTypeValidator**
     - Detected MIME type (via ``libmagic``) matches allowed video types. Warns on mismatch between declared and detected MIME.
   * - **FileHeaderValidator**
     - File magic bytes match known video signatures (MP4 ftyp box, AVI RIFF, MKV/WebM EBML header)
   * - **FilenameSanitizer**
     - Removes path traversal patterns (``..``), control characters, and Windows-forbidden characters. Replaces spaces with underscores.

All validation failures are logged to the ``cw.lib.security`` logger for security auditing. If any validator fails, the upload is rejected with a combined error message.

Analysis Phases
---------------

The ``analyze_video_task`` orchestrates 10 analysis phases with progress tracking:

Phase 1: Extract Metadata
^^^^^^^^^^^^^^^^^^^^^^^^^^

Extracts video metadata using **PyAV**:

- Duration, resolution (width/height), frame rate
- Audio channels and sample rate
- File size

Progress: 0–10%

Phase 2: Scene Detection
^^^^^^^^^^^^^^^^^^^^^^^^^^

Detects scene boundaries using **PySceneDetect**:

- Identifies scene transitions (cuts, fades, dissolves)
- Returns scene list with start/end times and duration

Progress: 10–30%

Phase 3: Audio Transcription
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Transcribes audio using **Whisper** (Large v3):

- Full transcription with timestamps per segment
- Language detection and confidence score
- Speaker identification

Progress: 30–50%

Phase 4: Keyframe Extraction & Object Detection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extracts one keyframe per scene (middle frame) and runs **YOLO v8x** object detection:

- Keyframes saved as JPEG images
- Object detection with bounding boxes and confidence scores
- Objects summarized across all frames (counts, most common classes)

Progress: 50–70%

Phase 5: Visual Style Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Analyzes visual style from keyframes using **OpenCV** with k-means clustering:

- Dominant color palette (hex codes)
- Average brightness and contrast
- Lighting distribution (soft, harsh, dramatic)
- Exposure distribution (normal, overexposed, underexposed)

Phase 6: Camera Work Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Derived from scene data:

- Average scene duration and pacing (fast/medium/slow)
- Total scene count and number of transitions

Phase 7: Sentiment Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Combines text and visual signals:

- **Text sentiment** — keyword-based analysis of transcription
- **Visual sentiment** — derived from brightness, color warmth, and detected objects
- Overall sentiment score and confidence

Phase 8: Scene Categorization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Categorizes each scene into one of 10 categories based on detected objects, transcription content, and visual features:

- People, product, lifestyle, action, nature, urban, food, technology, abstract, other
- Primary categories identified from frequency across scenes

Phase 9: Script Generation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generates a structured script by mapping transcription segments to detected scenes:

- Each scene gets a visual description and associated voiceover text
- Output format matches the TV spot JSON schema (scene number, duration, visual, audio)

Phase 10: Audience Insights
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generates audience targeting insights using an **LLM** (Qwen 2.5):

- Primary audience demographics and psychographics
- Secondary audience segments
- Market potential analysis (high-fit markets, considerations)
- Schema-validated output via structured generation

Progress: 90–100%

VideoProcessingResult
---------------------

All analysis output is stored in a single ``VideoProcessingResult`` record with JSON fields:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Contents
   * - ``scenes``
     - Detected scenes with timestamps, visual descriptions, objects, colors, sentiment
   * - ``script``
     - Generated script in TV spot JSON format
   * - ``transcription``
     - Full transcription with timestamps, language, confidence, segments
   * - ``visual_style``
     - Color palette, brightness, contrast, lighting, camera work
   * - ``objects_summary``
     - Aggregated object detection: total count, per-class counts and confidence
   * - ``sentiment_analysis``
     - Overall sentiment, text sentiment, visual sentiment, scores
   * - ``categories``
     - Scene categorization summary with primary categories
   * - ``audience_insights``
     - LLM-generated demographics, psychographics, market potential
   * - ``processing_time``
     - Total processing time in seconds
   * - ``models_used``
     - Which model/library was used for each analysis phase

KeyFrame Records
^^^^^^^^^^^^^^^^

Each extracted keyframe is saved as a ``KeyFrame`` record linked to the result:

- Scene number and timestamp
- Saved image file
- Per-frame object detection results (label, confidence, bounding box)
- Dominant colors for the specific frame
- Embedding field (reserved for future similarity search)

AdUnitMedia Lifecycle
---------------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Status
     - Description
   * - ``pending``
     - Upload not yet started
   * - ``uploaded``
     - File uploaded, awaiting processing
   * - ``processing``
     - Analysis task running
   * - ``completed``
     - Analysis complete, result attached
   * - ``failed``
     - Analysis failed (check ``processing_error``)
   * - ``reviewed``
     - Results reviewed and approved

The task includes retry logic with exponential backoff (up to 3 retries, starting at 60 seconds).

Viewing Results
---------------

After processing completes:

1. View the **Ad Unit Media** record — metadata fields (duration, resolution, etc.) are populated
2. Click through to the linked **Video Processing Result** for full analysis data
3. View **Key Frames** as inline images with object detection overlay data
4. Use the result to inform the creation of an origin ad unit with accurate script rows
