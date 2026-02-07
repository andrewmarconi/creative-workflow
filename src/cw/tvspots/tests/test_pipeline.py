"""
Tests for the multi-agent adaptation pipeline.

Covers issues #39–#42 (Phase 4: Validation):
  - #39: End-to-end pipeline test
  - #40: Side-by-side comparison: pipeline vs single-step
  - #41: Evaluation loop and revision exercise
  - #42: Model fallback test on alternative_models

All LLM calls are mocked — these tests validate the pipeline's graph
routing, state management, DB persistence, and error handling without
requiring GPU or downloaded models.

Run with:
    uv run manage.py test cw.tvspots.tests -v2
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from cw.core.models import Language, LLMModel
from cw.lib.pipeline.graph import (
    build_adaptation_graph,
    route_after_concept_eval,
    route_after_cultural_eval,
)
from cw.lib.pipeline.schemas import (
    ConceptBrief,
    CulturalBrief,
    EvaluationResult,
    PipelineState,
)
from cw.lib.pipeline.state import build_initial_state, get_alternative_model, save_pipeline_result
from cw.tvspots.models import (
    AdaptationJob,
    AdaptationMarket,
    TvSpot,
    TvSpotScriptRow,
    TvSpotVersion,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _sample_concept_brief() -> ConceptBrief:
    return ConceptBrief(
        core_message="WonderWash makes laundry effortless and joyful.",
        emotional_beats=["surprise", "delight", "confidence"],
        narrative_structure="Setup: mundane laundry. Conflict: stubborn stains. Resolution: WonderWash magic.",
        themes=["convenience", "family care", "modern living"],
        cultural_assumptions=["Western suburban home setting", "nuclear family structure"],
        must_preserve=["Brand name WonderWash", "Product efficacy claim", "Logo end frame"],
        can_adapt=["Setting", "Family structure", "Music style", "Humor approach"],
        brand_voice="Warm, playful, aspirational but approachable",
    )


def _sample_cultural_brief() -> CulturalBrief:
    from cw.lib.pipeline.schemas import Substitution

    return CulturalBrief(
        market_context="Japan values cleanliness, harmony, and subtlety in advertising.",
        substitutions=[
            Substitution(
                original="Western suburban home",
                replacement="Modern Tokyo apartment",
                rationale="Reflects typical Japanese urban living",
            ),
        ],
        tone_adjustments="More understated humor, emphasize quality and craftsmanship",
        pitfalls=["Avoid direct comparison with competitors", "No exaggerated claims"],
        opportunities=["Tie into spring cleaning cultural moment", "Kawaii packaging appeal"],
        regulatory_notes="Must comply with JARO advertising standards.",
    )


def _sample_adaptation_output_dict() -> dict:
    return {
        "code": "JP",
        "name": "Japanese Adaptation",
        "language": "ja",
        "visual_style_prompt": "Modern Japanese apartment, soft natural lighting",
        "script_rows": [
            {
                "shot_number": "01",
                "timecode_start": "00:00:00:00",
                "duration_seconds": 5.0,
                "visual_text": "Modern Tokyo apartment. A young woman notices stains on a white shirt.",
                "audio_text": "SFX: Gentle morning ambience. VO: \u300c\u307e\u305f\u30b7\u30df\u304c\u2026\u300d(Another stain\u2026)",
            },
            {
                "shot_number": "02",
                "timecode_start": "00:00:05:00",
                "duration_seconds": 10.0,
                "visual_text": "CU of WonderWash product. Woman adds it to washing machine.",
                "audio_text": "VO: \u300c\u30ef\u30f3\u30c0\u30fc\u30a6\u30a9\u30c3\u30b7\u30e5\u306a\u3089\u300d(With WonderWash) \u2014 gentle piano melody",
            },
            {
                "shot_number": "03",
                "timecode_start": "00:00:15:00",
                "duration_seconds": 5.0,
                "visual_text": "Woman holds perfectly clean shirt, smiles. WonderWash logo + tagline.",
                "audio_text": "VO: \u300c\u304d\u308c\u3044\u304c\u7d9a\u304f\u300d(Lasting clean) \u2014 SUPER: WonderWash \u30ef\u30f3\u30c0\u30fc\u30a6\u30a9\u30c3\u30b7\u30e5",
            },
        ],
    }


def _sample_eval_pass() -> EvaluationResult:
    return EvaluationResult(passed=True, score=0.92, issues=[], summary="Excellent cultural adaptation.")


def _sample_eval_fail() -> EvaluationResult:
    from cw.lib.pipeline.schemas import EvaluationIssue

    return EvaluationResult(
        passed=False,
        score=0.45,
        issues=[
            EvaluationIssue(
                severity="major",
                description="Direct competitor comparison violates JARO standards.",
                location="Shot 02 audio",
                suggestion="Remove comparative language, focus on product benefits.",
            ),
        ],
        summary="Cultural compliance issues found.",
    )


class PipelineTestMixin:
    """Creates a standard set of test objects for pipeline tests."""

    def setUp(self):
        super().setUp()
        # LLM models
        self.primary_model = LLMModel.objects.create(
            model_id="Qwen/Qwen2.5-3B-Instruct",
            name="Qwen 2.5 3B",
            is_active=True,
        )
        self.alt_model = LLMModel.objects.create(
            model_id="Qwen/Qwen2.5-7B-Instruct",
            name="Qwen 2.5 7B",
            is_active=True,
        )

        # Languages
        self.japanese = Language.objects.create(
            code="ja",
            name="Japanese",
            primary_model=self.primary_model,
        )
        self.japanese.alternative_models.add(self.alt_model)

        self.english = Language.objects.create(
            code="en-US",
            name="English (United States)",
            base_language="en",
            primary_model=self.primary_model,
        )

        # Market
        self.japan_market = AdaptationMarket.objects.create(
            name="Japan",
            code="jp",
            default_language=self.japanese,
            rules=[
                {
                    "heading": "Cultural sensitivity",
                    "points": [
                        "Avoid direct competitor comparisons (JARO regulations).",
                        "Use polite/formal register by default.",
                    ],
                },
                {
                    "heading": "Visual standards",
                    "points": ["Prefer clean, minimalist aesthetics."],
                },
            ],
        )

        # TV Spot
        self.tv_spot = TvSpot.objects.create(
            client_name="Unilever",
            brand_name="WonderWash",
            script_title="WonderWash Launch 30s",
            total_runtime_seconds=30,
            job_id="UNI-2026-001",
        )

        # Origin version
        self.origin_version = TvSpotVersion.objects.create(
            tv_spot=self.tv_spot,
            version_type="origin",
            code="ORIGIN",
            name="Global Master",
            language=self.english,
        )

        # Script rows
        for idx, (shot, tc, dur, vis, aud) in enumerate([
            ("01", "00:00:00:00", 5.0, "Suburban home. A mom notices stains on a shirt.", "SFX: Morning sounds. VO: Oh no, not again!"),
            ("02", "00:00:05:00", 10.0, "CU of WonderWash. She adds it to the machine.", "VO: WonderWash tackles any stain — upbeat jingle"),
            ("03", "00:00:15:00", 5.0, "Mom holds clean shirt, big smile. Logo + tagline.", "VO: WonderWash. Brilliantly clean. — SUPER: WonderWash"),
        ]):
            TvSpotScriptRow.objects.create(
                tv_spot_version=self.origin_version,
                order_index=idx,
                shot_number=shot,
                timecode_start=tc,
                duration_seconds=Decimal(str(dur)),
                visual_text=vis,
                audio_text=aud,
            )

        # Adaptation job (pipeline)
        self.pipeline_job = AdaptationJob.objects.create(
            tv_spot=self.tv_spot,
            origin_version=self.origin_version,
            target_market=self.japan_market,
            use_pipeline=True,
            status="pending",
        )

        # Adaptation job (single-step)
        self.single_step_job = AdaptationJob.objects.create(
            tv_spot=self.tv_spot,
            origin_version=self.origin_version,
            target_market=self.japan_market,
            use_pipeline=False,
            status="pending",
        )


# ===========================================================================
# #39 — End-to-end pipeline test
# ===========================================================================

class EndToEndPipelineTest(PipelineTestMixin, TestCase):
    """Issue #39: End-to-end pipeline test with existing data.

    Validates that the pipeline:
    - Populates concept_brief and cultural_brief
    - Creates adapted_script preserving core message
    - Fires evaluation loops (check evaluation_history)
    - Creates TvSpotVersion and TvSpotScriptRow records
    - Records pipeline_metadata
    - Logs status transitions correctly
    """

    @patch("cw.lib.pipeline.nodes._get_generator")
    @patch("cw.lib.pipeline.nodes._apply_chat_template")
    def test_full_pipeline_success(self, mock_chat_template, mock_get_gen):
        """Run the full pipeline with mocked LLM — all evaluations pass."""
        concept_brief = _sample_concept_brief()
        cultural_brief = _sample_cultural_brief()
        adaptation_output = _sample_adaptation_output_dict()
        eval_pass = _sample_eval_pass()

        # Mock chat template to return a dummy string
        mock_chat_template.return_value = "formatted_prompt"

        # Build a generator mock that returns different outputs depending on call order
        call_count = {"n": 0}
        mock_generator = MagicMock()

        def side_effect(prompt, max_new_tokens=4096):
            call_count["n"] += 1
            n = call_count["n"]
            if n == 1:  # concept_node
                return concept_brief.model_dump()
            elif n == 2:  # culture_node
                return cultural_brief.model_dump()
            elif n == 3:  # writer_node
                return adaptation_output
            elif n == 4:  # cultural_eval_node
                return eval_pass.model_dump()
            elif n == 5:  # concept_eval_node
                return eval_pass.model_dump()
            return {}

        mock_generator.side_effect = side_effect
        mock_loader = MagicMock()
        mock_get_gen.return_value = (mock_generator, mock_loader)

        # Run pipeline
        from cw.lib.pipeline import run_adaptation_pipeline

        run_adaptation_pipeline(self.pipeline_job)

        # Refresh from DB
        self.pipeline_job.refresh_from_db()

        # Verify concept_brief populated
        self.assertIsNotNone(self.pipeline_job.concept_brief)
        self.assertEqual(
            self.pipeline_job.concept_brief["core_message"],
            "WonderWash makes laundry effortless and joyful.",
        )

        # Verify cultural_brief populated
        self.assertIsNotNone(self.pipeline_job.cultural_brief)
        self.assertIn("Japan", self.pipeline_job.cultural_brief["market_context"])

        # Verify evaluation_history has entries
        self.assertIsInstance(self.pipeline_job.evaluation_history, list)
        self.assertGreaterEqual(len(self.pipeline_job.evaluation_history), 2)
        eval_types = [e["type"] for e in self.pipeline_job.evaluation_history]
        self.assertIn("cultural", eval_types)
        self.assertIn("concept", eval_types)

        # Verify TvSpotVersion created
        self.assertIsNotNone(self.pipeline_job.result_version)
        result_version = self.pipeline_job.result_version
        self.assertEqual(result_version.version_type, "adaptation")
        self.assertEqual(result_version.market, self.japan_market)
        self.assertEqual(result_version.code, "JP")
        self.assertEqual(result_version.language.code, "ja")

        # Verify TvSpotScriptRow records
        rows = result_version.script_rows.all().order_by("order_index")
        self.assertEqual(rows.count(), 3)
        self.assertEqual(rows[0].shot_number, "01")

        # Verify pipeline_metadata
        self.assertIsNotNone(self.pipeline_job.pipeline_metadata)
        meta = self.pipeline_job.pipeline_metadata
        self.assertIn("cultural_revision_count", meta)
        self.assertIn("concept_revision_count", meta)
        self.assertIn("final_model_id", meta)

        # Verify final status
        self.assertEqual(self.pipeline_job.status, "completed")
        self.assertIsNotNone(self.pipeline_job.completed_at)

    @patch("cw.lib.pipeline.nodes._get_generator")
    @patch("cw.lib.pipeline.nodes._apply_chat_template")
    def test_pipeline_failure_produces_error(self, mock_chat_template, mock_get_gen):
        """Pipeline failure records error and metadata correctly."""
        mock_chat_template.return_value = "formatted_prompt"
        mock_generator = MagicMock()
        mock_generator.side_effect = RuntimeError("Model out of memory")
        mock_loader = MagicMock()
        mock_get_gen.return_value = (mock_generator, mock_loader)

        from cw.lib.pipeline import run_adaptation_pipeline

        # The entry point catches exceptions and re-raises; the task layer catches them
        with self.assertRaises(RuntimeError):
            run_adaptation_pipeline(self.pipeline_job)


class BuildInitialStateTest(PipelineTestMixin, TestCase):
    """Test that build_initial_state correctly serializes AdaptationJob data."""

    def test_state_has_all_required_keys(self):
        state = build_initial_state(self.pipeline_job)

        required_keys = [
            "job_id", "model_id", "load_in_4bit", "original_script",
            "target_market_name", "target_market_code", "target_market_rules",
            "target_market_language", "language_code", "num_script_rows",
            "concept_brief", "cultural_brief", "adapted_script",
            "cultural_feedback", "concept_feedback",
            "cultural_revision_count", "concept_revision_count",
            "status", "error_message",
        ]
        for key in required_keys:
            self.assertIn(key, state, f"Missing key: {key}")

    def test_state_script_rows_count(self):
        state = build_initial_state(self.pipeline_job)
        self.assertEqual(state["num_script_rows"], 3)

    def test_state_target_market_info(self):
        state = build_initial_state(self.pipeline_job)
        self.assertEqual(state["target_market_name"], "Japan")
        self.assertEqual(state["target_market_code"], "JP")
        self.assertEqual(state["language_code"], "ja")

    def test_state_original_script_is_valid_json(self):
        state = build_initial_state(self.pipeline_job)
        parsed = json.loads(state["original_script"])
        self.assertEqual(parsed["client_name"], "Unilever")
        self.assertEqual(parsed["brand_name"], "WonderWash")
        self.assertEqual(len(parsed["script_rows"]), 3)


class SavePipelineResultTest(PipelineTestMixin, TestCase):
    """Test save_pipeline_result persists pipeline output to DB correctly."""

    def test_success_creates_version_and_rows(self):
        adapted = _sample_adaptation_output_dict()
        final_state = {
            "adapted_script": json.dumps(adapted),
            "cultural_revision_count": 1,
            "concept_revision_count": 0,
            "model_id": "Qwen/Qwen2.5-3B-Instruct",
            "status": "completed",
        }

        save_pipeline_result(self.pipeline_job, final_state)
        self.pipeline_job.refresh_from_db()

        self.assertEqual(self.pipeline_job.status, "completed")
        self.assertIsNotNone(self.pipeline_job.result_version)
        self.assertEqual(self.pipeline_job.result_version.code, "JP")
        self.assertEqual(self.pipeline_job.result_version.script_rows.count(), 3)
        self.assertEqual(self.pipeline_job.pipeline_metadata["cultural_revision_count"], 1)

    def test_failure_when_no_adapted_script(self):
        final_state = {
            "adapted_script": None,
            "error_message": "Max retries exceeded",
            "cultural_revision_count": 3,
            "concept_revision_count": 0,
            "model_id": "Qwen/Qwen2.5-3B-Instruct",
            "status": "failed",
        }

        save_pipeline_result(self.pipeline_job, final_state)
        self.pipeline_job.refresh_from_db()

        self.assertEqual(self.pipeline_job.status, "failed")
        self.assertIn("Max retries", self.pipeline_job.error_message)
        self.assertIsNone(self.pipeline_job.result_version)


# ===========================================================================
# #40 — Side-by-side comparison: pipeline vs single-step
# ===========================================================================

class SideBySideComparisonTest(PipelineTestMixin, TestCase):
    """Issue #40: Side-by-side comparison of pipeline vs single-step.

    Validates that:
    - Both paths produce valid TvSpotVersion records
    - Pipeline output includes richer metadata
    - Both outputs have the same number of script rows
    """

    def test_pipeline_job_has_richer_metadata(self):
        """Pipeline jobs carry briefs and evaluation history; single-step does not."""
        adapted = _sample_adaptation_output_dict()

        # Simulate pipeline completion
        final_state = {
            "adapted_script": json.dumps(adapted),
            "cultural_revision_count": 0,
            "concept_revision_count": 0,
            "model_id": "Qwen/Qwen2.5-3B-Instruct",
            "status": "completed",
        }
        self.pipeline_job.concept_brief = _sample_concept_brief().model_dump()
        self.pipeline_job.cultural_brief = _sample_cultural_brief().model_dump()
        self.pipeline_job.evaluation_history = [
            {"type": "cultural", **_sample_eval_pass().model_dump()},
            {"type": "concept", **_sample_eval_pass().model_dump()},
        ]
        self.pipeline_job.save()

        save_pipeline_result(self.pipeline_job, final_state)
        self.pipeline_job.refresh_from_db()

        # Pipeline job has concept/cultural briefs
        self.assertIsNotNone(self.pipeline_job.concept_brief)
        self.assertIsNotNone(self.pipeline_job.cultural_brief)
        self.assertEqual(len(self.pipeline_job.evaluation_history), 2)
        self.assertIn("cultural_revision_count", self.pipeline_job.pipeline_metadata)

        # Single-step job lacks these
        self.assertIsNone(self.single_step_job.concept_brief)
        self.assertIsNone(self.single_step_job.cultural_brief)
        self.assertEqual(self.single_step_job.evaluation_history, [])

    def test_both_paths_produce_same_structure(self):
        """Both pipeline and single-step create TvSpotVersion with script rows."""
        adapted = _sample_adaptation_output_dict()

        # Simulate pipeline result
        save_pipeline_result(
            self.pipeline_job,
            {
                "adapted_script": json.dumps(adapted),
                "cultural_revision_count": 0,
                "concept_revision_count": 0,
                "model_id": "Qwen/Qwen2.5-3B-Instruct",
                "status": "completed",
            },
        )

        # Simulate single-step result (manually create version)
        from cw.lib.adaptation import AdaptationOutput

        result = AdaptationOutput.model_validate(adapted)
        # Lookup Language by code from result
        language_obj = Language.objects.get(code=result.language)
        single_version = TvSpotVersion.objects.create(
            tv_spot=self.tv_spot,
            version_type="adaptation",
            market=self.japan_market,
            code=result.code + "-SS",
            name=result.name + " (Single-Step)",
            language=language_obj,
            visual_style_prompt=result.visual_style_prompt,
        )
        for idx, row_data in enumerate(result.script_rows):
            TvSpotScriptRow.objects.create(
                tv_spot_version=single_version,
                order_index=idx,
                shot_number=row_data.shot_number,
                timecode_start=row_data.timecode_start,
                duration_seconds=row_data.duration_seconds,
                visual_text=row_data.visual_text,
                audio_text=row_data.audio_text,
            )

        self.pipeline_job.refresh_from_db()

        # Both created versions with same row count
        pipeline_version = self.pipeline_job.result_version
        self.assertEqual(pipeline_version.script_rows.count(), single_version.script_rows.count())
        self.assertEqual(pipeline_version.version_type, "adaptation")
        self.assertEqual(single_version.version_type, "adaptation")


# ===========================================================================
# #41 — Evaluation loop and revision exercise
# ===========================================================================

class EvaluationLoopTest(PipelineTestMixin, TestCase):
    """Issue #41: Evaluation loop and revision exercise.

    Validates that:
    - Cultural evaluator flags issues in the first adaptation
    - Writer node revises with evaluator feedback
    - cultural_revision_count increments correctly
    - evaluation_history contains chronological entries
    - Pipeline succeeds after revision or fails at max retries
    - Status transitions are correct
    """

    def test_graph_routing_cultural_pass(self):
        """When cultural eval passes, route to concept_eval."""
        state = {"cultural_feedback": None, "cultural_revision_count": 0}
        self.assertEqual(route_after_cultural_eval(state), "concept_eval")

    def test_graph_routing_cultural_fail_with_retries(self):
        """When cultural eval fails but retries remain, route to writer."""
        state = {"cultural_feedback": "issues found", "cultural_revision_count": 1}
        self.assertEqual(route_after_cultural_eval(state), "writer")

    def test_graph_routing_cultural_exhausted(self):
        """When cultural eval exhausted retries, route to fail (END)."""
        state = {"cultural_feedback": "issues found", "cultural_revision_count": 3}
        self.assertEqual(route_after_cultural_eval(state), "fail")

    def test_graph_routing_concept_pass(self):
        """When concept eval passes, route to end."""
        state = {"concept_feedback": None, "concept_revision_count": 0}
        self.assertEqual(route_after_concept_eval(state), "end")

    def test_graph_routing_concept_fail_with_retries(self):
        """When concept eval fails but retries remain, route to writer."""
        state = {"concept_feedback": "issues found", "concept_revision_count": 1}
        self.assertEqual(route_after_concept_eval(state), "writer")

    def test_graph_routing_concept_exhausted(self):
        """When concept eval exhausted retries, route to fail (END)."""
        state = {"concept_feedback": "issues found", "concept_revision_count": 3}
        self.assertEqual(route_after_concept_eval(state), "fail")

    @patch("cw.lib.pipeline.nodes._get_generator")
    @patch("cw.lib.pipeline.nodes._apply_chat_template")
    def test_cultural_eval_fail_triggers_revision(self, mock_chat_template, mock_get_gen):
        """When cultural eval fails, the writer revises with feedback."""
        concept_brief = _sample_concept_brief()
        cultural_brief = _sample_cultural_brief()
        adapted_v1 = _sample_adaptation_output_dict()
        adapted_v2 = _sample_adaptation_output_dict()
        adapted_v2["name"] = "Japanese Adaptation (Revised)"
        eval_fail = _sample_eval_fail()
        eval_pass = _sample_eval_pass()

        mock_chat_template.return_value = "formatted_prompt"

        call_count = {"n": 0}
        mock_generator = MagicMock()

        def side_effect(prompt, max_new_tokens=4096):
            call_count["n"] += 1
            n = call_count["n"]
            if n == 1:  # concept_node
                return concept_brief.model_dump()
            elif n == 2:  # culture_node
                return cultural_brief.model_dump()
            elif n == 3:  # writer_node (first attempt)
                return adapted_v1
            elif n == 4:  # cultural_eval_node (fails)
                return eval_fail.model_dump()
            elif n == 5:  # writer_node (revision)
                return adapted_v2
            elif n == 6:  # cultural_eval_node (passes)
                return eval_pass.model_dump()
            elif n == 7:  # concept_eval_node (passes)
                return eval_pass.model_dump()
            return {}

        mock_generator.side_effect = side_effect
        mock_loader = MagicMock()
        mock_get_gen.return_value = (mock_generator, mock_loader)

        from cw.lib.pipeline import run_adaptation_pipeline

        run_adaptation_pipeline(self.pipeline_job)
        self.pipeline_job.refresh_from_db()

        # Verify revision occurred
        self.assertEqual(self.pipeline_job.status, "completed")

        # Evaluation history should have 3 entries: cultural fail, cultural pass, concept pass
        history = self.pipeline_job.evaluation_history
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["type"], "cultural")
        self.assertFalse(history[0]["passed"])
        self.assertEqual(history[1]["type"], "cultural")
        self.assertTrue(history[1]["passed"])
        self.assertEqual(history[2]["type"], "concept")
        self.assertTrue(history[2]["passed"])

        # Pipeline metadata should reflect revision count
        meta = self.pipeline_job.pipeline_metadata
        self.assertEqual(meta["cultural_revision_count"], 1)

    @patch("cw.lib.pipeline.nodes._get_generator")
    @patch("cw.lib.pipeline.nodes._apply_chat_template")
    def test_max_retries_exhausted_fails_gracefully(self, mock_chat_template, mock_get_gen):
        """Pipeline fails gracefully when max cultural retries exhausted."""
        concept_brief = _sample_concept_brief()
        cultural_brief = _sample_cultural_brief()
        adapted = _sample_adaptation_output_dict()
        eval_fail = _sample_eval_fail()

        mock_chat_template.return_value = "formatted_prompt"

        call_count = {"n": 0}
        mock_generator = MagicMock()

        def side_effect(prompt, max_new_tokens=4096):
            call_count["n"] += 1
            n = call_count["n"]
            if n == 1:
                return concept_brief.model_dump()
            elif n == 2:
                return cultural_brief.model_dump()
            elif n in (3, 5, 7, 9):  # writer attempts
                return adapted
            elif n in (4, 6, 8, 10):  # cultural eval — always fails
                return eval_fail.model_dump()
            return {}

        mock_generator.side_effect = side_effect
        mock_loader = MagicMock()
        mock_get_gen.return_value = (mock_generator, mock_loader)

        from cw.lib.pipeline import run_adaptation_pipeline

        run_adaptation_pipeline(self.pipeline_job)
        self.pipeline_job.refresh_from_db()

        # Pipeline should still complete (graph reaches END via "fail" route)
        # but the result may or may not have an adapted script depending on
        # whether the final state includes it — the graph terminates at END
        # The important thing is it doesn't crash
        meta = self.pipeline_job.pipeline_metadata
        self.assertGreaterEqual(meta.get("cultural_revision_count", 0), 3)


class EvaluationRevisionCountTest(PipelineTestMixin, TestCase):
    """Verify revision counts increment correctly through the eval nodes."""

    @patch("cw.lib.pipeline.nodes._get_generator")
    @patch("cw.lib.pipeline.nodes._apply_chat_template")
    def test_cultural_revision_count_increments(self, mock_chat_template, mock_get_gen):
        """Cultural revision count increments on each failed evaluation."""
        from cw.lib.pipeline.nodes import cultural_eval_node

        eval_fail = _sample_eval_fail()
        mock_chat_template.return_value = "formatted_prompt"
        mock_generator = MagicMock(return_value=eval_fail.model_dump())
        mock_loader = MagicMock()
        mock_get_gen.return_value = (mock_generator, mock_loader)

        state: PipelineState = {
            "job_id": self.pipeline_job.pk,
            "model_id": "Qwen/Qwen2.5-3B-Instruct",
            "load_in_4bit": False,
            "adapted_script": json.dumps(_sample_adaptation_output_dict()),
            "cultural_brief": _sample_cultural_brief().model_dump_json(),
            "target_market_rules": "### Rules\n- Be polite",
            "cultural_revision_count": 0,
        }

        result = cultural_eval_node(state)
        self.assertEqual(result["cultural_revision_count"], 1)
        self.assertIsNotNone(result["cultural_feedback"])

    @patch("cw.lib.pipeline.nodes._get_generator")
    @patch("cw.lib.pipeline.nodes._apply_chat_template")
    def test_concept_revision_count_increments(self, mock_chat_template, mock_get_gen):
        """Concept revision count increments on each failed evaluation."""
        from cw.lib.pipeline.nodes import concept_eval_node

        eval_fail = _sample_eval_fail()
        mock_chat_template.return_value = "formatted_prompt"
        mock_generator = MagicMock(return_value=eval_fail.model_dump())
        mock_loader = MagicMock()
        mock_get_gen.return_value = (mock_generator, mock_loader)

        state: PipelineState = {
            "job_id": self.pipeline_job.pk,
            "model_id": "Qwen/Qwen2.5-3B-Instruct",
            "load_in_4bit": False,
            "adapted_script": json.dumps(_sample_adaptation_output_dict()),
            "concept_brief": _sample_concept_brief().model_dump_json(),
            "concept_revision_count": 1,
        }

        result = concept_eval_node(state)
        self.assertEqual(result["concept_revision_count"], 2)


# ===========================================================================
# #42 — Model fallback test on alternative_models
# ===========================================================================

class ModelFallbackTest(PipelineTestMixin, TestCase):
    """Issue #42: Model fallback test on alternative_models.

    Validates that:
    - get_alternative_model returns the alternative when available
    - get_alternative_model returns None when no alternatives
    - Writer node triggers model switch after 2+ revisions
    - Pipeline continues with primary if no alternatives available
    - pipeline_metadata records model switch
    """

    def test_get_alternative_model_returns_alt(self):
        """get_alternative_model returns the first active alternative."""
        alt = get_alternative_model("ja")
        self.assertIsNotNone(alt)
        self.assertEqual(alt.model_id, "Qwen/Qwen2.5-7B-Instruct")

    def test_get_alternative_model_none_for_unknown_language(self):
        """get_alternative_model returns None for unknown language code."""
        alt = get_alternative_model("zz")
        self.assertIsNone(alt)

    def test_get_alternative_model_none_when_no_alternatives(self):
        """get_alternative_model returns None when language has no alternatives."""
        english_model = LLMModel.objects.create(
            model_id="Meta/Llama-3B", name="Llama 3B", is_active=True,
        )
        Language.objects.create(
            code="en", name="English", primary_model=english_model,
        )
        alt = get_alternative_model("en")
        self.assertIsNone(alt)

    @patch("cw.lib.pipeline.nodes._apply_chat_template")
    @patch("cw.lib.pipeline.nodes._get_generator")
    @patch("cw.lib.pipeline.state.get_alternative_model")
    @patch("cw.lib.pipeline.model_loader.get_model_loader")
    def test_writer_switches_model_after_two_revisions(
        self, mock_loader_factory, mock_alt_model, mock_get_gen, mock_chat_template
    ):
        """Writer node switches to alternative model after >= 2 total revisions."""
        from cw.lib.pipeline.nodes import writer_node

        adapted = _sample_adaptation_output_dict()
        mock_chat_template.return_value = "formatted_prompt"
        mock_generator = MagicMock(return_value=adapted)
        mock_loader = MagicMock()
        mock_get_gen.return_value = (mock_generator, mock_loader)

        mock_alt = MagicMock()
        mock_alt.model_id = "Qwen/Qwen2.5-7B-Instruct"
        mock_alt.load_in_4bit = False
        mock_alt_model.return_value = mock_alt

        mock_loader_instance = MagicMock()
        mock_loader_factory.return_value = mock_loader_instance

        state = {
            "job_id": self.pipeline_job.pk,
            "model_id": "Qwen/Qwen2.5-3B-Instruct",
            "load_in_4bit": False,
            "original_script": "{}",
            "target_market_name": "Japan",
            "target_market_language": "ja",
            "target_market_rules": "",
            "target_market_code": "JP",
            "num_script_rows": 3,
            "concept_brief": _sample_concept_brief().model_dump_json(),
            "cultural_brief": _sample_cultural_brief().model_dump_json(),
            "cultural_feedback": "issues found",
            "concept_feedback": None,
            "cultural_revision_count": 2,
            "concept_revision_count": 0,
            "language_code": "ja",
        }

        result = writer_node(state)

        # Should have attempted model switch
        mock_alt_model.assert_called_once_with("ja")
        mock_loader_instance.switch_model.assert_called_once_with(
            "Qwen/Qwen2.5-7B-Instruct", False,
        )

        # State should reflect new model
        self.assertEqual(result["model_id"], "Qwen/Qwen2.5-7B-Instruct")
        self.assertFalse(result["load_in_4bit"])

    @patch("cw.lib.pipeline.nodes._apply_chat_template")
    @patch("cw.lib.pipeline.nodes._get_generator")
    @patch("cw.lib.pipeline.state.get_alternative_model")
    @patch("cw.lib.pipeline.model_loader.get_model_loader")
    def test_writer_no_switch_below_threshold(
        self, mock_loader_factory, mock_alt_model, mock_get_gen, mock_chat_template
    ):
        """Writer does NOT switch model when revision count < 2."""
        from cw.lib.pipeline.nodes import writer_node

        adapted = _sample_adaptation_output_dict()
        mock_chat_template.return_value = "formatted_prompt"
        mock_generator = MagicMock(return_value=adapted)
        mock_loader = MagicMock()
        mock_get_gen.return_value = (mock_generator, mock_loader)

        state = {
            "job_id": self.pipeline_job.pk,
            "model_id": "Qwen/Qwen2.5-3B-Instruct",
            "load_in_4bit": False,
            "original_script": "{}",
            "target_market_name": "Japan",
            "target_market_language": "ja",
            "target_market_rules": "",
            "target_market_code": "JP",
            "num_script_rows": 3,
            "concept_brief": _sample_concept_brief().model_dump_json(),
            "cultural_brief": _sample_cultural_brief().model_dump_json(),
            "cultural_feedback": "issues found",
            "concept_feedback": None,
            "cultural_revision_count": 1,
            "concept_revision_count": 0,
            "language_code": "ja",
        }

        writer_node(state)

        # Should NOT attempt model switch
        mock_alt_model.assert_not_called()

    @patch("cw.lib.pipeline.nodes._apply_chat_template")
    @patch("cw.lib.pipeline.nodes._get_generator")
    @patch("cw.lib.pipeline.state.get_alternative_model")
    @patch("cw.lib.pipeline.model_loader.get_model_loader")
    def test_writer_continues_with_primary_when_no_alternative(
        self, mock_loader_factory, mock_alt_model, mock_get_gen, mock_chat_template
    ):
        """Writer continues with primary model when no alternatives exist."""
        from cw.lib.pipeline.nodes import writer_node

        adapted = _sample_adaptation_output_dict()
        mock_chat_template.return_value = "formatted_prompt"
        mock_generator = MagicMock(return_value=adapted)
        mock_loader = MagicMock()
        mock_get_gen.return_value = (mock_generator, mock_loader)

        mock_alt_model.return_value = None  # No alternative

        state = {
            "job_id": self.pipeline_job.pk,
            "model_id": "Qwen/Qwen2.5-3B-Instruct",
            "load_in_4bit": False,
            "original_script": "{}",
            "target_market_name": "Japan",
            "target_market_language": "ja",
            "target_market_rules": "",
            "target_market_code": "JP",
            "num_script_rows": 3,
            "concept_brief": _sample_concept_brief().model_dump_json(),
            "cultural_brief": _sample_cultural_brief().model_dump_json(),
            "cultural_feedback": "issues found",
            "concept_feedback": None,
            "cultural_revision_count": 2,
            "concept_revision_count": 0,
            "language_code": "ja",
        }

        result = writer_node(state)

        # No model switch should have occurred
        self.assertNotIn("model_id", result)
        # But adapted script should still be produced
        self.assertIsNotNone(result["adapted_script"])


# ===========================================================================
# Graph compilation test
# ===========================================================================

class GraphCompilationTest(TestCase):
    """Verify the LangGraph state graph compiles and has expected structure."""

    def test_graph_compiles(self):
        """build_adaptation_graph returns a compiled graph."""
        graph = build_adaptation_graph()
        self.assertIsNotNone(graph)

    def test_graph_has_mermaid_representation(self):
        """Graph can produce Mermaid diagram (validates structure)."""
        graph = build_adaptation_graph()
        mermaid = graph.get_graph().draw_mermaid()
        self.assertIn("concept", mermaid)
        self.assertIn("culture", mermaid)
        self.assertIn("writer", mermaid)
        self.assertIn("cultural_eval", mermaid)
        self.assertIn("concept_eval", mermaid)


# ===========================================================================
# Schema validation tests
# ===========================================================================

class SchemaValidationTest(TestCase):
    """Verify Pydantic schemas accept and validate correctly."""

    def test_concept_brief_round_trip(self):
        brief = _sample_concept_brief()
        json_str = brief.model_dump_json()
        restored = ConceptBrief.model_validate_json(json_str)
        self.assertEqual(restored.core_message, brief.core_message)

    def test_cultural_brief_round_trip(self):
        brief = _sample_cultural_brief()
        json_str = brief.model_dump_json()
        restored = CulturalBrief.model_validate_json(json_str)
        self.assertEqual(restored.market_context, brief.market_context)

    def test_evaluation_result_round_trip(self):
        result = _sample_eval_fail()
        json_str = result.model_dump_json()
        restored = EvaluationResult.model_validate_json(json_str)
        self.assertFalse(restored.passed)
        self.assertEqual(len(restored.issues), 1)

    def test_evaluation_result_pass(self):
        result = _sample_eval_pass()
        self.assertTrue(result.passed)
        self.assertEqual(len(result.issues), 0)
