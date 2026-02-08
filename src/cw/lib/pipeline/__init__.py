"""Multi-agent adaptation pipeline using LangGraph.

Public API:
    ``run_adaptation_pipeline(video_ad_unit)`` — Run the full pipeline for a VideoAdUnit.
"""

from __future__ import annotations

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def run_adaptation_pipeline(video_ad_unit):
    """Run the full multi-agent adaptation pipeline for a VideoAdUnit.

    Handles state building, graph execution, status updates, and result
    persistence.  The caller only needs to handle top-level exceptions.
    """
    from .graph import build_adaptation_graph
    from .state import build_initial_state, save_pipeline_result

    # Build target description for logging
    target_parts = []
    if video_ad_unit.region:
        target_parts.append(video_ad_unit.region.code)
    if video_ad_unit.country:
        target_parts.append(video_ad_unit.country.code)
    target_code = "-".join(target_parts) if target_parts else video_ad_unit.language.code

    logger.info(
        f"Pipeline starting for video ad unit {video_ad_unit.pk}",
        extra={"video_ad_unit_id": video_ad_unit.pk, "target": target_code},
    )

    video_ad_unit.status = "processing"
    video_ad_unit.started_at = timezone.now()
    video_ad_unit.save(update_fields=["status", "started_at"])

    initial_state = build_initial_state(video_ad_unit)
    graph = build_adaptation_graph()
    final_state = graph.invoke(initial_state)

    save_pipeline_result(video_ad_unit, final_state)

    logger.info(
        f"Pipeline completed for video ad unit {video_ad_unit.pk}: status={video_ad_unit.status}",
        extra={"video_ad_unit_id": video_ad_unit.pk, "status": video_ad_unit.status},
    )
