"""
Integration tests for wireframe storyboard generation.

Tests:
- WireframePromptBuilder prompt construction
- create_wireframe_storyboard_jobs linking keyframes → DiffusionJobs
- generate_wireframe_storyboard_task end-to-end (mocked diffusion)
- Error handling: no keyframes, no source media
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from cw.diffusion.models import ControlNetModel, DiffusionJob, DiffusionModel, Prompt
from cw.lib.storyboard import WireframePromptBuilder, create_wireframe_storyboard_jobs
from cw.tvspots.models import (
    AdUnitMedia,
    AdUnitScriptRow,
    Campaign,
    KeyFrame,
    Storyboard,
    StoryboardImage,
    VideoAdUnit,
    VideoProcessingResult,
)


class WireframePromptBuilderTestCase(TestCase):
    """Test WireframePromptBuilder prompt construction."""

    def test_default_style(self):
        """Uses DEFAULT_STYLE when no custom style_prompt given."""
        builder = WireframePromptBuilder()
        result = builder.build_prompt()
        self.assertIn("wireframe storyboard cel", result["prompt"])
        self.assertIn("negative_prompt", result)

    def test_custom_style(self):
        """Custom style_prompt replaces default."""
        builder = WireframePromptBuilder(style_prompt="anime sketch")
        result = builder.build_prompt()
        self.assertTrue(result["prompt"].startswith("anime sketch"))

    def test_visual_text_appended(self):
        """Optional visual_text is appended after style."""
        builder = WireframePromptBuilder(style_prompt="line art")
        result = builder.build_prompt(visual_text="woman holding product")
        self.assertIn("line art", result["prompt"])
        self.assertIn("woman holding product", result["prompt"])

    def test_empty_visual_text_omitted(self):
        """Empty visual_text doesn't add trailing comma."""
        builder = WireframePromptBuilder(style_prompt="line art")
        result = builder.build_prompt(visual_text="")
        self.assertEqual(result["prompt"], "line art")


class CreateWireframeStoryboardJobsTestCase(TestCase):
    """Test create_wireframe_storyboard_jobs creates correct DB records."""

    def setUp(self):
        """Set up a full object graph: Campaign → VideoAdUnit → AdUnitMedia → Result → KeyFrames."""
        self.campaign = Campaign.objects.create(
            job_id="WF-TEST-001",
            client_name="Test Client",
            script_title="Wireframe Test",
        )

        self.video_ad_unit = VideoAdUnit.objects.create(
            campaign=self.campaign,
            code="WF-ORIGIN",
            origin_or_adaptation="ORIGIN",
        )

        # Script rows matching keyframe scene numbers
        self.row1 = AdUnitScriptRow.objects.create(
            ad_unit=self.video_ad_unit,
            order_index=0,
            shot_number="1",
            visual_text="Wide shot of cityscape at sunrise",
            audio_text="Narrator: In a world of possibilities...",
        )
        self.row2 = AdUnitScriptRow.objects.create(
            ad_unit=self.video_ad_unit,
            order_index=1,
            shot_number="2",
            visual_text="Close-up of product on table",
            audio_text="VO: The new XPhone Pro",
        )

        # VideoProcessingResult with KeyFrames
        self.result = VideoProcessingResult.objects.create(
            scenes=[{"scene_number": 1}, {"scene_number": 2}],
            script={"scenes": []},
        )

        # Create fake keyframe images
        self._tmp_dir = tempfile.mkdtemp()
        for scene_num in [1, 2]:
            img_path = Path(self._tmp_dir) / f"scene_{scene_num:03d}.jpg"
            # Create a minimal valid JPEG (SOI + EOI markers)
            img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9")

        self.kf1 = KeyFrame.objects.create(
            result=self.result,
            scene_number=1,
            timestamp=1.5,
            image=SimpleUploadedFile("scene_001.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9", content_type="image/jpeg"),
        )
        self.kf2 = KeyFrame.objects.create(
            result=self.result,
            scene_number=2,
            timestamp=4.2,
            image=SimpleUploadedFile("scene_002.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9", content_type="image/jpeg"),
        )

        # AdUnitMedia links VideoAdUnit → VideoProcessingResult
        self.media = AdUnitMedia.objects.create(
            campaign=self.campaign,
            video_file=SimpleUploadedFile("test.mp4", b"fake-mp4"),
            video_ad_unit=self.video_ad_unit,
            result=self.result,
            status="completed",
        )

        # Diffusion model for storyboard
        self.diffusion_model = DiffusionModel.objects.create(
            label="Test SDXL",
            slug="test-sdxl",
            path="test/sdxl-base",
            pipeline="StableDiffusionXLControlNetPipeline",
            base_architecture="sdxl",
        )

        # ControlNet model
        self.controlnet = ControlNetModel.objects.create(
            label="Test ControlNet Canny",
            slug="test-cn-canny",
            path="test/controlnet-canny",
            control_type="canny",
            base_architecture="sdxl",
            default_conditioning_scale=0.5,
            default_guidance_end=0.8,
        )

        # Create storyboard with keyframe source type
        self.storyboard = Storyboard.objects.create(
            video_ad_unit=self.video_ad_unit,
            diffusion_model=self.diffusion_model,
            source_type="keyframe",
            controlnet_model=self.controlnet,
            images_per_row=1,
        )

    def test_creates_diffusion_jobs_for_each_keyframe(self):
        """One DiffusionJob per keyframe (with images_per_row=1)."""
        jobs = create_wireframe_storyboard_jobs(self.storyboard)
        self.assertEqual(len(jobs), 2)

    def test_diffusion_job_has_controlnet_settings(self):
        """DiffusionJobs use storyboard's ControlNet settings."""
        jobs = create_wireframe_storyboard_jobs(self.storyboard)
        job = jobs[0]
        self.assertEqual(job.controlnet_model, self.controlnet)
        self.assertEqual(job.preprocessing_type, "canny")
        self.assertEqual(job.conditioning_scale, 0.5)
        self.assertEqual(job.control_guidance_end, 0.8)

    def test_storyboard_overrides_controlnet_defaults(self):
        """Storyboard-level overrides take precedence over ControlNet defaults."""
        self.storyboard.conditioning_scale = 1.2
        self.storyboard.control_guidance_end = 0.6
        self.storyboard.preprocessing_type = "lineart"
        self.storyboard.save()

        jobs = create_wireframe_storyboard_jobs(self.storyboard)
        job = jobs[0]
        self.assertEqual(job.conditioning_scale, 1.2)
        self.assertEqual(job.control_guidance_end, 0.6)
        self.assertEqual(job.preprocessing_type, "lineart")

    def test_creates_storyboard_images_with_key_frame_link(self):
        """StoryboardImage records link to their source KeyFrame."""
        create_wireframe_storyboard_jobs(self.storyboard)
        images = StoryboardImage.objects.filter(storyboard=self.storyboard)
        self.assertEqual(images.count(), 2)

        # Check key_frame FK is set
        for img in images:
            self.assertIsNotNone(img.key_frame)

    def test_identifier_format(self):
        """DiffusionJob identifiers follow wireframe naming convention."""
        jobs = create_wireframe_storyboard_jobs(self.storyboard)
        self.assertIn("_wf-", jobs[0].identifier)
        self.assertTrue(jobs[0].identifier.startswith("WF-TEST-001_WF-ORIGIN"))

    def test_prompt_records_created(self):
        """Each DiffusionJob has a linked Prompt with wireframe style text."""
        jobs = create_wireframe_storyboard_jobs(self.storyboard)
        for job in jobs:
            self.assertIsNotNone(job.prompt)
            self.assertIn("wireframe", job.prompt.source_prompt.lower())

    def test_images_per_row_multiplier(self):
        """images_per_row > 1 creates multiple jobs per keyframe."""
        self.storyboard.images_per_row = 3
        self.storyboard.save()

        jobs = create_wireframe_storyboard_jobs(self.storyboard)
        # 2 keyframes * 3 images_per_row = 6 jobs
        self.assertEqual(len(jobs), 6)

    def test_skips_keyframes_without_matching_script_row(self):
        """Keyframes with no matching script row are skipped."""
        # Add a keyframe for scene 99 (no matching script row)
        KeyFrame.objects.create(
            result=self.result,
            scene_number=99,
            timestamp=10.0,
            image=SimpleUploadedFile("scene_099.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9", content_type="image/jpeg"),
        )

        jobs = create_wireframe_storyboard_jobs(self.storyboard)
        # Still only 2 jobs (scene 99 has no script row)
        self.assertEqual(len(jobs), 2)

    def test_reference_image_copied_from_keyframe(self):
        """DiffusionJob.reference_image is populated from KeyFrame.image."""
        jobs = create_wireframe_storyboard_jobs(self.storyboard)
        for job in jobs:
            job.refresh_from_db()
            self.assertTrue(job.reference_image, f"Job {job.identifier} has no reference_image")

    def test_raises_when_no_source_media(self):
        """Raises ValueError if VideoAdUnit has no source_media."""
        # Delete the media link
        self.media.delete()

        with self.assertRaises(ValueError) as ctx:
            create_wireframe_storyboard_jobs(self.storyboard)
        self.assertIn("no source media", str(ctx.exception).lower())

    def test_raises_when_no_keyframes(self):
        """Raises ValueError if no keyframes exist."""
        KeyFrame.objects.all().delete()

        with self.assertRaises(ValueError) as ctx:
            create_wireframe_storyboard_jobs(self.storyboard)
        self.assertIn("no keyframes", str(ctx.exception).lower())

    def test_custom_style_prompt_used(self):
        """Storyboard.style_prompt overrides default wireframe style."""
        self.storyboard.style_prompt = "anime cel shading, bold outlines"
        self.storyboard.save()

        jobs = create_wireframe_storyboard_jobs(self.storyboard)
        self.assertIn("anime cel shading", jobs[0].prompt.source_prompt)


class WireframeStoryboardTaskTestCase(TestCase):
    """Test generate_wireframe_storyboard_task end-to-end (mocked diffusion)."""

    def setUp(self):
        """Set up full object graph for the task."""
        self.campaign = Campaign.objects.create(
            job_id="WF-TASK-001",
            client_name="Task Client",
            script_title="Task Test",
        )

        self.video_ad_unit = VideoAdUnit.objects.create(
            campaign=self.campaign,
            code="WF-TASK-ORIGIN",
            origin_or_adaptation="ORIGIN",
        )

        AdUnitScriptRow.objects.create(
            ad_unit=self.video_ad_unit,
            order_index=0,
            shot_number="1",
            visual_text="Product hero shot",
        )

        self.result = VideoProcessingResult.objects.create(
            scenes=[{"scene_number": 1}],
            script={"scenes": []},
        )

        KeyFrame.objects.create(
            result=self.result,
            scene_number=1,
            timestamp=2.0,
            image=SimpleUploadedFile("scene_001.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9", content_type="image/jpeg"),
        )

        AdUnitMedia.objects.create(
            campaign=self.campaign,
            video_file=SimpleUploadedFile("test.mp4", b"fake-mp4"),
            video_ad_unit=self.video_ad_unit,
            result=self.result,
            status="completed",
        )

        self.diffusion_model = DiffusionModel.objects.create(
            label="Test SDXL CN",
            slug="test-sdxl-cn-task",
            path="test/sdxl-base",
            pipeline="StableDiffusionXLControlNetPipeline",
            base_architecture="sdxl",
        )

        self.controlnet = ControlNetModel.objects.create(
            label="Test ControlNet Task",
            slug="test-cn-task",
            path="test/controlnet-canny",
            control_type="canny",
            base_architecture="sdxl",
            default_conditioning_scale=0.5,
            default_guidance_end=0.8,
        )

        self.storyboard = Storyboard.objects.create(
            video_ad_unit=self.video_ad_unit,
            diffusion_model=self.diffusion_model,
            source_type="keyframe",
            controlnet_model=self.controlnet,
            images_per_row=1,
        )

    @patch("cw.tvspots.tasks.generate_images_task")
    @patch("cw.tvspots.tasks._evict_pipeline_model")
    def test_task_creates_jobs_and_queues(self, mock_evict, mock_gen_task):
        """Task creates DiffusionJobs and queues them for image generation."""
        from cw.tvspots.tasks import generate_wireframe_storyboard_task

        result = generate_wireframe_storyboard_task(None, self.storyboard.pk)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["num_jobs"], 1)
        self.assertTrue(mock_evict.called)
        self.assertTrue(mock_gen_task.apply_async.called)

    @patch("cw.tvspots.tasks.generate_images_task")
    @patch("cw.tvspots.tasks._evict_pipeline_model")
    def test_task_updates_storyboard_status(self, mock_evict, mock_gen_task):
        """Task updates storyboard status to completed."""
        from cw.tvspots.tasks import generate_wireframe_storyboard_task

        generate_wireframe_storyboard_task(None, self.storyboard.pk)

        self.storyboard.refresh_from_db()
        self.assertEqual(self.storyboard.status, "completed")
        self.assertIsNotNone(self.storyboard.completed_at)

    @patch("cw.tvspots.tasks.generate_images_task")
    @patch("cw.tvspots.tasks._evict_pipeline_model")
    def test_task_sets_failed_on_error(self, mock_evict, mock_gen_task):
        """Task catches exceptions and sets storyboard status to failed."""
        from cw.tvspots.tasks import generate_wireframe_storyboard_task

        # Delete keyframes to trigger ValueError
        KeyFrame.objects.all().delete()

        result = generate_wireframe_storyboard_task(None, self.storyboard.pk)

        self.assertEqual(result["status"], "failed")
        self.storyboard.refresh_from_db()
        self.assertEqual(self.storyboard.status, "failed")
        self.assertIn("No keyframes", self.storyboard.error_message)

    @patch("cw.tvspots.tasks.generate_images_task")
    @patch("cw.tvspots.tasks._evict_pipeline_model")
    def test_task_queues_jobs_to_default_queue(self, mock_evict, mock_gen_task):
        """DiffusionJobs are queued to the 'default' Celery queue."""
        from cw.tvspots.tasks import generate_wireframe_storyboard_task

        generate_wireframe_storyboard_task(None, self.storyboard.pk)

        call_kwargs = mock_gen_task.apply_async.call_args
        self.assertEqual(call_kwargs.kwargs.get("queue", call_kwargs[1].get("queue")), "default")
