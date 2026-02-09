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


_GATE_NODE_KEYS = ("concept", "culture", "format_gate", "culture_gate", "concept_gate", "brand_gate")


def _model_to_config(model) -> dict:
    """Convert an LLMModel instance to a config dict."""
    return {"model_id": model.model_id, "load_in_4bit": model.load_in_4bit}


def resolve_pipeline_models(video_ad_unit) -> dict:
    """Resolve LLM model config for each pipeline node.

    Fallback chain per non-writer node:
        1. AdUnit.pipeline_model_config[node_key]  (per-adaptation override)
        2. PipelineSettings.<node_key>_default_model  (app setting)
        3. PipelineSettings.global_default_model  (app fallback)
        4. Language primary model  (ultimate fallback)

    Writer fallback chain:
        1. AdUnit.pipeline_model_config["writer"]  (per-adaptation override)
        2. AdUnit.llm_model (existing FK)  (legacy override)
        3. Language primary model  (language default)
        4. PipelineSettings.global_default_model  (app fallback)

    Returns dict of {node_key: {"model_id": str, "load_in_4bit": bool}}.
    """
    from cw.core.models import LLMModel, PipelineSettings

    settings = PipelineSettings.get_instance()
    overrides = video_ad_unit.pipeline_model_config or {}
    language_model = video_ad_unit.language.primary_model if video_ad_unit.language else None
    global_default = settings.global_default_model

    config = {}

    # Resolve non-writer nodes
    for key in _GATE_NODE_KEYS:
        # 1. Per-adaptation override
        override_pk = overrides.get(key)
        if override_pk:
            model = LLMModel.objects.filter(pk=override_pk, is_active=True).first()
            if model:
                config[key] = _model_to_config(model)
                continue

        # 2. PipelineSettings per-node default
        settings_model = getattr(settings, f"{key}_default_model", None)
        if settings_model:
            config[key] = _model_to_config(settings_model)
            continue

        # 3. Global default
        if global_default:
            config[key] = _model_to_config(global_default)
            continue

        # 4. Language primary model (ultimate fallback)
        if language_model:
            config[key] = _model_to_config(language_model)

    # Resolve writer node (different fallback chain)
    writer_override_pk = overrides.get("writer")
    if writer_override_pk:
        model = LLMModel.objects.filter(pk=writer_override_pk, is_active=True).first()
        if model:
            config["writer"] = _model_to_config(model)
    if "writer" not in config:
        writer_model = video_ad_unit.effective_llm_model
        if writer_model:
            config["writer"] = _model_to_config(writer_model)
        elif global_default:
            config["writer"] = _model_to_config(global_default)

    return config


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
        "brand_name": campaign.brand.name if campaign.brand else "",
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

    # Resolve per-node model configuration
    model_config = resolve_pipeline_models(video_ad_unit)

    # Writer model for backward compat (state["model_id"] used as default fallback)
    writer_config = model_config.get("writer", {})
    model_id = writer_config.get("model_id") or (
        effective_model.model_id if effective_model else "Qwen/Qwen2.5-3B-Instruct"
    )
    load_in_4bit = writer_config.get("load_in_4bit", False) if writer_config else (
        getattr(effective_model, "load_in_4bit", False) if effective_model else False
    )

    # Compose insights from all levels (region → country → language → persona segments)
    insights_markdown = compose_insights_as_markdown(video_ad_unit)

    # Build target market name from persona or region/country/language
    if video_ad_unit.persona:
        target_market_name = video_ad_unit.persona.name
    else:
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
        "model_config": model_config,
        "original_script": json.dumps(original_spot, indent=2, ensure_ascii=False),
        "target_market_name": target_market_name,
        "target_market_code": target_market_code,
        "target_market_rules": insights_markdown,  # Hierarchical insights from region → country → language → persona segments
        "target_market_language": language_code,
        "language_code": language_code,
        "num_script_rows": len(original_spot["script_rows"]),
        "brand_guidelines": video_ad_unit.effective_brand.guidelines if video_ad_unit.effective_brand else "",
        # Intermediate (populated by nodes)
        "concept_brief": None,
        "cultural_brief": None,
        "adapted_script": None,
        # Evaluation
        "format_feedback": None,
        "cultural_feedback": None,
        "concept_feedback": None,
        "format_revision_count": 0,
        "cultural_revision_count": 0,
        "concept_revision_count": 0,
        "brand_feedback": None,
        "brand_revision_count": 0,
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
        from cw.audiences.models import Language

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
        "format_revision_count": final_state.get("format_revision_count", 0),
        "cultural_revision_count": final_state.get("cultural_revision_count", 0),
        "concept_revision_count": final_state.get("concept_revision_count", 0),
        "brand_revision_count": final_state.get("brand_revision_count", 0),
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
    from cw.audiences.models import Language

    try:
        lang = Language.objects.get(code=language_code, is_active=True)
    except Language.DoesNotExist:
        return None

    alt = lang.alternative_models.filter(is_active=True).first()
    if alt:
        logger.info(f"Alternative model for '{language_code}': {alt.model_id}")
    return alt
