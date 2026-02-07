"""Multi-agent adaptation pipeline using LangGraph.

Public API:
    ``run_adaptation_pipeline(job)`` — Run the full pipeline for an AdaptationJob.
"""

from __future__ import annotations

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def run_adaptation_pipeline(job):
    """Run the full multi-agent adaptation pipeline for an AdaptationJob.

    Handles state building, graph execution, status updates, and result
    persistence.  The caller only needs to handle top-level exceptions.
    """
    from .graph import build_adaptation_graph
    from .state import build_initial_state, save_pipeline_result

    # Build target description for logging
    target_parts = []
    if job.region:
        target_parts.append(job.region.code)
    if job.country:
        target_parts.append(job.country.code)
    target_code = "-".join(target_parts) if target_parts else job.language.code

    logger.info(
        f"Pipeline starting for job {job.pk}",
        extra={"job_id": job.pk, "target": target_code},
    )

    job.status = "processing"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    initial_state = build_initial_state(job)
    graph = build_adaptation_graph()
    final_state = graph.invoke(initial_state)

    save_pipeline_result(job, final_state)

    logger.info(
        f"Pipeline completed for job {job.pk}: status={job.status}",
        extra={"job_id": job.pk, "status": job.status},
    )
