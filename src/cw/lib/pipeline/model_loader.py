"""Shared model loader for the adaptation pipeline.

Extracts model loading logic from AdaptationGenerator into a reusable
class that can serve Outlines generators for any Pydantic schema.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PipelineModelLoader:
    """Loads and caches an LLM, producing Outlines generators for arbitrary schemas.

    Designed as a shared resource: the model loads once, and ``get_generator()``
    can be called with different Pydantic schemas cheaply.
    """

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-3B-Instruct",
        device: Optional[str] = None,
        load_in_4bit: bool = False,
    ):
        self.model_id = model_id
        self.device = device
        self.load_in_4bit = load_in_4bit
        self._model = None
        self._tokenizer = None

    def _is_model_cached(self) -> bool:
        """Check if the model is already cached locally."""
        try:
            from huggingface_hub import try_to_load_from_cache

            result = try_to_load_from_cache(self.model_id, "config.json")
            return result is not None
        except Exception:
            return False

    def _load_model(self):
        """Load the HuggingFace model and tokenizer (lazy, cached)."""
        if self._model is not None:
            logger.debug("Model already loaded, skipping _load_model")
            return

        import outlines
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        is_cached = self._is_model_cached()
        if is_cached:
            logger.info(f"Model '{self.model_id}' found in local cache, loading...")
        else:
            logger.info(f"Model '{self.model_id}' not in cache, downloading from HuggingFace Hub...")

        # Detect device
        if self.device is None:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

        logger.info(f"Using device: {self.device}, load_in_4bit: {self.load_in_4bit}")

        dtype = torch.bfloat16 if self.device != "cpu" else torch.float32
        model_kwargs = {
            "torch_dtype": dtype,
            "low_cpu_mem_usage": True,
            "device_map": self.device if not self.load_in_4bit else "auto",
        }

        if self.load_in_4bit:
            if self.device != "cuda":
                logger.warning(
                    f"4-bit quantization requested but device is {self.device}. "
                    "Falling back to standard loading."
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

        hf_model = AutoModelForCausalLM.from_pretrained(self.model_id, **model_kwargs)
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)

        self._model = outlines.from_transformers(hf_model, self._tokenizer, device_dtype=dtype)

        logger.info(f"Model '{self.model_id}' loaded successfully.")

    @property
    def tokenizer(self):
        """Access the tokenizer (loads model if needed)."""
        self._load_model()
        return self._tokenizer

    def get_generator(self, output_schema):
        """Return an Outlines generator bound to a specific Pydantic schema.

        Args:
            output_schema: A Pydantic BaseModel class defining the output format.

        Returns:
            An ``outlines.Generator`` that produces JSON matching the schema.
        """
        import outlines

        self._load_model()
        logger.debug(f"Creating Outlines Generator for schema {output_schema.__name__}")

        # Create generator - Outlines will use default sampling parameters
        # which helps avoid numerical instability
        base_generator = outlines.Generator(self._model, output_type=output_schema)

        # Wrap to add retry logic for probability tensor errors
        class GeneratorWithRetry:
            """Wrapper that retries generation with safer parameters on numerical errors."""

            def __call__(self, prompt, max_new_tokens=4096, **kwargs):
                logger.debug(
                    f"Generating with schema {output_schema.__name__}, max_tokens={max_new_tokens}"
                )

                try:
                    # First attempt with default parameters
                    result = base_generator(prompt, max_new_tokens=max_new_tokens, **kwargs)
                    return result

                except Exception as e:
                    error_str = str(e).lower()

                    # Check if it's a numerical stability error
                    if any(keyword in error_str for keyword in ["probability tensor", "inf", "nan", "element < 0"]):
                        logger.warning(
                            f"Numerical stability error detected: {e}. "
                            f"This can happen with structured generation. "
                            f"Clearing cache and retrying..."
                        )

                        # Clear GPU cache which can help with numerical stability
                        import torch
                        if torch.backends.mps.is_available():
                            torch.mps.empty_cache()
                        elif torch.cuda.is_available():
                            torch.cuda.empty_cache()

                        # Retry with a shorter prompt if possible
                        logger.warning("Retrying generation after cache clear...")
                        try:
                            result = base_generator(prompt, max_new_tokens=max_new_tokens, **kwargs)
                            logger.info("Retry after cache clear succeeded")
                            return result
                        except Exception as retry_e:
                            logger.error(f"Retry also failed: {retry_e}")

                    # Re-raise the original error
                    logger.error(
                        f"Generation failed for {output_schema.__name__}: {e}",
                        exc_info=True,
                    )
                    raise

        return GeneratorWithRetry()

    def switch_model(self, model_id: str, load_in_4bit: bool = False):
        """Clear cache and reconfigure for a different model."""
        logger.info(f"Switching model: {self.model_id} -> {model_id}")
        self.clear_cache()
        self.model_id = model_id
        self.load_in_4bit = load_in_4bit

    def clear_cache(self):
        """Clear the model from memory."""
        import torch

        if self._model is not None:
            del self._model
            self._model = None

        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        if self.device == "mps":
            torch.mps.empty_cache()
        elif self.device == "cuda":
            torch.cuda.empty_cache()

        logger.info("Model cache cleared")


# Module-level singleton
_model_loader: Optional[PipelineModelLoader] = None


def get_model_loader(
    model_id: str = "Qwen/Qwen2.5-3B-Instruct",
    load_in_4bit: bool = False,
) -> PipelineModelLoader:
    """Get or create the shared PipelineModelLoader singleton."""
    global _model_loader

    if (
        _model_loader is None
        or _model_loader.model_id != model_id
        or _model_loader.load_in_4bit != load_in_4bit
    ):
        _model_loader = PipelineModelLoader(model_id=model_id, load_in_4bit=load_in_4bit)

    return _model_loader
