#!/usr/bin/env python3
"""
Mixins for model implementations.

This module provides reusable behaviors that can be composed with
:class:`~cw.lib.models.base.BaseModel` via multiple inheritance.

Available Mixins:
    :class:`CompelPromptMixin`
        Long prompt handling (>77 tokens) and prompt weighting syntax
        ``(word:1.3)`` for CLIP-based models. Recommended for SDXL/SD15.

    :class:`CLIPTokenLimitMixin`
        Simple 77-token truncation with LoRA suffix preservation.
        Legacy mixin - prefer CompelPromptMixin for new models.

    :class:`DebugLoggingMixin`
        Conditional debug print statements via ``enable_debug_logging`` flag.

Usage Example::

    from cw.lib.models.base import BaseModel
    from cw.lib.models.mixins import CompelPromptMixin

    class MySDXLModel(CompelPromptMixin, BaseModel):
        def _create_pipeline(self):
            return StableDiffusionXLPipeline.from_pretrained(...)

Note:
    Mixins must be listed before BaseModel in the inheritance order
    (MRO) to properly override BaseModel methods.
"""

import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


class CLIPTokenLimitMixin:
    """
    Mixin for models that need CLIP 77-token limit handling

    Used by SDXL, SDXLTurbo, and SD15 models to ensure prompts
    fit within CLIP's token limit while prioritizing LoRA trigger words.
    """

    @staticmethod
    def _strip_a1111_lora_tags(text: str) -> str:
        """
        Remove A1111/ComfyUI <lora:...> tags which are meaningless in diffusers.

        Args:
            text: Text containing potential LoRA tags

        Returns:
            Text with LoRA tags removed and cleaned up
        """
        return re.sub(r"<lora:[^>]+>", "", text).strip().rstrip(",").strip()

    def _fit_prompt_to_token_limit(self, prompt: str, suffix: str) -> str:
        """
        Build a prompt that fits within CLIP's 77-token limit.

        Prioritizes the LoRA suffix (trigger words), then fills remaining
        space with as much of the prompt as possible.

        Args:
            prompt: Base prompt text
            suffix: LoRA suffix to append (prioritized)

        Returns:
            Prompt that fits within token limit
        """
        suffix = self._strip_a1111_lora_tags(suffix)
        tokenizer = self.pipeline.tokenizer
        max_content_tokens = tokenizer.model_max_length - 2  # Reserve for special tokens

        # If no suffix, just truncate prompt if needed
        if not suffix:
            tokens = tokenizer.encode(prompt, add_special_tokens=False)
            if len(tokens) <= max_content_tokens:
                return prompt
            return tokenizer.decode(tokens[:max_content_tokens], skip_special_tokens=True)

        # Build suffix with separator
        suffix_with_sep = f", {suffix}"
        suffix_tokens = tokenizer.encode(suffix_with_sep, add_special_tokens=False)
        prompt_tokens = tokenizer.encode(prompt, add_special_tokens=False)

        # If both fit, return concatenated
        if len(prompt_tokens) + len(suffix_tokens) <= max_content_tokens:
            return f"{prompt}{suffix_with_sep}"

        # Calculate available space for prompt after reserving space for suffix
        available = max_content_tokens - len(suffix_tokens)
        if available <= 0:
            # Suffix alone exceeds limit, truncate suffix
            return tokenizer.decode(suffix_tokens[:max_content_tokens], skip_special_tokens=True)

        # Truncate prompt to fit available space
        truncated = tokenizer.decode(prompt_tokens[:available], skip_special_tokens=True)
        return f"{truncated}{suffix_with_sep}"

    def _build_prompts(self, params: Dict) -> Dict:
        """
        Override to apply token limiting to prompts

        Args:
            params: Parameter dictionary

        Returns:
            Updated parameter dictionary with token-limited prompts
        """
        # Apply token limiting to main prompt with LoRA suffix
        lora_suffix = self.get_lora_prompt_suffix()
        params["prompt"] = self._fit_prompt_to_token_limit(params["prompt"], lora_suffix)

        # Handle negative prompt
        if self.supports_negative_prompt and params["negative_prompt"]:
            lora_neg_suffix = self.get_lora_negative_prompt_suffix()
            if lora_neg_suffix:
                params["negative_prompt"] = f"{params['negative_prompt']}, {lora_neg_suffix}"

        return params


class CompelPromptMixin:
    """
    Mixin for models that use Compel for long prompt handling and prompt weighting

    Compel enables:
    - Prompts longer than 77 tokens (breaks into chunks, concatenates embeddings)
    - Prompt weighting syntax: (word:1.3) for emphasis, (word:0.8) for de-emphasis
    - Proper handling of LoRA trigger words without truncation

    Used by SDXL, SDXLTurbo, and SD15 models as an alternative to CLIPTokenLimitMixin.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._compel = None

    @staticmethod
    def _strip_a1111_lora_tags(text: str) -> str:
        """
        Remove A1111/ComfyUI <lora:...> tags which are meaningless in diffusers.

        Args:
            text: Text containing potential LoRA tags

        Returns:
            Text with LoRA tags removed and cleaned up
        """
        return re.sub(r"<lora:[^>]+>", "", text).strip().rstrip(",").strip()

    def _get_compel(self):
        """
        Lazy-initialize Compel instance for prompt encoding
        Handles both single and dual text encoder models (SDXL)

        Returns:
            Compel instance (CompelForSDXL or CompelForSD)
        """
        if self._compel is None:
            logger.debug("Initializing Compel for prompt encoding")
            # Compel expects device as string ("mps", "cuda", "cpu")
            device_str = str(self.device.type) if hasattr(self.device, "type") else str(self.device)
            logger.debug(f"Compel device: {device_str}")

            # Check if model has dual text encoders (SDXL)
            has_text_encoder_2 = hasattr(self.pipeline, "text_encoder_2") and hasattr(
                self.pipeline, "tokenizer_2"
            )
            logger.debug(f"Has dual text encoders (SDXL): {has_text_encoder_2}")

            # Compel wrappers don't work with CPU offloading
            # We need to ensure the text encoders are loaded before Compel accesses them
            # Check if text encoder is on meta device (from CPU offload)
            text_encoder_on_meta = (
                hasattr(self.pipeline.text_encoder, "device")
                and str(self.pipeline.text_encoder.device) == "meta"
            )

            if text_encoder_on_meta:
                logger.warning("Text encoders on meta device due to CPU offload")
                logger.debug("Compel requires text encoders on real device, moving pipeline")
                # Remove the offload hooks
                if hasattr(self.pipeline, "_all_hooks"):
                    self.pipeline._all_hooks = []
                # Move pipeline to device
                self.pipeline = self.pipeline.to(self.device)
                logger.debug(f"Pipeline moved to {self.device}")

            if has_text_encoder_2:
                # SDXL: Use CompelForSDXL wrapper
                from compel import CompelForSDXL

                logger.debug("Creating CompelForSDXL wrapper")
                self._compel = CompelForSDXL(
                    pipe=self.pipeline,
                    device=device_str,
                )
            else:
                # SD 1.5: Use CompelForSD wrapper
                from compel import CompelForSD

                logger.debug("Creating CompelForSD wrapper")
                self._compel = CompelForSD(
                    pipe=self.pipeline,
                    device=device_str,
                )
            logger.debug("Compel initialized successfully")
        return self._compel

    def _build_prompts(self, params: Dict) -> Dict:
        """
        Override to use Compel for prompt encoding

        Converts text prompts to embeddings using Compel, which allows:
        - Long prompts (>77 tokens)
        - Prompt weighting syntax
        - Proper LoRA trigger word handling
        - Proper SDXL dual text encoder support

        Args:
            params: Parameter dictionary with 'prompt' and optional 'negative_prompt'

        Returns:
            Updated parameter dictionary with 'prompt_embeds' and 'negative_prompt_embeds'
        """
        logger.debug("Building prompts with Compel")
        compel = self._get_compel()

        # Preserve original prompts for metadata (before encoding)
        original_prompt = params["prompt"]
        original_negative_prompt = params.get("negative_prompt")
        logger.debug(f"Original prompt length: {len(original_prompt)} chars")

        # Build final prompt with LoRA suffix
        lora_suffix = self.get_lora_prompt_suffix()
        lora_suffix = self._strip_a1111_lora_tags(lora_suffix)

        if lora_suffix:
            full_prompt = f"{original_prompt}, {lora_suffix}"
            logger.debug(f"Added LoRA suffix: {lora_suffix[:50]}...")
        else:
            full_prompt = original_prompt

        # Encode prompt to embeddings using Compel
        # CompelForSDXL/CompelForSD return LabelledConditioning objects
        logger.debug("Encoding prompt with Compel")
        conditioning = compel(full_prompt)

        # Extract embeddings from LabelledConditioning
        logger.debug(f"Conditioning type: {type(conditioning).__name__}")

        # Check if it's a LabelledConditioning object (from CompelFor* wrappers)
        if hasattr(conditioning, "embeds"):
            # CompelForSDXL or CompelForSD wrapper
            logger.debug("Using LabelledConditioning wrapper")
            params["prompt_embeds"] = conditioning.embeds
            logger.debug(f"prompt_embeds shape: {conditioning.embeds.shape}")

            # SDXL has pooled embeddings
            if hasattr(conditioning, "pooled_embeds") and conditioning.pooled_embeds is not None:
                params["pooled_prompt_embeds"] = conditioning.pooled_embeds
                logger.debug(f"pooled_prompt_embeds shape: {conditioning.pooled_embeds.shape}")
        elif isinstance(conditioning, tuple):
            # Legacy Compel returns (prompt_embeds, pooled_prompt_embeds)
            logger.debug("Legacy tuple format from Compel")
            prompt_embeds, pooled_prompt_embeds = conditioning
            params["prompt_embeds"] = prompt_embeds
            params["pooled_prompt_embeds"] = pooled_prompt_embeds
        else:
            # Direct tensor (shouldn't happen with current wrappers)
            logger.debug("Direct tensor format from Compel")
            params["prompt_embeds"] = conditioning

        # Handle negative prompt
        if self.supports_negative_prompt:
            # Build negative prompt with LoRA suffix
            lora_neg_suffix = self.get_lora_negative_prompt_suffix()
            if lora_neg_suffix:
                lora_neg_suffix = self._strip_a1111_lora_tags(lora_neg_suffix)
                full_negative = (
                    f"{original_negative_prompt}, {lora_neg_suffix}"
                    if original_negative_prompt
                    else lora_neg_suffix
                )
            else:
                full_negative = original_negative_prompt if original_negative_prompt else ""

            # Encode negative prompt
            logger.debug("Encoding negative prompt with Compel")
            negative_conditioning = compel(full_negative)

            # Extract negative embeddings from LabelledConditioning
            if hasattr(negative_conditioning, "embeds"):
                # CompelForSDXL or CompelForSD wrapper
                params["negative_prompt_embeds"] = negative_conditioning.embeds
                logger.debug(f"negative_prompt_embeds shape: {negative_conditioning.embeds.shape}")

                # SDXL has pooled embeddings
                if (
                    hasattr(negative_conditioning, "pooled_embeds")
                    and negative_conditioning.pooled_embeds is not None
                ):
                    params["negative_pooled_prompt_embeds"] = negative_conditioning.pooled_embeds
                    logger.debug(
                        f"negative_pooled_prompt_embeds shape: {negative_conditioning.pooled_embeds.shape}"
                    )
            elif isinstance(negative_conditioning, tuple):
                # Legacy Compel
                negative_prompt_embeds, negative_pooled_prompt_embeds = negative_conditioning
                params["negative_prompt_embeds"] = negative_prompt_embeds
                params["negative_pooled_prompt_embeds"] = negative_pooled_prompt_embeds
            else:
                # Direct tensor
                params["negative_prompt_embeds"] = negative_conditioning

        # Keep original text prompts in params for metadata
        # (Pipeline will use embeddings when both are present)
        params["prompt"] = full_prompt  # Full prompt with LoRA suffix for metadata
        if self.supports_negative_prompt:
            if lora_neg_suffix and original_negative_prompt:
                params["negative_prompt"] = f"{original_negative_prompt}, {lora_neg_suffix}"
            elif original_negative_prompt:
                params["negative_prompt"] = original_negative_prompt
            elif lora_neg_suffix:
                params["negative_prompt"] = lora_neg_suffix

        logger.debug("Prompt encoding complete")
        return params


class DebugLoggingMixin:
    """
    Mixin for models that need debug print statements

    Used by ZImageTurbo and SDXLTurbo for diagnostic output.
    """

    def _debug_print(self, message: str) -> None:
        """
        Log debug message if debug logging is enabled

        Args:
            message: Debug message to log
        """
        if getattr(self, "enable_debug_logging", False):
            logger.debug(f"[{self.__class__.__name__}] {message}")
