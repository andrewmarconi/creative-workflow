"""
Storyboard generation from TV spot scripts.

This module generates image prompts from TV spot script visual descriptions
and creates DiffusionJobs for storyboard frame generation.

Key Features:
    - Extracts visual elements from script descriptions
    - Optional LLM enhancement for more detailed prompts
    - Creates linked DiffusionJob records for each frame
    - Supports visual style prefixes for consistency

Classes:
    :class:`StoryboardGenerator`
        Generates image prompts from script rows with optional LLM enhancement

Functions:
    :func:`create_storyboard_jobs`
        Creates DiffusionJob and StoryboardImage records from prompts

Workflow:
    1. Extract visual elements from script row ``visual_text``
    2. Add visual style prefix and cinematic quality keywords
    3. Optionally enhance with LLM (HFPromptEnhancer)
    4. Create DiffusionJob records linked to StoryboardJob

Usage::

    from cw.lib.storyboard import StoryboardGenerator, create_storyboard_jobs

    # Generate prompts
    generator = StoryboardGenerator(use_llm=True)
    prompts = generator.generate_prompts_for_version(tv_spot_version)

    # Create DiffusionJobs
    jobs = create_storyboard_jobs(storyboard_job, prompts)

Note:
    Generated storyboard frames use 1280x720 (16:9) dimensions by default.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class StoryboardGenerator:
    """
    Generates storyboard image prompts from TV spot script rows.

    Can use either simple prompt building (combines visual description with
    style prefix) or LLM-enhanced prompts for more detailed generation.
    """

    def __init__(
        self,
        use_llm: bool = True,
        model_id: str = "Qwen/Qwen2.5-3B-Instruct",
        device: Optional[str] = None,
    ):
        """
        Initialize the storyboard generator.

        Args:
            use_llm: Whether to use LLM for enhanced prompt generation
            model_id: HuggingFace model ID for prompt enhancement
            device: Device to use ('cpu', 'mps', 'cuda', or None for auto-detect)
        """
        self.use_llm = use_llm
        self.model_id = model_id
        self.device = device
        self._enhancer = None

    def _get_enhancer(self):
        """Get or create the prompt enhancer."""
        if self._enhancer is None and self.use_llm:
            logger.debug(f"Creating HFPromptEnhancer with model: {self.model_id}")
            from cw.lib.prompt_enhancer import HFPromptEnhancer

            self._enhancer = HFPromptEnhancer(
                model_id=self.model_id,
                style="cinematic",
                creativity=0.7,
            )
            logger.debug("HFPromptEnhancer created")
        return self._enhancer

    def generate_prompt(
        self,
        visual_text: str,
        audio_text: str,
        visual_style_prompt: str = "",
        enhance: bool = True,
    ) -> dict:
        """
        Generate an image prompt from a script row.

        Args:
            visual_text: Visual description from script (shots, settings, actions)
            audio_text: Audio description (dialogue, VO) for context
            visual_style_prompt: Common style prefix for consistency
            enhance: Whether to use LLM enhancement

        Returns:
            Dict with 'prompt' and optionally 'negative_prompt'
        """
        logger.debug(f"Generating prompt from visual_text: {visual_text[:80]}...")

        # Build base prompt from visual description
        # Extract key visual elements, ignoring timing/technical notes
        base_prompt = self._extract_visual_elements(visual_text)
        logger.debug(f"Extracted visual elements: {base_prompt[:80]}...")

        # Add style prefix if provided
        if visual_style_prompt:
            full_prompt = f"{visual_style_prompt}, {base_prompt}"
            logger.debug(f"Added style prefix: {visual_style_prompt[:50]}...")
        else:
            full_prompt = base_prompt

        # Add cinematic quality keywords
        quality_suffix = "cinematic still, professional photography, high quality, detailed"
        full_prompt = f"{full_prompt}, {quality_suffix}"

        result = {
            "prompt": full_prompt,
            "negative_prompt": "blurry, low quality, amateur, distorted, watermark, text overlay",
            "source_visual": visual_text,
            "source_audio": audio_text,
        }

        # Optionally enhance with LLM
        if enhance and self.use_llm:
            logger.debug("Attempting LLM enhancement")
            try:
                enhancer = self._get_enhancer()
                if enhancer:
                    enhanced = enhancer.enhance_prompt(full_prompt)
                    result["prompt"] = enhanced.get("enhanced_prompt", full_prompt)
                    result["negative_prompt"] = enhanced.get(
                        "negative_prompt", result["negative_prompt"]
                    )
                    result["enhanced"] = True
                    logger.debug(
                        f"LLM enhancement successful, prompt length: {len(result['prompt'])}"
                    )
            except Exception as e:
                logger.warning(f"LLM enhancement failed, using base prompt: {e}")
                result["enhanced"] = False
        else:
            logger.debug("Skipping LLM enhancement (disabled)")
            result["enhanced"] = False

        return result

    def _extract_visual_elements(self, visual_text: str) -> str:
        """
        Extract key visual elements from script visual description.

        Removes timing notations, technical directions, and focuses on
        describable visual content.
        """
        # Remove common technical prefixes
        text = visual_text

        # Remove timing references like "00:00:05:00" or "(5.0s)"
        import re

        text = re.sub(r"\d{2}:\d{2}:\d{2}:\d{2}", "", text)
        text = re.sub(r"\(\d+\.?\d*s\)", "", text)

        # Remove shot type prefixes (these are useful context but not for image gen)
        # Keep them but normalize - they add context
        shot_types = ["CU", "MCU", "MS", "WS", "ECU", "EWS", "MWS", "POV", "OTS"]
        for shot in shot_types:
            text = re.sub(rf"\b{shot}\b[:\s]*", f"{shot}: ", text, flags=re.IGNORECASE)

        # Clean up extra whitespace
        text = " ".join(text.split())

        return text.strip()

    def generate_prompts_for_version(
        self,
        tv_spot_version,
        enhance: bool = True,
    ) -> list[dict]:
        """
        Generate prompts for all script rows in a TV spot version.

        Args:
            tv_spot_version: TvSpotVersion instance
            enhance: Whether to use LLM enhancement

        Returns:
            List of prompt dicts, one per script row
        """
        logger.debug(f"Generating prompts for version: {tv_spot_version.code}")
        prompts = []
        visual_style = tv_spot_version.visual_style_prompt or ""
        logger.debug(f"Visual style prompt: {visual_style[:50] if visual_style else '(none)'}...")

        script_rows = list(tv_spot_version.script_rows.all().order_by("order_index"))
        logger.debug(f"Processing {len(script_rows)} script rows")

        for idx, row in enumerate(script_rows):
            logger.debug(
                f"Generating prompt for row {idx + 1}/{len(script_rows)}: shot {row.shot_number}"
            )
            prompt_data = self.generate_prompt(
                visual_text=row.visual_text,
                audio_text=row.audio_text,
                visual_style_prompt=visual_style,
                enhance=enhance,
            )
            prompt_data["row_index"] = row.order_index
            prompt_data["shot_number"] = row.shot_number
            prompts.append(prompt_data)

        logger.info(f"Generated {len(prompts)} prompts for version {tv_spot_version.code}")
        return prompts


def create_storyboard_jobs(
    storyboard_job,
    prompts: list[dict],
) -> list:
    """
    Create DiffusionJobs and StoryboardImages for a storyboard job.

    Args:
        storyboard_job: StoryboardJob instance
        prompts: List of prompt dicts from generate_prompts_for_version

    Returns:
        List of created DiffusionJob instances
    """
    from cw.diffusion.models import (
        DiffusionJob,
        Prompt,
        StoryboardImage,
    )

    tv_spot_version = storyboard_job.tv_spot_version
    tv_spot = tv_spot_version.tv_spot
    diffusion_model = storyboard_job.diffusion_model
    lora_model = storyboard_job.lora_model
    images_per_row = storyboard_job.images_per_row

    created_jobs = []
    script_rows = {row.order_index: row for row in tv_spot_version.script_rows.all()}

    for prompt_data in prompts:
        row_index = prompt_data["row_index"]
        shot_number = prompt_data.get("shot_number", f"{row_index + 1:02d}")
        script_row = script_rows.get(row_index)

        if not script_row:
            logger.warning(f"Script row {row_index} not found, skipping")
            continue

        for img_idx in range(images_per_row):
            # Create identifier: {job_id}_{version_code}_row-{NN}_img-{NN}
            identifier = (
                f"{tv_spot.job_id}_{tv_spot_version.code}_row-{shot_number}_img-{img_idx + 1:02d}"
            )

            # Create Prompt record
            prompt_record = Prompt.objects.create(
                source_prompt=prompt_data["prompt"],
                enhanced_prompt=prompt_data["prompt"],  # Already enhanced if using LLM
                negative_prompt=prompt_data.get("negative_prompt", ""),
                enhancement_method="huggingface" if prompt_data.get("enhanced") else "none",
            )

            # Create DiffusionJob with 16:9 storyboard dimensions
            diffusion_job = DiffusionJob.objects.create(
                diffusion_model=diffusion_model,
                lora_model=lora_model,
                prompt=prompt_record,
                identifier=identifier,
                status="pending",
                width=1280,
                height=720,
            )

            # Create StoryboardImage link
            StoryboardImage.objects.create(
                storyboard_job=storyboard_job,
                script_row=script_row,
                diffusion_job=diffusion_job,
                image_index=img_idx,
            )

            created_jobs.append(diffusion_job)

            logger.info(
                f"Created DiffusionJob for storyboard: {identifier}",
                extra={
                    "storyboard_job_id": storyboard_job.pk,
                    "diffusion_job_id": diffusion_job.pk,
                    "row_index": row_index,
                    "image_index": img_idx,
                },
            )

    return created_jobs
