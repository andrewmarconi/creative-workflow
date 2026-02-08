"""State helpers bridging VideoAdUnit (ORM) and PipelineState (in-memory).

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


def build_initial_state(video_ad_unit) -> PipelineState:
    """Build the initial ``PipelineState`` dict from a ``VideoAdUnit``.

    Mirrors the data-fetching logic used by the adaptation generator, providing
    pipeline nodes with the necessary origin data and target context.
    """
    source_ad_unit = video_ad_unit.source_ad_unit
    campaign = source_ad_unit.campaign

    effective_language = video_ad_unit.language
    effective_model = video_ad_unit.effective_llm_model

    # Serialize origin ad unit + script rows
    original_spot = {
        "client_name": campaign.client_name,
        "brand_name": campaign.brand_name,
        "script_title": campaign.script_title,
        "language": source_ad_unit.language.code if source_ad_unit.language else "en",
        "script_rows": [
            {
                "shot_number": row.shot_number,
                "timecode_start": row.timecode,
                "duration_seconds": None,  # Not tracked in AdUnitScriptRow
                "visual_text": row.visual_text,
                "audio_text": row.audio_text,
            }
            for row in source_ad_unit.script_rows.all().order_by("order_index")
        ],
    }

    language_code = effective_language.code if effective_language else "en"
    model_id = effective_model.model_id if effective_model else "Qwen/Qwen2.5-3B-Instruct"
    load_in_4bit = getattr(effective_model, "load_in_4bit", False) if effective_model else False

    # Compose insights from all levels (region → country → language)
    insights_markdown = compose_insights_as_markdown(video_ad_unit)

    # Build target market name from region/country/language
    target_parts = []
    if video_ad_unit.region:
        target_parts.append(video_ad_unit.region.name)
    if video_ad_unit.country:
        target_parts.append(video_ad_unit.country.name)
    target_market_name = " / ".join(target_parts) if target_parts else effective_language.name

    # Build target market code from region/country codes
    code_parts = []
    if video_ad_unit.region:
        code_parts.append(video_ad_unit.region.code)
    if video_ad_unit.country:
        code_parts.append(video_ad_unit.country.code)
    target_market_code = "-".join(code_parts).upper() if code_parts else language_code.upper()

    return {
        # Input
        "job_id": video_ad_unit.pk,
        "model_id": model_id,
        "load_in_4bit": load_in_4bit,
        "original_script": json.dumps(original_spot, indent=2, ensure_ascii=False),
        "target_market_name": target_market_name,
        "target_market_code": target_market_code,
        "target_market_rules": insights_markdown,  # Hierarchical insights from region → country → language
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


def save_pipeline_result(video_ad_unit, final_state: PipelineState):
    """Persist the pipeline's final state back to the ``VideoAdUnit``.

    On success, creates ``AdUnitScriptRow`` records for the adapted script.
    On failure, records the error.
    """
    from cw.lib.adaptation import AdaptationOutput
    from cw.tvspots.models import AdUnitScriptRow

    adapted_json = final_state.get("adapted_script")

    if adapted_json:
        from cw.core.models import Language

        result = AdaptationOutput.model_validate_json(adapted_json)

        # Lookup Language by code
        language_obj = Language.objects.get(code=result.language)

        # Update the VideoAdUnit with adapted content
        video_ad_unit.language = language_obj
        video_ad_unit.visual_style_prompt = result.visual_style_prompt
        video_ad_unit.status = "completed"
        video_ad_unit.completed_at = timezone.now()
        video_ad_unit.save(update_fields=["language", "visual_style_prompt", "status", "completed_at"])

        # Create script rows for the adapted content
        for idx, row_data in enumerate(result.script_rows):
            AdUnitScriptRow.objects.create(
                ad_unit=video_ad_unit,
                order_index=idx,
                shot_number=row_data.shot_number,
                timecode=row_data.timecode_start,
                visual_text=row_data.visual_text,
                audio_text=row_data.audio_text,
            )

        logger.info(
            f"Adapted script saved: {len(result.script_rows)} rows",
            extra={
                "video_ad_unit_id": video_ad_unit.pk,
                "num_rows": len(result.script_rows),
            },
        )
    else:
        video_ad_unit.status = "failed"
        video_ad_unit.error_message = final_state.get("error_message") or "Pipeline produced no adapted script"
        video_ad_unit.completed_at = timezone.now()
        video_ad_unit.save(update_fields=["status", "error_message", "completed_at"])

    # Always persist pipeline metadata
    video_ad_unit.pipeline_metadata = {
        "cultural_revision_count": final_state.get("cultural_revision_count", 0),
        "concept_revision_count": final_state.get("concept_revision_count", 0),
        "final_model_id": final_state.get("model_id"),
        "final_status": final_state.get("status"),
    }
    video_ad_unit.save(update_fields=["pipeline_metadata"])

    logger.info(
        f"Pipeline result saved: status={video_ad_unit.status}",
        extra={"video_ad_unit_id": video_ad_unit.pk, "status": video_ad_unit.status},
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
