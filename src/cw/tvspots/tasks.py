"""
Celery tasks for video ad unit adaptation and storyboard generation.

These tasks integrate with cw.lib modules:
- cw.lib.pipeline (multi-agent adaptation pipeline)
- cw.lib.storyboard (StoryboardGenerator)
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Video Ad Unit Adaptation Tasks
# ---------------------------------------------------------------------------


@shared_task(bind=True, name="cw.tvspots.tasks.create_adaptation_task")
def create_adaptation_task(self, video_ad_unit_id):
    """
    Create a culturally-adapted video ad unit using the multi-agent pipeline.

    Args:
        video_ad_unit_id: ID of the VideoAdUnit to process (must be an adaptation)

    Returns:
        Dict with adaptation results
    """
    from cw.tvspots.models import VideoAdUnit

    video_ad_unit = VideoAdUnit.objects.get(id=video_ad_unit_id)

    # Build target description
    target_parts = [video_ad_unit.region.name] if video_ad_unit.region else []
    if video_ad_unit.country:
        target_parts.append(video_ad_unit.country.name)
    target_parts.append(f"({video_ad_unit.language.code})")
    target_desc = " / ".join(target_parts)

    logger.info(
        f"Starting adaptation of '{video_ad_unit.campaign.script_title}' "
        f"to {target_desc}",
        extra={
            "video_ad_unit_id": video_ad_unit_id,
            "use_pipeline": video_ad_unit.use_pipeline,
        },
    )

    from cw.lib.pipeline import run_adaptation_pipeline

    try:
        run_adaptation_pipeline(video_ad_unit)
        return {
            "status": "success",
            "video_ad_unit_id": video_ad_unit_id,
            "pipeline": True,
        }
    except Exception as e:
        video_ad_unit.status = "failed"
        video_ad_unit.error_message = str(e)
        video_ad_unit.completed_at = timezone.now()
        video_ad_unit.save(update_fields=["status", "error_message", "completed_at"])

        logger.error(f"Pipeline adaptation failed: {e}", extra={
            "video_ad_unit_id": video_ad_unit_id, "error": str(e),
        })
        return {
            "status": "failed",
            "video_ad_unit_id": video_ad_unit_id,
            "pipeline": True,
            "error": str(e),
        }


@shared_task(bind=True, name="cw.tvspots.tasks.generate_storyboard_task")
def generate_storyboard_task(self, storyboard_id, enhance_prompts=True):
    """
    Generate storyboard images for a video ad unit.

    This task:
    1. Generates image prompts from script rows
    2. Creates Prompt and DiffusionJob records for each frame
    3. Queues the DiffusionJobs for image generation

    Args:
        storyboard_id: ID of the Storyboard
        enhance_prompts: Whether to use LLM to enhance prompts

    Returns:
        Dict with generation results
    """
    from cw.diffusion.tasks import generate_images_task
    from cw.tvspots.models import Storyboard
    from cw.lib.storyboard import StoryboardGenerator, create_storyboard_jobs

    storyboard = Storyboard.objects.get(id=storyboard_id)
    video_ad_unit = storyboard.video_ad_unit
    campaign = video_ad_unit.campaign

    logger.info(
        f"Starting storyboard generation for '{campaign.script_title}' / {video_ad_unit.code}",
        extra={
            "storyboard_id": storyboard_id,
            "campaign_id": campaign.pk,
            "video_ad_unit_id": video_ad_unit.pk,
            "images_per_row": storyboard.images_per_row,
        },
    )

    try:
        # Update storyboard status
        storyboard.status = "processing"
        storyboard.save()

        # Evict pipeline LLM from VRAM before loading prompt enhancer
        from cw.diffusion.tasks import _evict_pipeline_model
        _evict_pipeline_model()

        # Generate prompts from script rows
        generator = StoryboardGenerator(use_llm=enhance_prompts)
        prompts = generator.generate_prompts_for_version(
            video_ad_unit,
            enhance=enhance_prompts,
        )

        logger.info(
            f"Generated {len(prompts)} prompts for storyboard",
            extra={
                "storyboard_id": storyboard_id,
                "num_prompts": len(prompts),
            },
        )

        # Clear GPU cache after prompt enhancement to free memory before image generation
        import torch
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
            logger.debug("Cleared MPS cache after prompt enhancement")
        elif torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.debug("Cleared CUDA cache after prompt enhancement")

        # Create DiffusionJobs and StoryboardImages
        created_jobs = create_storyboard_jobs(storyboard, prompts)

        # Queue the DiffusionJobs for image generation
        for job in created_jobs:
            generate_images_task.apply_async(args=[job.id], queue="default")
            job.status = "queued"
            job.save()

        # Update storyboard status
        storyboard.status = "completed"
        storyboard.completed_at = timezone.now()
        storyboard.save()

        logger.info(
            f"Storyboard generation complete: {len(created_jobs)} jobs queued",
            extra={
                "storyboard_id": storyboard_id,
                "num_jobs": len(created_jobs),
            },
        )

        return {
            "status": "success",
            "storyboard_id": storyboard_id,
            "num_prompts": len(prompts),
            "num_jobs": len(created_jobs),
            "job_ids": [job.id for job in created_jobs],
        }

    except Exception as e:
        storyboard.status = "failed"
        storyboard.error_message = str(e)
        storyboard.save()

        logger.error(
            f"Storyboard generation failed: {e}",
            extra={
                "storyboard_id": storyboard_id,
                "error": str(e),
            },
        )

        return {
            "status": "failed",
            "storyboard_id": storyboard_id,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Video Analysis Tasks (Origin Script Extraction)
# ---------------------------------------------------------------------------


@shared_task(bind=True, name="cw.tvspots.tasks.analyze_video_task", max_retries=3)
def analyze_video_task(self, ad_unit_media_id: int):
    """
    Analyze uploaded video and extract script, scenes, transcription, and insights.

    This task orchestrates the video processing pipeline:
    1. Extract video metadata (duration, resolution, etc.)
    2. Detect scenes using PySceneDetect
    3. Transcribe audio with Whisper
    4. Extract keyframes and detect objects with YOLO
    5. Analyze visual style (colors, lighting, camera work)
    6. Analyze sentiment (audio + visual)
    7. Categorize scenes
    8. Generate enhanced script
    9. Generate audience insights with LLM
    10. Create result object
    11. Save keyframes to database

    Args:
        ad_unit_media_id: ID of the AdUnitMedia to process

    Returns:
        Dict with processing results:
        {
            'status': 'success' | 'failed',
            'media_id': int,
            'result_id': int,
            'processing_time': float
        }
    """
    from cw.tvspots.models import AdUnitMedia, VideoProcessingResult

    logger.info(
        f"Starting video analysis for AdUnitMedia {ad_unit_media_id}",
        extra={"ad_unit_media_id": ad_unit_media_id},
    )

    try:
        media = AdUnitMedia.objects.get(id=ad_unit_media_id)
        media.status = "processing"
        media.processing_started_at = timezone.now()
        media.save(update_fields=["status", "processing_started_at"])

        video_path = media.video_file.path

        # Phase 1: Extract metadata
        logger.info("Extracting video metadata...")
        from cw.lib.video_analysis import extract_video_metadata

        metadata = extract_video_metadata(video_path)
        media.duration = metadata["duration"]
        media.resolution_width = metadata["width"]
        media.resolution_height = metadata["height"]
        media.frame_rate = metadata["frame_rate"]
        media.audio_channels = metadata["audio_channels"]
        media.audio_sample_rate = metadata["sample_rate"]
        media.file_size = metadata["file_size"]
        media.save(
            update_fields=[
                "duration",
                "resolution_width",
                "resolution_height",
                "frame_rate",
                "audio_channels",
                "audio_sample_rate",
                "file_size",
            ]
        )

        logger.info(
            f"Metadata extracted: {metadata['width']}x{metadata['height']}, "
            f"{metadata['duration']:.1f}s",
            extra={"metadata": metadata},
        )

        # Phase 2: Scene detection
        logger.info("Detecting scenes...")
        from cw.lib.video_analysis import detect_scenes

        scenes = detect_scenes(video_path)
        logger.info(
            f"Detected {len(scenes)} scenes",
            extra={"num_scenes": len(scenes)},
        )

        # Phase 3: Transcribe audio
        logger.info("Transcribing audio...")
        from cw.lib.video_analysis import transcribe_audio

        transcription = transcribe_audio(video_path)
        logger.info(
            f"Transcription complete: {transcription['language']}, "
            f"{len(transcription['segments'])} segments",
            extra={
                "language": transcription["language"],
                "num_segments": len(transcription["segments"]),
            },
        )

        # Phase 4: Extract keyframes and detect objects (Phase 2)
        import tempfile
        keyframes_dir = tempfile.mkdtemp(prefix="keyframes_")

        logger.info("Extracting keyframes...")
        keyframes = _extract_keyframes(video_path, scenes, keyframes_dir)

        logger.info("Detecting objects in keyframes...")
        from cw.lib.video_analysis import detect_objects, summarize_objects

        # Detect objects in each keyframe
        keyframe_detections = {}
        for scene_number, keyframe_path in keyframes.items():
            detections = detect_objects(keyframe_path, conf_threshold=0.5)
            keyframe_detections[scene_number] = detections

        # Summarize all detections across all keyframes
        all_detections = []
        for detections in keyframe_detections.values():
            all_detections.extend(detections)

        objects_summary = summarize_objects(all_detections)
        logger.info(
            f"Object detection complete: {objects_summary['total_objects']} objects detected",
            extra={"objects_summary": objects_summary},
        )

        # Phase 5: Analyze visual style (Phase 2)
        logger.info("Analyzing visual style...")
        from cw.lib.video_analysis import analyze_visual_style, analyze_camera_work

        keyframe_paths = list(keyframes.values())
        visual_style = analyze_visual_style(keyframe_paths)
        camera_work = analyze_camera_work(scenes)
        visual_style["camera_work"] = camera_work

        logger.info(
            f"Visual style analysis complete: {len(visual_style['dominant_colors'])} dominant colors",
            extra={"visual_style": visual_style},
        )

        # Phase 6: Analyze sentiment (Phase 2)
        logger.info("Analyzing sentiment...")
        from cw.lib.video_analysis import analyze_sentiment

        sentiment_analysis = analyze_sentiment(transcription, visual_style, objects_summary)
        logger.info(
            f"Sentiment analysis complete: {sentiment_analysis['overall_sentiment']}",
            extra={"sentiment": sentiment_analysis},
        )

        # Phase 7: Categorize scenes (Phase 2)
        logger.info("Categorizing scenes...")
        from cw.lib.video_analysis import categorize_scenes, summarize_categories

        categorized_scenes = categorize_scenes(scenes, keyframe_detections, transcription)
        categories_summary = summarize_categories(categorized_scenes)

        logger.info(
            f"Scene categorization complete: {categories_summary['primary_categories']}",
            extra={"categories": categories_summary},
        )

        # Phase 8: Generate enhanced script with vision inputs (Phase 2)
        logger.info("Generating enhanced script...")
        script = _generate_basic_script(categorized_scenes, transcription)

        # Phase 9: Generate audience insights (Phase 3 Part 1)
        logger.info("Generating audience insights...")
        from cw.lib.video_analysis.audience_insights import generate_audience_insights

        audience_insights = generate_audience_insights(
            script=script,
            visual_style=visual_style,
            sentiment=sentiment_analysis,
            transcription=transcription,
            categories=categories_summary,
        )
        logger.info(
            f"Audience insights generation complete",
            extra={"audience_insights": audience_insights},
        )

        # Phase 10: Create result object
        result = VideoProcessingResult.objects.create(
            scenes=categorized_scenes,
            script=script,
            transcription=transcription,
            visual_style=visual_style,
            objects_summary=objects_summary,
            sentiment_analysis=sentiment_analysis,
            categories=categories_summary,
            audience_insights=audience_insights,
            processing_time=(timezone.now() - media.processing_started_at).total_seconds(),
            models_used={
                "scene_detection": "PySceneDetect",
                "transcription": "Whisper Large v3",
                "object_detection": "YOLO v8x",
                "visual_style": "OpenCV + k-means",
                "sentiment": "keyword-based",
                "script_generation": "Basic (MVP)",
                "audience_insights": "LLM-based (Qwen 2.5)",
            },
        )

        # Phase 11: Save keyframes with detected objects to KeyFrame model
        from cw.tvspots.models import KeyFrame
        from django.core.files import File

        logger.info("Saving keyframes to database...")
        for scene_number, keyframe_path in keyframes.items():
            # Find corresponding scene for timestamp
            scene = next((s for s in categorized_scenes if s["scene_number"] == scene_number), None)
            if not scene:
                continue

            timestamp = (scene["start_time"] + scene["end_time"]) / 2
            detections = keyframe_detections.get(scene_number, [])

            # Create KeyFrame record
            with open(keyframe_path, "rb") as f:
                keyframe = KeyFrame.objects.create(
                    result=result,
                    scene_number=scene_number,
                    timestamp=timestamp,
                    detected_objects=detections,
                    colors=visual_style.get("dominant_colors", [])[:3],  # Top 3 colors
                )
                keyframe.image.save(
                    f"scene_{scene_number:03d}.jpg",
                    File(f),
                    save=True,
                )

        logger.info(f"Saved {len(keyframes)} keyframes to database")

        # Clean up temporary keyframes directory
        import shutil
        shutil.rmtree(keyframes_dir, ignore_errors=True)

        # Link result to media
        media.result = result
        media.status = "completed"
        media.processing_completed_at = timezone.now()
        media.save(
            update_fields=["result", "status", "processing_completed_at"]
        )

        logger.info(
            f"Video analysis complete for AdUnitMedia {ad_unit_media_id}",
            extra={
                "ad_unit_media_id": ad_unit_media_id,
                "result_id": result.id,
                "processing_time": result.processing_time,
            },
        )

        return {
            "status": "success",
            "media_id": media.id,
            "result_id": result.id,
            "processing_time": result.processing_time,
        }

    except Exception as e:
        logger.error(
            f"Video analysis failed for AdUnitMedia {ad_unit_media_id}: {e}",
            extra={"ad_unit_media_id": ad_unit_media_id, "error": str(e)},
            exc_info=True,
        )

        # Update media with error
        media = AdUnitMedia.objects.get(id=ad_unit_media_id)
        media.status = "failed"
        media.processing_error = str(e)
        media.processing_completed_at = timezone.now()
        media.save(
            update_fields=["status", "processing_error", "processing_completed_at"]
        )

        # Retry with exponential backoff if not max retries
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying video analysis (attempt {self.request.retries + 1}/{self.max_retries})",
                extra={"ad_unit_media_id": ad_unit_media_id},
            )
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

        return {
            "status": "failed",
            "media_id": ad_unit_media_id,
            "error": str(e),
        }


def _extract_keyframes(video_path: str, scenes: list, output_dir: str) -> dict:
    """
    Extract one keyframe per scene (middle frame of each scene).

    Args:
        video_path: Path to video file
        scenes: List of scene dictionaries
        output_dir: Directory to save keyframe images

    Returns:
        Dict mapping scene_number to keyframe path
    """
    import cv2
    import os
    from pathlib import Path

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    keyframes = {}

    for scene in scenes:
        scene_number = scene["scene_number"]
        # Extract middle frame of scene
        mid_time = (scene["start_time"] + scene["end_time"]) / 2
        mid_frame = int(mid_time * fps)

        # Seek to frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
        ret, frame = cap.read()

        if ret:
            # Save keyframe
            keyframe_path = os.path.join(output_dir, f"scene_{scene_number:03d}.jpg")
            cv2.imwrite(keyframe_path, frame)
            keyframes[scene_number] = keyframe_path

    cap.release()
    logger.info(f"Extracted {len(keyframes)} keyframes")
    return keyframes


def _generate_basic_script(scenes, transcription):
    """
    Generate a basic script from scenes and transcription (MVP version).

    This is a simple implementation that maps transcription segments to scenes.
    Phase 2 will add LLM-based script generation with visual descriptions.

    Args:
        scenes: List of detected scenes
        transcription: Transcription dictionary with segments

    Returns:
        Script dictionary in tvspot.schema.json format
    """
    script_scenes = []

    for scene in scenes:
        # Find transcription segments that overlap with this scene
        scene_audio = []
        for segment in transcription["segments"]:
            if (
                segment["start"] >= scene["start_time"]
                and segment["start"] < scene["end_time"]
            ):
                scene_audio.append(segment["text"])

        # Combine audio segments
        voiceover = " ".join(scene_audio) if scene_audio else ""

        script_scenes.append(
            {
                "scene_number": scene["scene_number"],
                "duration": scene["duration"],
                "visual": f"Scene {scene['scene_number']} (extracting visual description in Phase 2)",
                "audio": {
                    "voiceover": voiceover,
                    "music": "",
                    "sfx": "",
                },
                "action": "",
                "products": [],
                "sentiment": "",
            }
        )

    return {"scenes": script_scenes}
