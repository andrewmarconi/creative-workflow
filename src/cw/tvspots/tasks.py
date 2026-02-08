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
