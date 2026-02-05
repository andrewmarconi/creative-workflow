"""
Celery tasks for TV spot adaptation and storyboard generation.

These tasks integrate with cw.lib modules:
- cw.lib.adaptation (AdaptationGenerator)
- cw.lib.storyboard (StoryboardGenerator)
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TV Spot Adaptation Tasks
# ---------------------------------------------------------------------------


@shared_task(bind=True, name="cw.tvspots.tasks.create_adaptation_task")
def create_adaptation_task(self, origin_version_id, target_market_id):
    """
    Create a culturally-adapted TV spot version using LLM.

    Args:
        origin_version_id: ID of the origin TvSpotVersion to adapt from
        target_market_id: ID of the target AdaptationMarket

    Returns:
        Dict with adaptation results
    """
    from cw.tvspots.models import AdaptationMarket, TvSpotScriptRow, TvSpotVersion

    origin_version = TvSpotVersion.objects.get(id=origin_version_id)
    target_market = AdaptationMarket.objects.get(id=target_market_id)
    tv_spot = origin_version.tv_spot

    logger.info(
        f"Starting adaptation of '{tv_spot.script_title}' to {target_market.name}",
        extra={
            "tv_spot_id": tv_spot.pk,
            "origin_version_id": origin_version_id,
            "target_market_id": target_market_id,
            "target_market_code": target_market.code,
        },
    )

    try:
        # Get the adaptation generator
        from cw.lib.adaptation import get_adaptation_generator

        generator = get_adaptation_generator()

        # Generate the adaptation
        result = generator.adapt(origin_version, target_market)

        # Create the new TvSpotVersion
        new_version = TvSpotVersion.objects.create(
            tv_spot=tv_spot,
            version_type="adaptation",
            market=target_market,
            code=result.code,
            name=result.name,
            language=result.language,
            visual_style_prompt=result.visual_style_prompt,
            is_active=True,
        )

        # Create the adapted script rows
        for idx, row_data in enumerate(result.script_rows):
            TvSpotScriptRow.objects.create(
                tv_spot_version=new_version,
                order_index=idx,
                shot_number=row_data.shot_number,
                timecode_start=row_data.timecode_start,
                duration_seconds=row_data.duration_seconds,
                visual_text=row_data.visual_text,
                audio_text=row_data.audio_text,
            )

        logger.info(
            f"Adaptation created successfully: {new_version.name}",
            extra={
                "tv_spot_id": tv_spot.pk,
                "new_version_id": new_version.pk,
                "adaptation_code": new_version.code,
                "num_rows": len(result.script_rows),
            },
        )

        return {
            "status": "success",
            "tv_spot_id": tv_spot.pk,
            "origin_version_id": origin_version_id,
            "new_version_id": new_version.pk,
            "adaptation_code": new_version.code,
            "adaptation_name": new_version.name,
            "num_rows": len(result.script_rows),
        }

    except Exception as e:
        logger.error(
            f"Adaptation failed: {e}",
            extra={
                "tv_spot_id": tv_spot.pk,
                "origin_version_id": origin_version_id,
                "target_market_id": target_market_id,
                "error": str(e),
            },
        )
        return {
            "status": "failed",
            "origin_version_id": origin_version_id,
            "target_market_id": target_market_id,
            "error": str(e),
        }


@shared_task(bind=True, name="cw.tvspots.tasks.generate_storyboard_task")
def generate_storyboard_task(self, storyboard_job_id, enhance_prompts=True):
    """
    Generate storyboard images for a TV spot version.

    This task:
    1. Generates image prompts from script rows
    2. Creates Prompt and DiffusionJob records for each frame
    3. Queues the DiffusionJobs for image generation

    Args:
        storyboard_job_id: ID of the StoryboardJob
        enhance_prompts: Whether to use LLM to enhance prompts

    Returns:
        Dict with generation results
    """
    from cw.diffusion.tasks import generate_images_task
    from cw.tvspots.models import StoryboardJob
    from cw.lib.storyboard import StoryboardGenerator, create_storyboard_jobs

    storyboard_job = StoryboardJob.objects.get(id=storyboard_job_id)
    tv_spot_version = storyboard_job.tv_spot_version
    tv_spot = tv_spot_version.tv_spot

    logger.info(
        f"Starting storyboard generation for '{tv_spot.script_title}' / {tv_spot_version.code}",
        extra={
            "storyboard_job_id": storyboard_job_id,
            "tv_spot_id": tv_spot.pk,
            "version_id": tv_spot_version.pk,
            "images_per_row": storyboard_job.images_per_row,
        },
    )

    try:
        # Update job status
        storyboard_job.status = "processing"
        storyboard_job.save()

        # Generate prompts from script rows
        generator = StoryboardGenerator(use_llm=enhance_prompts)
        prompts = generator.generate_prompts_for_version(
            tv_spot_version,
            enhance=enhance_prompts,
        )

        logger.info(
            f"Generated {len(prompts)} prompts for storyboard",
            extra={
                "storyboard_job_id": storyboard_job_id,
                "num_prompts": len(prompts),
            },
        )

        # Create DiffusionJobs and StoryboardImages
        created_jobs = create_storyboard_jobs(storyboard_job, prompts)

        # Queue the DiffusionJobs for image generation
        for job in created_jobs:
            generate_images_task.apply_async(args=[job.id], queue="default")
            job.status = "queued"
            job.save()

        # Update storyboard job status
        storyboard_job.status = "completed"
        storyboard_job.completed_at = timezone.now()
        storyboard_job.save()

        logger.info(
            f"Storyboard generation complete: {len(created_jobs)} jobs queued",
            extra={
                "storyboard_job_id": storyboard_job_id,
                "num_jobs": len(created_jobs),
            },
        )

        return {
            "status": "success",
            "storyboard_job_id": storyboard_job_id,
            "num_prompts": len(prompts),
            "num_jobs": len(created_jobs),
            "job_ids": [job.id for job in created_jobs],
        }

    except Exception as e:
        storyboard_job.status = "failed"
        storyboard_job.error_message = str(e)
        storyboard_job.save()

        logger.error(
            f"Storyboard generation failed: {e}",
            extra={
                "storyboard_job_id": storyboard_job_id,
                "error": str(e),
            },
        )

        return {
            "status": "failed",
            "storyboard_job_id": storyboard_job_id,
            "error": str(e),
        }
