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
        video_ad_unit,
        enhance: bool = True,
    ) -> list[dict]:
        """
        Generate prompts for all script rows in a video ad unit.

        Args:
            video_ad_unit: VideoAdUnit instance
            enhance: Whether to use LLM enhancement

        Returns:
            List of prompt dicts, one per script row
        """
        logger.debug(f"Generating prompts for video ad unit: {video_ad_unit.code}")
        prompts = []
        visual_style = video_ad_unit.visual_style_prompt or ""
        logger.debug(f"Visual style prompt: {visual_style[:50] if visual_style else '(none)'}...")

        script_rows = list(video_ad_unit.script_rows.all().order_by("order_index"))
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

        logger.info(f"Generated {len(prompts)} prompts for video ad unit {video_ad_unit.code}")
        return prompts


def create_storyboard_jobs(
    storyboard,
    prompts: list[dict],
) -> list:
    """
    Create DiffusionJobs and StoryboardImages for a storyboard.

    Args:
        storyboard: Storyboard instance
        prompts: List of prompt dicts from generate_prompts_for_version

    Returns:
        List of created DiffusionJob instances
    """
    from cw.diffusion.models import DiffusionJob, Prompt
    from cw.tvspots.models import StoryboardImage

    video_ad_unit = storyboard.video_ad_unit
    campaign = video_ad_unit.campaign
    diffusion_model = storyboard.diffusion_model
    lora_model = storyboard.lora_model
    images_per_row = storyboard.images_per_row

    created_jobs = []
    script_rows = {row.order_index: row for row in video_ad_unit.script_rows.all()}

    for prompt_data in prompts:
        row_index = prompt_data["row_index"]
        shot_number = prompt_data.get("shot_number", f"{row_index + 1:02d}")
        script_row = script_rows.get(row_index)

        if not script_row:
            logger.warning(f"Script row {row_index} not found, skipping")
            continue

        for img_idx in range(images_per_row):
            # Create identifier: {job_id}_{ad_unit_code}_row-{NN}_img-{NN}
            identifier = (
                f"{campaign.job_id}_{video_ad_unit.code}_row-{shot_number}_img-{img_idx + 1:02d}"
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
                storyboard=storyboard,
                script_row=script_row,
                diffusion_job=diffusion_job,
                image_index=img_idx,
            )

            created_jobs.append(diffusion_job)

            logger.info(
                f"Created DiffusionJob for storyboard: {identifier}",
                extra={
                    "storyboard_id": storyboard.pk,
                    "diffusion_job_id": diffusion_job.pk,
                    "row_index": row_index,
                    "image_index": img_idx,
                },
            )

    return created_jobs


class WireframePromptBuilder:
    """Builds image prompts for wireframe/line-drawing storyboard generation.

    Unlike :class:`StoryboardGenerator` which creates prompts from script text,
    this builder creates simple style-focused prompts designed to work with
    ControlNet structural guidance from video keyframes.
    """

    DEFAULT_STYLE = (
        "clean line drawing, wireframe storyboard cel, black and white, "
        "professional illustration, architectural sketch style"
    )
    DEFAULT_NEGATIVE = (
        "photorealistic, photograph, blurry, low quality, watermark, "
        "text overlay, color photograph, 3D render"
    )

    def __init__(self, style_prompt: str = ""):
        """
        Args:
            style_prompt: Custom style prompt. Falls back to DEFAULT_STYLE if empty.
        """
        self.style_prompt = style_prompt or self.DEFAULT_STYLE

    def build_prompt(
        self,
        visual_text: str = "",
        scene_number: int | None = None,
    ) -> dict:
        """Build a wireframe generation prompt for a single keyframe.

        The prompt emphasises the desired visual *style* rather than content
        description — the content comes from the ControlNet reference image.

        Args:
            visual_text: Optional script-row description for extra context.
            scene_number: Optional scene number for logging.

        Returns:
            Dict with ``prompt`` and ``negative_prompt`` keys.
        """
        parts = [self.style_prompt]
        if visual_text:
            # Add a short content hint from the script
            parts.append(visual_text.strip())
        prompt = ", ".join(parts)

        logger.debug(
            f"Built wireframe prompt for scene {scene_number}: {prompt[:80]}..."
        )
        return {
            "prompt": prompt,
            "negative_prompt": self.DEFAULT_NEGATIVE,
        }


def create_wireframe_storyboard_jobs(storyboard) -> list:
    """Create ControlNet-guided DiffusionJobs from video keyframes.

    Matches keyframes (by ``scene_number``) to script rows and creates one
    :class:`~cw.diffusion.models.DiffusionJob` per keyframe per ``images_per_row``.
    Each DiffusionJob is configured with the storyboard's ControlNet settings
    and the keyframe image as the reference input.

    Args:
        storyboard: :class:`~cw.tvspots.models.Storyboard` with
            ``source_type="keyframe"`` and a ``controlnet_model`` set.

    Returns:
        List of created :class:`~cw.diffusion.models.DiffusionJob` instances.

    Raises:
        ValueError: If the VideoAdUnit has no source media or keyframes.
    """
    from django.core.files import File

    from cw.diffusion.models import DiffusionJob, Prompt
    from cw.tvspots.models import StoryboardImage

    video_ad_unit = storyboard.video_ad_unit
    campaign = video_ad_unit.campaign

    # Resolve ControlNet settings with fallback to model defaults
    controlnet = storyboard.controlnet_model
    preprocessing = (
        storyboard.preprocessing_type or controlnet.control_type
    )
    cond_scale = (
        storyboard.conditioning_scale
        if storyboard.conditioning_scale is not None
        else controlnet.default_conditioning_scale
    )
    guidance_end = (
        storyboard.control_guidance_end
        if storyboard.control_guidance_end is not None
        else controlnet.default_guidance_end
    )

    # Get keyframes via VideoAdUnit → source_media → result → key_frames
    source_media = getattr(video_ad_unit, "source_media", None)
    if not source_media or not source_media.result:
        raise ValueError(
            f"VideoAdUnit {video_ad_unit.code} has no source media with "
            "processing results. Upload and process a video first."
        )

    key_frames = list(
        source_media.result.key_frames.all().order_by("scene_number")
    )
    if not key_frames:
        raise ValueError(
            f"No keyframes found for VideoAdUnit {video_ad_unit.code}. "
            "Ensure video analysis completed successfully."
        )

    # Build scene_number → script_row mapping
    script_rows_by_scene = {}
    for row in video_ad_unit.script_rows.all():
        # shot_number often matches scene_number; fall back to order_index + 1
        try:
            scene_num = int(row.shot_number)
        except (ValueError, TypeError):
            scene_num = row.order_index + 1
        script_rows_by_scene[scene_num] = row

    prompt_builder = WireframePromptBuilder(style_prompt=storyboard.style_prompt)

    created_jobs = []

    for key_frame in key_frames:
        script_row = script_rows_by_scene.get(key_frame.scene_number)
        if not script_row:
            logger.warning(
                f"No script row for scene {key_frame.scene_number}, skipping keyframe"
            )
            continue

        visual_hint = script_row.visual_text if script_row else ""
        prompt_data = prompt_builder.build_prompt(
            visual_text=visual_hint,
            scene_number=key_frame.scene_number,
        )

        shot_number = script_row.shot_number or f"{script_row.order_index + 1:02d}"

        for img_idx in range(storyboard.images_per_row):
            identifier = (
                f"{campaign.job_id}_{video_ad_unit.code}"
                f"_wf-{shot_number}_img-{img_idx + 1:02d}"
            )

            prompt_record = Prompt.objects.create(
                source_prompt=prompt_data["prompt"],
                enhanced_prompt=prompt_data["prompt"],
                negative_prompt=prompt_data["negative_prompt"],
                enhancement_method="none",
            )

            # Create DiffusionJob with ControlNet settings and keyframe reference
            diffusion_job = DiffusionJob.objects.create(
                diffusion_model=storyboard.diffusion_model,
                lora_model=storyboard.lora_model,
                prompt=prompt_record,
                identifier=identifier,
                status="pending",
                width=1280,
                height=720,
                controlnet_model=controlnet,
                preprocessing_type=preprocessing,
                conditioning_scale=cond_scale,
                control_guidance_end=guidance_end,
            )

            # Copy the keyframe image to the DiffusionJob's reference_image field
            if key_frame.image:
                with open(key_frame.image.path, "rb") as f:
                    diffusion_job.reference_image.save(
                        f"ref_scene_{key_frame.scene_number:03d}.jpg",
                        File(f),
                        save=True,
                    )

            # Create StoryboardImage linking everything
            StoryboardImage.objects.create(
                storyboard=storyboard,
                script_row=script_row,
                diffusion_job=diffusion_job,
                key_frame=key_frame,
                image_index=img_idx,
            )

            created_jobs.append(diffusion_job)

            logger.info(
                f"Created wireframe DiffusionJob: {identifier}",
                extra={
                    "storyboard_id": storyboard.pk,
                    "diffusion_job_id": diffusion_job.pk,
                    "key_frame_id": key_frame.pk,
                    "scene_number": key_frame.scene_number,
                    "image_index": img_idx,
                },
            )

    logger.info(
        f"Created {len(created_jobs)} wireframe DiffusionJobs for storyboard {storyboard.pk}",
        extra={
            "storyboard_id": storyboard.pk,
            "num_jobs": len(created_jobs),
            "num_keyframes": len(key_frames),
        },
    )

    return created_jobs
