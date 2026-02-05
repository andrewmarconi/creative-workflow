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
def create_adaptation_task(self, adaptation_job_id):
    """
    Create a culturally-adapted TV spot version using LLM.

    Args:
        adaptation_job_id: ID of the AdaptationJob to process

    Returns:
        Dict with adaptation results
    """
    from cw.tvspots.models import AdaptationJob, TvSpotScriptRow, TvSpotVersion

    adaptation_job = AdaptationJob.objects.get(id=adaptation_job_id)
    origin_version = adaptation_job.origin_version
    target_market = adaptation_job.target_market
    tv_spot = adaptation_job.tv_spot

    logger.info(
        f"Starting adaptation of '{tv_spot.script_title}' to {target_market.name}",
        extra={
            "adaptation_job_id": adaptation_job_id,
            "tv_spot_id": tv_spot.pk,
            "origin_version_id": origin_version.pk,
            "target_market_id": target_market.pk,
            "target_market_code": target_market.code,
        },
    )

    # Update job status to processing
    adaptation_job.status = "processing"
    adaptation_job.started_at = timezone.now()
    adaptation_job.save(update_fields=["status", "started_at"])

    try:
        # Get the adaptation generator
        from cw.lib.adaptation import get_adaptation_generator

        generator = get_adaptation_generator()

        # Generate the adaptation using job's effective language and model
        result = generator.adapt(adaptation_job)

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

        # Update job as completed
        adaptation_job.status = "completed"
        adaptation_job.result_version = new_version
        adaptation_job.completed_at = timezone.now()
        adaptation_job.save(update_fields=["status", "result_version", "completed_at"])

        logger.info(
            f"Adaptation created successfully: {new_version.name}",
            extra={
                "adaptation_job_id": adaptation_job_id,
                "tv_spot_id": tv_spot.pk,
                "new_version_id": new_version.pk,
                "adaptation_code": new_version.code,
                "num_rows": len(result.script_rows),
            },
        )

        return {
            "status": "success",
            "adaptation_job_id": adaptation_job_id,
            "tv_spot_id": tv_spot.pk,
            "origin_version_id": origin_version.pk,
            "new_version_id": new_version.pk,
            "adaptation_code": new_version.code,
            "adaptation_name": new_version.name,
            "num_rows": len(result.script_rows),
        }

    except Exception as e:
        # Update job as failed
        adaptation_job.status = "failed"
        adaptation_job.error_message = str(e)
        adaptation_job.completed_at = timezone.now()
        adaptation_job.save(update_fields=["status", "error_message", "completed_at"])

        logger.error(
            f"Adaptation failed: {e}",
            extra={
                "adaptation_job_id": adaptation_job_id,
                "tv_spot_id": tv_spot.pk,
                "origin_version_id": origin_version.pk,
                "target_market_id": target_market.pk,
                "error": str(e),
            },
        )
        return {
            "status": "failed",
            "adaptation_job_id": adaptation_job_id,
            "origin_version_id": origin_version.pk,
            "target_market_id": target_market.pk,
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
