Video Upload & Analysis
=======================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

How the video processing pipeline analyzes uploaded media.

Planned content:

- Upload flow and ``AdUnitMedia`` model
- Security validation (``VideoFileValidator``: file type, size, codec, format)
- Analysis modules:

  - Scene detection (PySceneDetect)
  - Audio transcription (Whisper)
  - Object detection (YOLO v8x)
  - Visual style analysis (OpenCV: colors, brightness, contrast, lighting)
  - Sentiment analysis (text + visual)
  - Scene categorization (people, product, lifestyle)
  - Audience insights (LLM-generated demographics, psychographics, market potential)

- ``VideoProcessingResult`` and ``KeyFrame`` models
- Viewing results in the admin
