"""Node functions for the LangGraph adaptation pipeline.

Each node follows the signature ``(state: PipelineState) -> dict`` and returns
a partial state update.  ORM imports are at function level to avoid circular
imports and to match the pattern used in ``cw.tvspots.tasks``.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING

from cw.lib.prompts import render_prompt

if TYPE_CHECKING:
    from cw.lib.pipeline.schemas import PipelineState

logger = logging.getLogger(__name__)

MAX_FORMAT_RETRIES = 3
MAX_CULTURAL_RETRIES = 3
MAX_CONCEPT_RETRIES = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_generator(state, output_schema):
    """Return an Outlines generator for *output_schema*, handling model switches."""
    from cw.lib.pipeline.model_loader import get_model_loader

    logger.debug(
        f"Getting generator for schema: {output_schema.__name__}",
        extra={
            "job_id": state.get("job_id"),
            "model_id": state["model_id"],
            "load_in_4bit": state.get("load_in_4bit", False),
        },
    )

    loader = get_model_loader(
        model_id=state["model_id"],
        load_in_4bit=state.get("load_in_4bit", False),
    )
    return loader.get_generator(output_schema), loader


def _apply_chat_template(loader, system_message: str, user_prompt: str) -> str:
    """Format a system + user message pair using the loaded tokenizer's chat template."""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_prompt},
    ]
    return loader.tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )


def _update_job_status(job_id: int, status: str, **extra_fields):
    """Persist status and optional extra fields on the VideoAdUnit."""
    from cw.tvspots.models import VideoAdUnit

    update_fields = ["status"]
    job = VideoAdUnit.objects.get(id=job_id)
    job.status = status
    for field, value in extra_fields.items():
        setattr(job, field, value)
        update_fields.append(field)
    job.save(update_fields=update_fields)


# ---------------------------------------------------------------------------
# Concept extraction node
# ---------------------------------------------------------------------------

def concept_node(state: PipelineState) -> dict:
    """Analyse the original script and produce a ConceptBrief."""
    from cw.lib.pipeline.schemas import ConceptBrief

    logger.info("Pipeline node: concept_extraction starting", extra={"job_id": state["job_id"]})
    _update_job_status(state["job_id"], "concept_analysis")
    start = time.time()

    try:
        logger.debug("Loading model and creating generator", extra={"job_id": state["job_id"]})
        generator, loader = _get_generator(state, ConceptBrief)

        logger.debug("Rendering concept extraction prompt", extra={"job_id": state["job_id"]})
        user_prompt = render_prompt(
            "concept_extraction.j2",
            original_json=state["original_script"],
        )
        system_message = (
            "You are an expert advertising analyst. Produce ONLY valid JSON "
            "matching the requested schema — no commentary."
        )
        prompt = _apply_chat_template(loader, system_message, user_prompt)

        logger.info("Generating concept brief with LLM", extra={"job_id": state["job_id"], "prompt_length": len(prompt)})
        raw = generator(prompt, max_new_tokens=4096)
        logger.debug("LLM generation complete, validating output", extra={"job_id": state["job_id"]})

        result = ConceptBrief.model_validate(json.loads(raw) if isinstance(raw, str) else raw)
        brief_json = result.model_dump_json()

        logger.debug("Saving concept brief to database", extra={"job_id": state["job_id"]})
        _update_job_status(state["job_id"], "concept_analysis", concept_brief=json.loads(brief_json))

        elapsed = round(time.time() - start, 2)
        logger.info(f"Pipeline node: concept_extraction done ({elapsed}s)", extra={"job_id": state["job_id"]})

        return {"concept_brief": brief_json}

    except Exception as e:
        logger.error(
            f"Concept extraction failed: {e}",
            extra={"job_id": state["job_id"], "error": str(e)},
            exc_info=True,
        )
        raise


# ---------------------------------------------------------------------------
# Cultural research node
# ---------------------------------------------------------------------------

def culture_node(state: PipelineState) -> dict:
    """Produce a CulturalBrief for the target market."""
    from cw.lib.pipeline.schemas import CulturalBrief

    logger.info("Pipeline node: cultural_research starting", extra={"job_id": state["job_id"]})
    _update_job_status(state["job_id"], "cultural_analysis")
    start = time.time()

    try:
        logger.debug("Loading model and creating generator", extra={"job_id": state["job_id"]})
        generator, loader = _get_generator(state, CulturalBrief)

        logger.debug("Rendering cultural research prompt", extra={"job_id": state["job_id"], "target": state["target_market_name"]})
        user_prompt = render_prompt(
            "cultural_research.j2",
            concept_brief_json=state["concept_brief"],
            target_market_name=state["target_market_name"],
            target_market_rules=state["target_market_rules"],
            original_json=state["original_script"],
        )
        system_message = (
            "You are a cultural research specialist. Produce ONLY valid JSON "
            "matching the requested schema — no commentary."
        )
        prompt = _apply_chat_template(loader, system_message, user_prompt)

        logger.info("Generating cultural brief with LLM", extra={"job_id": state["job_id"], "prompt_length": len(prompt)})
        raw = generator(prompt, max_new_tokens=4096)
        logger.debug("LLM generation complete, validating output", extra={"job_id": state["job_id"]})

        result = CulturalBrief.model_validate(json.loads(raw) if isinstance(raw, str) else raw)
        brief_json = result.model_dump_json()

        logger.debug("Saving cultural brief to database", extra={"job_id": state["job_id"]})
        _update_job_status(state["job_id"], "cultural_analysis", cultural_brief=json.loads(brief_json))

        elapsed = round(time.time() - start, 2)
        logger.info(f"Pipeline node: cultural_research done ({elapsed}s)", extra={"job_id": state["job_id"]})

        return {"cultural_brief": brief_json}

    except Exception as e:
        logger.error(
            f"Cultural research failed: {e}",
            extra={"job_id": state["job_id"], "error": str(e)},
            exc_info=True,
        )
        raise


# ---------------------------------------------------------------------------
# Writer node
# ---------------------------------------------------------------------------

def writer_node(state: PipelineState) -> dict:
    """Generate (or revise) the adapted script."""
    from cw.lib.adaptation import AdaptationOutput

    format_count = state.get("format_revision_count", 0)
    cultural_count = state.get("cultural_revision_count", 0)
    concept_count = state.get("concept_revision_count", 0)
    total_revisions = format_count + cultural_count + concept_count
    is_revision = (
        state.get("format_feedback") is not None
        or state.get("cultural_feedback") is not None
        or state.get("concept_feedback") is not None
    )

    status = "revising" if is_revision else "writing"
    logger.info(
        f"Pipeline node: writer starting (revision={is_revision}, total_revisions={total_revisions})",
        extra={"job_id": state["job_id"]},
    )
    _update_job_status(state["job_id"], status)
    start = time.time()

    # Switch model after 2 failed revision attempts
    if total_revisions >= 2:
        from cw.lib.pipeline.state import get_alternative_model
        from cw.lib.pipeline.model_loader import get_model_loader

        alt = get_alternative_model(state.get("language_code", ""))
        if alt:
            loader = get_model_loader(state["model_id"], state.get("load_in_4bit", False))
            logger.info(f"Switching to alternative model: {alt.model_id}")
            loader.switch_model(alt.model_id, alt.load_in_4bit)
            # Update state so subsequent nodes use new model
            state_update_model = {"model_id": alt.model_id, "load_in_4bit": alt.load_in_4bit}
        else:
            state_update_model = {}
    else:
        state_update_model = {}

    generator, loader = _get_generator(state | state_update_model, AdaptationOutput)

    # Build revision feedback from whichever evaluator failed
    revision_feedback = state.get("format_feedback") or state.get("cultural_feedback") or state.get("concept_feedback") or None

    user_prompt = render_prompt(
        "adaptation.j2",
        target_market_name=state["target_market_name"],
        target_market_language=state["target_market_language"],
        target_market_rules=state["target_market_rules"],
        target_market_code=state["target_market_code"],
        original_json=state["original_script"],
        num_script_rows=state["num_script_rows"],
        creativity=0.7,
        concept_brief=state.get("concept_brief"),
        cultural_brief=state.get("cultural_brief"),
        revision_feedback=revision_feedback,
    )

    language_code = state["target_market_language"]
    system_message = (
        "You are an expert advertising creative and localization strategist. "
        "CRITICAL LANGUAGE RULE: You MUST write ALL descriptions, stage directions, "
        f"and visual_text content in ENGLISH. Only spoken dialogue (VO) and on-screen text "
        f"(supers, titles) should use {language_code}, and these MUST include "
        "an English translation in parentheses. Never write scene descriptions in any "
        "language other than English. Produce ONLY valid JSON — no commentary."
    )
    prompt = _apply_chat_template(loader, system_message, user_prompt)

    logger.info(
        f"Generating adapted script with LLM (revision={is_revision})",
        extra={"job_id": state["job_id"], "prompt_length": len(prompt), "total_revisions": total_revisions},
    )
    raw = generator(prompt, max_new_tokens=4096)
    logger.debug("LLM generation complete, validating output", extra={"job_id": state["job_id"]})

    result = AdaptationOutput.model_validate(json.loads(raw) if isinstance(raw, str) else raw)
    script_json = result.model_dump_json()

    elapsed = round(time.time() - start, 2)
    logger.info(f"Pipeline node: writer done ({elapsed}s)", extra={"job_id": state["job_id"]})

    return {
        "adapted_script": script_json,
        # Clear feedback so evaluators start fresh on the new draft
        "format_feedback": None,
        "cultural_feedback": None,
        "concept_feedback": None,
        **state_update_model,
    }


# ---------------------------------------------------------------------------
# Format / language compliance evaluation node
# ---------------------------------------------------------------------------

def format_eval_node(state: PipelineState) -> dict:
    """Evaluate format and language compliance of the adapted script."""
    from cw.lib.pipeline.schemas import EvaluationResult

    logger.info("Pipeline node: format_eval starting", extra={"job_id": state["job_id"]})
    _update_job_status(state["job_id"], "format_evaluation")
    start = time.time()

    try:
        logger.debug("Loading model and creating generator", extra={"job_id": state["job_id"]})
        generator, loader = _get_generator(state, EvaluationResult)

        logger.debug("Rendering format evaluation prompt", extra={"job_id": state["job_id"]})
        user_prompt = render_prompt(
            "eval_format.j2",
            adapted_script_json=state["adapted_script"],
            target_market_language=state["target_market_language"],
        )
        system_message = (
            "You are a localization QA specialist. Produce ONLY valid JSON "
            "matching the requested schema — no commentary."
        )
        prompt = _apply_chat_template(loader, system_message, user_prompt)

        logger.info("Evaluating format compliance with LLM", extra={"job_id": state["job_id"], "prompt_length": len(prompt)})
        raw = generator(prompt, max_new_tokens=2048)
        logger.debug("LLM evaluation complete, validating output", extra={"job_id": state["job_id"]})

        result = EvaluationResult.model_validate(json.loads(raw) if isinstance(raw, str) else raw)

        # Append to evaluation history
        from cw.tvspots.models import VideoAdUnit

        logger.debug("Updating evaluation history in database", extra={"job_id": state["job_id"]})
        job = VideoAdUnit.objects.get(id=state["job_id"])
        history = job.evaluation_history or []
        history.append({"type": "format", **result.model_dump()})
        job.evaluation_history = history
        job.save(update_fields=["evaluation_history"])

        elapsed = round(time.time() - start, 2)
        logger.info(
            f"Pipeline node: format_eval done ({elapsed}s, passed={result.passed})",
            extra={"job_id": state["job_id"], "passed": result.passed},
        )

    except Exception as e:
        logger.error(
            f"Format evaluation failed: {e}",
            extra={"job_id": state["job_id"], "error": str(e)},
            exc_info=True,
        )
        raise

    if result.passed:
        return {"format_feedback": None}
    else:
        return {
            "format_feedback": result.model_dump_json(),
            "format_revision_count": state.get("format_revision_count", 0) + 1,
        }


# ---------------------------------------------------------------------------
# Cultural evaluation node
# ---------------------------------------------------------------------------

def cultural_eval_node(state: PipelineState) -> dict:
    """Evaluate cultural compliance of the adapted script."""
    from cw.lib.pipeline.schemas import EvaluationResult

    logger.info("Pipeline node: cultural_eval starting", extra={"job_id": state["job_id"]})
    _update_job_status(state["job_id"], "cultural_evaluation")
    start = time.time()

    try:
        logger.debug("Loading model and creating generator", extra={"job_id": state["job_id"]})
        generator, loader = _get_generator(state, EvaluationResult)

        logger.debug("Rendering cultural evaluation prompt", extra={"job_id": state["job_id"]})
        user_prompt = render_prompt(
            "eval_cultural.j2",
            adapted_script_json=state["adapted_script"],
            cultural_brief_json=state["cultural_brief"],
            target_market_rules=state["target_market_rules"],
        )
        system_message = (
            "You are a cultural compliance reviewer. Produce ONLY valid JSON "
            "matching the requested schema — no commentary."
        )
        prompt = _apply_chat_template(loader, system_message, user_prompt)

        logger.info("Evaluating cultural compliance with LLM", extra={"job_id": state["job_id"], "prompt_length": len(prompt)})
        raw = generator(prompt, max_new_tokens=2048)
        logger.debug("LLM evaluation complete, validating output", extra={"job_id": state["job_id"]})

        result = EvaluationResult.model_validate(json.loads(raw) if isinstance(raw, str) else raw)

        # Append to evaluation history
        from cw.tvspots.models import VideoAdUnit

        logger.debug("Updating evaluation history in database", extra={"job_id": state["job_id"]})
        job = VideoAdUnit.objects.get(id=state["job_id"])
        history = job.evaluation_history or []
        history.append({"type": "cultural", **result.model_dump()})
        job.evaluation_history = history
        job.save(update_fields=["evaluation_history"])

        elapsed = round(time.time() - start, 2)
        logger.info(
            f"Pipeline node: cultural_eval done ({elapsed}s, passed={result.passed})",
            extra={"job_id": state["job_id"], "passed": result.passed},
        )

    except Exception as e:
        logger.error(
            f"Cultural evaluation failed: {e}",
            extra={"job_id": state["job_id"], "error": str(e)},
            exc_info=True,
        )
        raise

    if result.passed:
        return {"cultural_feedback": None}
    else:
        return {
            "cultural_feedback": result.model_dump_json(),
            "cultural_revision_count": state.get("cultural_revision_count", 0) + 1,
        }


# ---------------------------------------------------------------------------
# Concept fidelity evaluation node
# ---------------------------------------------------------------------------

def concept_eval_node(state: PipelineState) -> dict:
    """Evaluate concept fidelity of the adapted script."""
    from cw.lib.pipeline.schemas import EvaluationResult

    logger.info("Pipeline node: concept_eval starting", extra={"job_id": state["job_id"]})
    _update_job_status(state["job_id"], "concept_evaluation")
    start = time.time()

    generator, loader = _get_generator(state, EvaluationResult)

    user_prompt = render_prompt(
        "eval_concept.j2",
        adapted_script_json=state["adapted_script"],
        concept_brief_json=state["concept_brief"],
    )
    system_message = (
        "You are a brand strategy reviewer. Produce ONLY valid JSON "
        "matching the requested schema — no commentary."
    )
    prompt = _apply_chat_template(loader, system_message, user_prompt)

    raw = generator(prompt, max_new_tokens=2048)
    result = EvaluationResult.model_validate(json.loads(raw) if isinstance(raw, str) else raw)

    # Append to evaluation history
    from cw.tvspots.models import VideoAdUnit

    job = VideoAdUnit.objects.get(id=state["job_id"])
    history = job.evaluation_history or []
    history.append({"type": "concept", **result.model_dump()})
    job.evaluation_history = history
    job.save(update_fields=["evaluation_history"])

    elapsed = round(time.time() - start, 2)
    logger.info(
        f"Pipeline node: concept_eval done ({elapsed}s, passed={result.passed})",
        extra={"job_id": state["job_id"]},
    )

    if result.passed:
        return {"concept_feedback": None}
    else:
        return {
            "concept_feedback": result.model_dump_json(),
            "concept_revision_count": state.get("concept_revision_count", 0) + 1,
        }
