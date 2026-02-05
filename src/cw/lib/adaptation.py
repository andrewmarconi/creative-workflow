"""
TV Spot cultural adaptation using LLM with structured output.

This module uses local Qwen models with the Outlines library to generate
culturally-adapted versions of TV spot scripts. The Outlines library
guarantees valid JSON output matching the Pydantic schema.

Key Features:
    - Culturally-sensitive adaptations based on market rules
    - Preserves original timing and structure
    - Adapts language, idioms, visual cues, and references
    - Generates Pydantic-validated output for type safety

Classes:
    :class:`ScriptRowOutput`
        Pydantic model for a single adapted script row

    :class:`AdaptationOutput`
        Pydantic model for the complete adaptation

    :class:`AdaptationGenerator`
        Main generator class using Outlines for structured LLM output

Usage::

    from cw.lib.adaptation import AdaptationGenerator

    generator = AdaptationGenerator()

    # origin_version: TvSpotVersion instance
    # target_market: AdaptationMarket instance with rules
    result = generator.adapt(origin_version, target_market)

    print(result.code)  # "US-HISP"
    print(result.language)  # "es-MX"
    for row in result.script_rows:
        print(f"{row.shot_number}: {row.visual_text}")

Singleton Access::

    from cw.lib.adaptation import get_adaptation_generator

    generator = get_adaptation_generator()  # Reuses existing instance

Note:
    Uses Qwen2.5-3B-Instruct by default for multilingual capabilities.
    Optimized for Apple Silicon (MPS) with automatic device detection.
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, Field

from cw.lib.prompts import render_prompt

logger = logging.getLogger(__name__)


class ScriptRowOutput(BaseModel):
    """Pydantic model for a single adapted script row."""

    shot_number: str = Field(description="Shot identifier (e.g., '01', '1A')")
    timecode_start: str = Field(default="", description="Start timecode")
    duration_seconds: Optional[float] = Field(default=None, description="Row duration in seconds")
    visual_text: str = Field(description="Visual column: shots, supers, locations, casting notes")
    audio_text: str = Field(description="Audio column: dialogue, VO, SFX, music cues, taglines")


class AdaptationOutput(BaseModel):
    """Pydantic model for the complete adaptation output."""

    code: str = Field(description="Internal code for this adaptation (e.g., 'US-HISP', 'JP')")
    name: str = Field(description="Human-readable name (e.g., 'US Hispanic Adaptation')")
    language: str = Field(description="Primary language code (e.g., 'es-MX', 'ja')")
    visual_style_prompt: str = Field(
        default="", description="Common prompt prefix for storyboard generation consistency"
    )
    script_rows: list[ScriptRowOutput] = Field(
        description="Adapted script rows maintaining original structure"
    )


class AdaptationGenerator:
    """
    Generates culturally-adapted TV spot versions using LLM with Outlines.

    Uses Qwen model for multilingual capabilities and Outlines library
    to guarantee valid JSON output matching the expected schema.
    """

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-3B-Instruct",
        device: Optional[str] = None,
        load_in_4bit: bool = False,
    ):
        """
        Initialize the adaptation generator.

        Args:
            model_id: HuggingFace model ID
            device: Device to use ('cpu', 'mps', 'cuda', or None for auto-detect)
            load_in_4bit: Whether to load with 4-bit quantization (requires bitsandbytes)
        """
        self.model_id = model_id
        self.device = device
        self.load_in_4bit = load_in_4bit
        self._model = None
        self._tokenizer = None
        self._generator = None

    def _is_model_cached(self) -> bool:
        """Check if the model is already cached locally."""
        try:
            from huggingface_hub import try_to_load_from_cache
            from huggingface_hub.utils import LocalEntryNotFoundError

            # Check for a file that should exist in any HF model
            result = try_to_load_from_cache(self.model_id, "config.json")
            return result is not None
        except Exception:
            # If we can't determine cache status, assume not cached
            return False

    def _load_model(self):
        """Load the model and create Outlines generator."""
        if self._generator is not None:
            logger.debug("Model already loaded, skipping _load_model")
            return

        import outlines
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        # Check if model is cached locally
        is_cached = self._is_model_cached()
        if is_cached:
            logger.info(f"Model '{self.model_id}' found in local cache, loading...")
        else:
            logger.info(f"Model '{self.model_id}' not in cache, downloading from HuggingFace Hub...")
            logger.info("This may take several minutes depending on model size and connection speed.")

        # Detect device
        if self.device is None:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

        logger.info(f"Using device: {self.device}, load_in_4bit: {self.load_in_4bit}")

        # Load model and tokenizer with transformers
        dtype = torch.bfloat16 if self.device != "cpu" else torch.float32
        model_kwargs = {
            "torch_dtype": dtype,
            "low_cpu_mem_usage": True,
            "device_map": self.device if not self.load_in_4bit else "auto",
        }

        # Add 4-bit quantization config if enabled (requires CUDA and bitsandbytes)
        if self.load_in_4bit:
            if self.device != "cuda":
                logger.warning(
                    f"4-bit quantization requested but device is {self.device}. "
                    "4-bit quantization requires CUDA. Falling back to standard loading."
                )
            else:
                from transformers import BitsAndBytesConfig

                logger.info("Using 4-bit quantization with bitsandbytes")
                model_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=dtype,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )

        logger.debug(f"Loading HuggingFace model with dtype={dtype}")
        hf_model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            **model_kwargs,
        )
        if not is_cached:
            logger.info(f"Model '{self.model_id}' download complete.")
        logger.debug("HuggingFace model loaded, loading tokenizer")
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        logger.debug("Tokenizer loaded")

        # Wrap with Outlines
        logger.debug("Wrapping model with outlines.from_transformers")
        self._model = outlines.from_transformers(hf_model, self._tokenizer, device_dtype=dtype)
        logger.debug("Outlines model wrapper created")

        # Create generator with JSON schema output type
        logger.debug("Creating Outlines Generator with AdaptationOutput schema")
        self._generator = outlines.Generator(self._model, output_type=AdaptationOutput)
        logger.debug("Outlines Generator created")

        if is_cached:
            logger.info(f"Adaptation model '{self.model_id}' loaded successfully from cache.")
        else:
            logger.info(f"Adaptation model '{self.model_id}' downloaded and loaded successfully.")

    def adapt(
        self,
        adaptation_job,
        creativity: float = 0.7,
    ) -> AdaptationOutput:
        """
        Generate a culturally-adapted version of a TV spot.

        Args:
            adaptation_job: AdaptationJob instance with origin_version, target_market,
                and optional language/llm_model overrides
            creativity: Temperature for generation (0.0-1.0)

        Returns:
            AdaptationOutput with adapted script content
        """
        origin_version = adaptation_job.origin_version
        target_market = adaptation_job.target_market

        # Get effective language and model (from job overrides or market/language defaults)
        effective_language = adaptation_job.effective_language
        effective_model = adaptation_job.effective_llm_model

        logger.debug(
            f"adapt() called: origin_version_id={origin_version.pk}, "
            f"target_market={target_market.code}, language={effective_language.code if effective_language else 'None'}, "
            f"model={effective_model.model_id if effective_model else 'None'}, creativity={creativity}"
        )

        # Use the effective model from the job
        if effective_model:
            required_model = effective_model.model_id
            required_4bit = getattr(effective_model, "load_in_4bit", False)
            if required_model != self.model_id or required_4bit != self.load_in_4bit:
                logger.info(
                    f"Switching model for {effective_language.code}: "
                    f"{self.model_id} -> {required_model} (4bit: {required_4bit})"
                )
                self.clear_cache()
                self.model_id = required_model
                self.load_in_4bit = required_4bit

        self._load_model()

        tv_spot = origin_version.tv_spot
        logger.debug(f"TV Spot: {tv_spot.script_title} (id={tv_spot.pk})")

        # Build the original spot data
        logger.debug("Building original spot data structure")
        original_spot = {
            "client_name": tv_spot.client_name,
            "brand_name": tv_spot.brand_name,
            "script_title": tv_spot.script_title,
            "total_runtime_seconds": tv_spot.total_runtime_seconds,
            "language": origin_version.language,
            "script_rows": [
                {
                    "shot_number": row.shot_number,
                    "timecode_start": row.timecode_start,
                    "duration_seconds": (
                        float(row.duration_seconds) if row.duration_seconds else None
                    ),
                    "visual_text": row.visual_text,
                    "audio_text": row.audio_text,
                }
                for row in origin_version.script_rows.all().order_by("order_index")
            ],
        }
        logger.debug(f"Original spot has {len(original_spot['script_rows'])} script rows")

        # Build the prompt
        logger.debug("Building LLM prompt")
        prompt = self._build_prompt(original_spot, target_market, effective_language, creativity)
        logger.debug(f"Prompt built, length={len(prompt)} chars")

        logger.info(
            f"Generating adaptation for '{tv_spot.script_title}' to {target_market.name}",
            extra={
                "tv_spot_id": tv_spot.pk,
                "origin_version_id": origin_version.pk,
                "target_market": target_market.code,
                "num_rows": len(original_spot["script_rows"]),
            },
        )

        # Generate with Outlines (guaranteed valid JSON)
        # max_new_tokens needs to be high enough for full JSON output
        logger.debug("Calling Outlines generator with max_new_tokens=4096")
        raw_result = self._generator(prompt, max_new_tokens=4096)
        logger.debug(f"Generator returned result of type {type(raw_result).__name__}")

        # Parse the result - Outlines 1.x returns JSON string, need to parse to Pydantic
        if isinstance(raw_result, str):
            logger.debug(f"Raw result is string, length={len(raw_result)} chars")
            logger.debug(f"Raw result preview: {raw_result[:500]}...")
            import json

            logger.debug("Parsing JSON and validating with Pydantic")
            result = AdaptationOutput.model_validate(json.loads(raw_result))
            logger.debug("Pydantic validation successful")
        else:
            logger.debug("Raw result is already parsed object")
            result = raw_result

        logger.info(
            f"Adaptation generated successfully",
            extra={
                "adaptation_code": result.code,
                "adaptation_language": result.language,
                "num_adapted_rows": len(result.script_rows),
            },
        )

        return result

    def _build_prompt(self, original_spot: dict, target_market, language, creativity: float) -> str:
        """Build the adaptation prompt using Jinja2 template with chat formatting.

        Args:
            original_spot: Dict with original TV spot data
            target_market: AdaptationMarket instance
            language: Language instance (the effective language for the adaptation)
            creativity: Temperature for generation
        """
        import json

        language_code = language.code if language else "en"
        language_name = language.name if language else "English"

        logger.debug(f"_build_prompt: target_market={target_market.code}, language={language_code}, creativity={creativity}")
        original_json = json.dumps(original_spot, indent=2, ensure_ascii=False)
        logger.debug(f"Original spot JSON length: {len(original_json)} chars")

        user_prompt = render_prompt(
            "adaptation.j2",
            target_market_name=target_market.name,
            target_market_language=language_code,
            target_market_rules=target_market.rules_as_markdown(),
            target_market_code=target_market.code.upper(),
            original_json=original_json,
            num_script_rows=len(original_spot["script_rows"]),
            creativity=creativity,
        )

        # System message to enforce English for descriptions
        system_message = (
            "You are an expert advertising creative and localization strategist. "
            "CRITICAL LANGUAGE RULE: You MUST write ALL descriptions, stage directions, "
            f"and visual_text content in ENGLISH. Only spoken dialogue (VO) and on-screen text "
            f"(supers, titles) should use {language_name} ({language_code}), and these MUST include "
            "an English translation in parentheses. Never write scene descriptions in any "
            "language other than English."
        )

        # Format using Qwen chat template
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt},
        ]

        prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        logger.debug(f"Chat-formatted prompt length: {len(prompt)} chars")

        return prompt

    def clear_cache(self):
        """Clear the model from memory."""
        import torch

        logger.debug("clear_cache() called")

        if self._generator is not None:
            logger.debug("Deleting generator")
            del self._generator
            self._generator = None

        if self._model is not None:
            logger.debug("Deleting model")
            del self._model
            self._model = None

        if self._tokenizer is not None:
            logger.debug("Deleting tokenizer")
            del self._tokenizer
            self._tokenizer = None

        if self.device == "mps":
            logger.debug("Clearing MPS cache")
            torch.mps.empty_cache()
        elif self.device == "cuda":
            logger.debug("Clearing CUDA cache")
            torch.cuda.empty_cache()

        logger.info("Adaptation model cache cleared")


# Module-level singleton for reuse across tasks
_adaptation_generator: Optional[AdaptationGenerator] = None


def get_adaptation_generator(
    model_id: str = "Qwen/Qwen2.5-3B-Instruct",
    load_in_4bit: bool = False,
) -> AdaptationGenerator:
    """Get or create the adaptation generator singleton."""
    global _adaptation_generator

    logger.debug(f"get_adaptation_generator called with model_id={model_id}, load_in_4bit={load_in_4bit}")

    if (
        _adaptation_generator is None
        or _adaptation_generator.model_id != model_id
        or _adaptation_generator.load_in_4bit != load_in_4bit
    ):
        logger.debug("Creating new AdaptationGenerator instance")
        _adaptation_generator = AdaptationGenerator(model_id=model_id, load_in_4bit=load_in_4bit)
    else:
        logger.debug("Returning existing AdaptationGenerator instance")

    return _adaptation_generator
