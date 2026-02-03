#!/usr/bin/env python3
"""
Mixins for model implementations
Shared behaviors that can be composed with BaseModel
"""

import re
from typing import Dict


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
        return re.sub(r'<lora:[^>]+>', '', text).strip().rstrip(',').strip()

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
        params['prompt'] = self._fit_prompt_to_token_limit(params['prompt'], lora_suffix)

        # Handle negative prompt
        if self.supports_negative_prompt and params['negative_prompt']:
            lora_neg_suffix = self.get_lora_negative_prompt_suffix()
            if lora_neg_suffix:
                params['negative_prompt'] = f"{params['negative_prompt']}, {lora_neg_suffix}"

        return params


class DebugLoggingMixin:
    """
    Mixin for models that need debug print statements

    Used by ZImageTurbo and SDXLTurbo for diagnostic output.
    """

    def _debug_print(self, message: str) -> None:
        """
        Print debug message if debug logging is enabled

        Args:
            message: Debug message to print
        """
        if getattr(self, 'enable_debug_logging', False):
            print(f"DEBUG [{self.__class__.__name__}]: {message}")
