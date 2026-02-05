"""
TV Spot Adaptation using LLM with Outlines for structured JSON output.

Uses local Qwen model with Outlines library to generate culturally-adapted
versions of TV spot scripts with guaranteed valid JSON output.

Usage:
    from lib.adaptation import AdaptationGenerator

    generator = AdaptationGenerator()
    result = generator.adapt(origin_version, target_market)
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

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
    ):
        """
        Initialize the adaptation generator.

        Args:
            model_id: HuggingFace model ID
            device: Device to use ('cpu', 'mps', 'cuda', or None for auto-detect)
        """
        self.model_id = model_id
        self.device = device
        self._model = None
        self._tokenizer = None
        self._generator = None

    def _load_model(self):
        """Load the model and create Outlines generator."""
        if self._generator is not None:
            logger.debug("Model already loaded, skipping _load_model")
            return

        import outlines
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info(f"Loading model for adaptation: {self.model_id}")

        # Detect device
        if self.device is None:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

        logger.info(f"Using device: {self.device}")

        # Load model and tokenizer with transformers
        dtype = torch.bfloat16 if self.device != "cpu" else torch.float32
        logger.debug(f"Loading HuggingFace model with dtype={dtype}")
        hf_model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            device_map=self.device,
        )
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

        logger.info("Adaptation model loaded successfully")

    def adapt(
        self,
        origin_version,
        target_market,
        creativity: float = 0.7,
    ) -> AdaptationOutput:
        """
        Generate a culturally-adapted version of a TV spot.

        Args:
            origin_version: TvSpotVersion instance (the origin to adapt from)
            target_market: AdaptationMarket instance (target market with rules)
            creativity: Temperature for generation (0.0-1.0)

        Returns:
            AdaptationOutput with adapted script content
        """
        logger.debug(
            f"adapt() called: origin_version_id={origin_version.pk}, "
            f"target_market={target_market.code}, creativity={creativity}"
        )

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
        prompt = self._build_prompt(original_spot, target_market, creativity)
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

    def _build_prompt(self, original_spot: dict, target_market, creativity: float) -> str:
        """Build the adaptation prompt for the LLM."""
        import json

        logger.debug(f"_build_prompt: target_market={target_market.code}, creativity={creativity}")
        original_json = json.dumps(original_spot, indent=2, ensure_ascii=False)
        logger.debug(f"Original spot JSON length: {len(original_json)} chars")

        prompt = f"""You are an expert advertising creative and localization strategist.

Your task is to create a culturally sensitive, legally compliant, and creatively strong adaptation of a TV spot for a specified target market, while preserving the core brand idea and campaign objectives.

## Target Market: {target_market.name}

### Market Rules and Guidelines:
{target_market.rules}

## Original TV Spot:
```json
{original_json}
```

## Adaptation Requirements:

1. **Preserve**:
   - The core brand idea and primary call to action
   - The emotional arc and key storytelling beats
   - The overall timing and structure

2. **Adapt**:
   - Language to natural, idiomatic usage in the target market
   - Humor, idioms, metaphors, and references for cultural relevance
   - Settings, props, and lifestyle cues to feel authentic
   - On-screen text and taglines to align with local expectations
   - Visual details (gestures, symbols, colors) for cultural appropriateness

3. **Avoid**:
   - Stereotypes or exoticizing portrayals
   - Sensitive imagery related to religion, politics, or historical trauma
   - Claims that may be misleading in the target market

## Output Requirements:

Generate a JSON object with:
- `code`: Market code for this adaptation (e.g., "{target_market.code.upper()}")
- `name`: Human-readable name (e.g., "{target_market.name} Adaptation")
- `language`: Primary language code for the adaptation
- `visual_style_prompt`: A common prompt prefix for consistent storyboard generation
- `script_rows`: Array of adapted rows, each with shot_number, timecode_start, duration_seconds, visual_text, audio_text

Adapt all {len(original_spot['script_rows'])} script rows, maintaining the same structure and timing.

Creativity level: {creativity}/1.0 (higher = more creative adaptations)

Generate the adapted TV spot:"""

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


def get_adaptation_generator(model_id: str = "Qwen/Qwen2.5-3B-Instruct") -> AdaptationGenerator:
    """Get or create the adaptation generator singleton."""
    global _adaptation_generator

    logger.debug(f"get_adaptation_generator called with model_id={model_id}")

    if _adaptation_generator is None or _adaptation_generator.model_id != model_id:
        logger.debug("Creating new AdaptationGenerator instance")
        _adaptation_generator = AdaptationGenerator(model_id=model_id)
    else:
        logger.debug("Returning existing AdaptationGenerator instance")

    return _adaptation_generator
