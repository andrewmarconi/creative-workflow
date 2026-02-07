"""State helpers bridging AdaptationJob (ORM) and PipelineState (in-memory).

Functions here handle the translation between Django models and the
LangGraph ``PipelineState`` TypedDict used by pipeline nodes.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Optional

from django.utils import timezone

from cw.lib.insights import compose_insights_as_markdown

if TYPE_CHECKING:
    from cw.lib.pipeline.schemas import PipelineState

logger = logging.getLogger(__name__)


def build_initial_state(job) -> PipelineState:
    """Build the initial ``PipelineState`` dict from an ``AdaptationJob``.

    Mirrors the data-fetching logic in ``AdaptationGenerator.adapt()`` so
    the pipeline nodes receive the same origin data the single-step path uses.
    """
    origin_version = job.origin_version
    target_market = job.target_market
    tv_spot = origin_version.tv_spot

    effective_language = job.effective_language
    effective_model = job.effective_llm_model

    # Serialize origin version + script rows (same as AdaptationGenerator.adapt())
    original_spot = {
        "client_name": tv_spot.client_name,
        "brand_name": tv_spot.brand_name,
        "script_title": tv_spot.script_title,
        "total_runtime_seconds": tv_spot.total_runtime_seconds,
        "language": origin_version.language.code,
        "script_rows": [
            {
                "shot_number": row.shot_number,
                "timecode_start": row.timecode_start,
                "duration_seconds": float(row.duration_seconds) if row.duration_seconds else None,
                "visual_text": row.visual_text,
                "audio_text": row.audio_text,
            }
            for row in origin_version.script_rows.all().order_by("order_index")
        ],
    }

    language_code = effective_language.code if effective_language else "en"
    model_id = effective_model.model_id if effective_model else "Qwen/Qwen2.5-3B-Instruct"
    load_in_4bit = getattr(effective_model, "load_in_4bit", False) if effective_model else False

    # Compose insights from all levels (region → country → language → market)
    insights_markdown = compose_insights_as_markdown(job)

    return {
        # Input
        "job_id": job.pk,
        "model_id": model_id,
        "load_in_4bit": load_in_4bit,
        "original_script": json.dumps(original_spot, indent=2, ensure_ascii=False),
        "target_market_name": target_market.name,
        "target_market_code": target_market.code.upper(),
        "target_market_rules": insights_markdown,  # Now uses composed hierarchical insights
        "target_market_language": language_code,
        "language_code": language_code,
        "num_script_rows": len(original_spot["script_rows"]),
        # Intermediate (populated by nodes)
        "concept_brief": None,
        "cultural_brief": None,
        "adapted_script": None,
        # Evaluation
        "cultural_feedback": None,
        "concept_feedback": None,
        "cultural_revision_count": 0,
        "concept_revision_count": 0,
        # Terminal
        "status": "processing",
        "error_message": None,
    }


def save_pipeline_result(job, final_state: PipelineState):
    """Persist the pipeline's final state back to the ``AdaptationJob``.

    On success, creates ``TvSpotVersion`` and ``TvSpotScriptRow`` records
    exactly as the single-step task does.  On failure, records the error.
    """
    from cw.lib.adaptation import AdaptationOutput
    from cw.tvspots.models import TvSpotScriptRow, TvSpotVersion

    adapted_json = final_state.get("adapted_script")

    if adapted_json:
        result = AdaptationOutput.model_validate_json(adapted_json)

        new_version = TvSpotVersion.objects.create(
            tv_spot=job.tv_spot,
            version_type="adaptation",
            market=job.target_market,
            code=result.code,
            name=result.name,
            language=result.language,
            visual_style_prompt=result.visual_style_prompt,
            is_active=True,
        )

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

        job.result_version = new_version
        job.status = "completed"
        job.completed_at = timezone.now()
    else:
        job.status = "failed"
        job.error_message = final_state.get("error_message") or "Pipeline produced no adapted script"
        job.completed_at = timezone.now()

    # Always persist pipeline metadata
    job.pipeline_metadata = {
        "cultural_revision_count": final_state.get("cultural_revision_count", 0),
        "concept_revision_count": final_state.get("concept_revision_count", 0),
        "final_model_id": final_state.get("model_id"),
        "final_status": final_state.get("status"),
    }

    job.save(update_fields=[
        "status", "result_version", "completed_at", "error_message", "pipeline_metadata",
    ])

    logger.info(
        f"Pipeline result saved: status={job.status}",
        extra={"job_id": job.pk, "status": job.status},
    )


def get_alternative_model(language_code: str) -> Optional[object]:
    """Look up the first active alternative model for a language.

    Returns ``None`` if no alternatives are available.
    """
    from cw.core.models import Language

    try:
        lang = Language.objects.get(code=language_code, is_active=True)
    except Language.DoesNotExist:
        return None

    alt = lang.alternative_models.filter(is_active=True).first()
    if alt:
        logger.info(f"Alternative model for '{language_code}': {alt.model_id}")
    return alt
