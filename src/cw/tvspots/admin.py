"""
Django admin configuration for TV spots.

Uses Django Unfold for tabs, display decorators, and styled actions.
"""

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .models import (
    AdaptationJob,
    AdaptationMarket,
    StoryboardImage,
    StoryboardJob,
    TvSpot,
    TvSpotScriptRow,
    TvSpotVersion,
)

# ---------------------------------------------------------------------------
# AdaptationMarket
# ---------------------------------------------------------------------------


@admin.register(AdaptationMarket)
class AdaptationMarketAdmin(ModelAdmin):
    list_display = ["name", "code", "default_language", "show_active", "show_versions_count", "updated_at"]
    list_filter = ["is_active", "default_language"]
    search_fields = ["name", "code", "rules"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["default_language"]

    fieldsets = (
        (
            _("Market"),
            {
                "classes": ["tab"],
                "fields": ("name", "code", "default_language", "is_active"),
            },
        ),
        (
            _("Rules"),
            {
                "classes": ["tab"],
                "fields": ("rules",),
            },
        ),
        (
            _("Metadata"),
            {
                "classes": ["tab"],
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active

    @display(description=_("Versions"))
    def show_versions_count(self, obj):
        count = obj.versions.count()
        if count > 0:
            url = reverse("admin:tvspots_tvspotversion_changelist")
            return format_html(
                '<a href="{}?market__id__exact={}">{}</a>',
                url,
                obj.id,
                count,
            )
        return "0"


# ---------------------------------------------------------------------------
# AdaptationJob
# ---------------------------------------------------------------------------


@admin.register(AdaptationJob)
class AdaptationJobAdmin(ModelAdmin):
    list_display = [
        "show_id",
        "show_tvspot",
        "target_market",
        "show_language",
        "show_pipeline",
        "show_status",
        "created_at",
        "completed_at",
    ]
    list_filter = ["status", "use_pipeline", "target_market", "created_at"]
    search_fields = ["tv_spot__script_title", "target_market__name", "error_message"]
    readonly_fields = [
        "tv_spot",
        "origin_version",
        "target_market",
        "language",
        "llm_model",
        "result_version",
        "status",
        "celery_task_id",
        "error_message",
        "created_at",
        "started_at",
        "completed_at",
        "concept_brief",
        "cultural_brief",
        "evaluation_history",
        "pipeline_metadata",
    ]

    fieldsets = (
        (
            _("Request"),
            {
                "classes": ["tab"],
                "fields": (
                    "tv_spot",
                    "origin_version",
                    "target_market",
                    ("language", "llm_model"),
                    "use_pipeline",
                ),
            },
        ),
        (
            _("Status"),
            {
                "classes": ["tab"],
                "fields": (
                    "status",
                    "celery_task_id",
                    "error_message",
                    "result_version",
                ),
            },
        ),
        (
            _("Timing"),
            {
                "classes": ["tab"],
                "fields": ("created_at", "started_at", "completed_at"),
            },
        ),
        (
            _("Concept Brief"),
            {
                "classes": ["tab"],
                "fields": ("concept_brief",),
                "description": "Output of the concept extraction pipeline node.",
            },
        ),
        (
            _("Cultural Brief"),
            {
                "classes": ["tab"],
                "fields": ("cultural_brief",),
                "description": "Output of the cultural research pipeline node.",
            },
        ),
        (
            _("Evaluation History"),
            {
                "classes": ["tab"],
                "fields": ("evaluation_history",),
                "description": "Chronological evaluation results from pipeline review nodes.",
            },
        ),
        (
            _("Pipeline Metadata"),
            {
                "classes": ["tab"],
                "fields": ("pipeline_metadata",),
                "description": "Models used, revision counts, and timing per pipeline phase.",
            },
        ),
    )

    @display(description=_("ID"))
    def show_id(self, obj):
        return f"#{obj.pk}"

    @display(description=_("TV Spot"))
    def show_tvspot(self, obj):
        return obj.tv_spot.script_title

    @display(description=_("Language"))
    def show_language(self, obj):
        lang = obj.effective_language
        return f"{lang.name} ({lang.code})" if lang else "—"

    @display(description=_("Pipeline"), boolean=True)
    def show_pipeline(self, obj):
        return obj.use_pipeline

    @display(
        description=_("Status"),
        label={
            "Pending": "info",
            "Processing": "warning",
            "Completed": "success",
            "Failed": "danger",
            "Concept Analysis": "warning",
            "Cultural Analysis": "warning",
            "Writing": "warning",
            "Cultural Evaluation": "warning",
            "Concept Evaluation": "warning",
            "Revising": "warning",
        },
    )
    def show_status(self, obj):
        return obj.get_status_display()


# ---------------------------------------------------------------------------
# TV Spot Inlines
# ---------------------------------------------------------------------------


class TvSpotScriptRowInline(TabularInline):
    """Inline display of script rows for TvSpotVersion."""

    model = TvSpotScriptRow
    tab = True
    extra = 0
    fields = [
        "shot_number",
        "timecode_start",
        "duration_seconds",
        "visual_text",
        "audio_text",
    ]
    ordering = ["order_index"]


class TvSpotVersionInline(TabularInline):
    """Inline display of versions for TvSpot."""

    model = TvSpotVersion
    tab = True
    extra = 0
    fields = ["code", "name", "version_type", "market", "language", "is_active"]
    readonly_fields = ["code", "name", "version_type", "market", "language"]
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class AdaptationJobInline(TabularInline):
    """Inline display of adaptation jobs for TvSpot."""

    model = AdaptationJob
    tab = True
    extra = 0
    fields = ["target_market", "show_pipeline", "show_status", "result_version", "created_at"]
    readonly_fields = ["target_market", "show_pipeline", "show_status", "result_version", "created_at"]
    can_delete = False
    show_change_link = True
    verbose_name = "Adaptation Request"
    verbose_name_plural = "Adaptation Requests"

    def has_add_permission(self, request, obj=None):
        return False

    @display(description=_("Pipeline"), boolean=True)
    def show_pipeline(self, obj):
        return obj.use_pipeline

    @display(
        description=_("Status"),
        label={
            "Pending": "info",
            "Processing": "warning",
            "Completed": "success",
            "Failed": "danger",
            "Concept Analysis": "warning",
            "Cultural Analysis": "warning",
            "Writing": "warning",
            "Cultural Evaluation": "warning",
            "Concept Evaluation": "warning",
            "Revising": "warning",
        },
    )
    def show_status(self, obj):
        return obj.get_status_display()


# ---------------------------------------------------------------------------
# TvSpot
# ---------------------------------------------------------------------------


@admin.register(TvSpot)
class TvSpotAdmin(ModelAdmin):
    list_display = [
        "script_title",
        "client_name",
        "brand_name",
        "job_id",
        "show_trt",
        "show_versions_count",
        "created_at",
    ]
    list_filter = ["client_name", "created_at"]
    search_fields = ["script_title", "client_name", "brand_name", "job_id"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [TvSpotVersionInline, AdaptationJobInline]
    actions_list = ["import_tvspot_action"]
    actions_detail = ["create_adaptation_action"]

    fieldsets = (
        (
            _("Project"),
            {
                "classes": ["tab"],
                "fields": (
                    ("client_name", "brand_name"),
                    ("script_title", "job_id"),
                    "total_runtime_seconds",
                ),
            },
        ),
        (
            _("Notes"),
            {
                "classes": ["tab"],
                "fields": ("notes",),
            },
        ),
        (
            _("Metadata"),
            {
                "classes": ["tab"],
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @display(description=_("TRT"))
    def show_trt(self, obj):
        return f"{obj.total_runtime_seconds}s"

    @display(description=_("Versions"))
    def show_versions_count(self, obj):
        count = obj.versions.count()
        if count > 0:
            url = reverse("admin:tvspots_tvspotversion_changelist")
            return format_html(
                '<a href="{}?tv_spot__id__exact={}">{}</a>',
                url,
                obj.id,
                count,
            )
        return "0"

    def get_urls(self):
        """Add custom URLs for import and adaptation actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_tvspot_view),
                name="tvspots_tvspot_import",
            ),
            path(
                "<int:object_id>/create-adaptation/",
                self.admin_site.admin_view(self.create_adaptation_view),
                name="tvspots_tvspot_create_adaptation",
            ),
            path(
                "api/language/<int:language_id>/models/",
                self.admin_site.admin_view(self.get_language_models_api),
                name="tvspots_tvspot_language_models_api",
            ),
        ]
        return custom_urls + urls

    def get_language_models_api(self, request, language_id):
        """AJAX endpoint to get models for a language."""
        from django.http import JsonResponse

        from cw.core.models import Language

        try:
            language = Language.objects.select_related("primary_model").prefetch_related(
                "alternative_models"
            ).get(pk=language_id)
        except Language.DoesNotExist:
            return JsonResponse({"error": "Language not found"}, status=404)

        models = [
            {
                "id": language.primary_model.id,
                "model_id": language.primary_model.model_id,
                "name": language.primary_model.name,
                "is_primary": True,
            }
        ]
        for alt in language.alternative_models.filter(is_active=True):
            models.append({
                "id": alt.id,
                "model_id": alt.model_id,
                "name": alt.name,
                "is_primary": False,
            })

        return JsonResponse({
            "language": {"id": language.id, "code": language.code, "name": language.name},
            "models": models,
        })

    def import_tvspot_view(self, request):
        """Handle importing a TV spot from JSON."""
        import json

        from django.db import transaction
        from django.template.response import TemplateResponse

        if request.method == "POST":
            json_data = request.POST.get("json_data", "").strip()

            if not json_data:
                messages.error(request, "JSON data is required.")
                return redirect("admin:tvspots_tvspot_import")

            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                messages.error(request, f"Invalid JSON: {e}")
                return redirect("admin:tvspots_tvspot_import")

            # Validate required fields
            errors = self._validate_tvspot_json(data)
            if errors:
                for error in errors:
                    messages.error(request, error)
                return redirect("admin:tvspots_tvspot_import")

            # Check for duplicate job_id
            job_id = data["job_id"]
            if TvSpot.objects.filter(job_id=job_id).exists():
                messages.error(request, f"TV Spot with job_id '{job_id}' already exists.")
                return redirect("admin:tvspots_tvspot_import")

            # Create records
            try:
                with transaction.atomic():
                    tv_spot = TvSpot.objects.create(
                        client_name=data["client_name"],
                        brand_name=data.get("brand_name", ""),
                        script_title=data["script_title"],
                        total_runtime_seconds=data["total_runtime_seconds"],
                        job_id=job_id,
                        notes=data.get("notes", ""),
                    )

                    version = TvSpotVersion.objects.create(
                        tv_spot=tv_spot,
                        version_type="origin",
                        code="ORIGIN",
                        name="Origin",
                        language=data.get("language", "en-US"),
                    )

                    for idx, row_data in enumerate(data["script_rows"]):
                        TvSpotScriptRow.objects.create(
                            tv_spot_version=version,
                            order_index=idx,
                            shot_number=row_data.get("shot_number", f"{idx + 1:02d}"),
                            timecode_start=row_data.get("timecode_start", ""),
                            duration_seconds=row_data.get("duration_seconds"),
                            visual_text=row_data["visual_text"],
                            audio_text=row_data["audio_text"],
                        )

                messages.success(
                    request,
                    f"Created TV Spot '{tv_spot.script_title}' with {len(data['script_rows'])} script rows.",
                )
                return redirect("admin:tvspots_tvspot_change", tv_spot.pk)

            except Exception as e:
                messages.error(request, f"Failed to create TV Spot: {e}")
                return redirect("admin:tvspots_tvspot_import")

        # Render import form
        return TemplateResponse(
            request,
            "admin/tvspots/tvspot/import_tvspot.html",
            {
                **self.admin_site.each_context(request),
                "title": _("Import TV Spot from JSON"),
                "opts": self.model._meta,
            },
        )

    def _validate_tvspot_json(self, data: dict) -> list:
        """Validate JSON against expected schema. Returns list of errors."""
        errors = []

        required = ["client_name", "script_title", "total_runtime_seconds", "job_id", "script_rows"]
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        if errors:
            return errors

        if not isinstance(data["script_rows"], list):
            errors.append("script_rows must be an array")
            return errors

        if len(data["script_rows"]) == 0:
            errors.append("script_rows must have at least one row")

        if not isinstance(data["total_runtime_seconds"], int) or data["total_runtime_seconds"] <= 0:
            errors.append("total_runtime_seconds must be a positive integer")

        for idx, row in enumerate(data["script_rows"]):
            if not isinstance(row, dict):
                errors.append(f"script_rows[{idx}] must be an object")
                continue
            if "visual_text" not in row or not row["visual_text"]:
                errors.append(f"script_rows[{idx}] missing or empty visual_text")
            if "audio_text" not in row or not row["audio_text"]:
                errors.append(f"script_rows[{idx}] missing or empty audio_text")

        return errors

    @action(
        description=_("Import TV Spot"),
        url_path="import-tvspot-action",
    )
    def import_tvspot_action(self, request):
        """Redirect to the import TV spot view."""
        return redirect("admin:tvspots_tvspot_import")

    @action(
        description=_("Create Adaptation"),
        url_path="create-adaptation-action",
        permissions=["create_adaptation_action"],
    )
    def create_adaptation_action(self, request, object_id):
        """Redirect to the create adaptation view."""
        return redirect("admin:tvspots_tvspot_create_adaptation", object_id)

    def has_create_adaptation_action_permission(self, request, object_id=None):
        """Only show button if there's an origin version."""
        if object_id:
            try:
                tv_spot = TvSpot.objects.get(pk=object_id)
                return tv_spot.versions.filter(version_type="origin").exists()
            except TvSpot.DoesNotExist:
                return False
        return False

    def create_adaptation_view(self, request, object_id):
        """Handle creating an adaptation of a TV spot."""
        from django.template.response import TemplateResponse

        from cw.core.models import Language, LLMModel

        from .tasks import create_adaptation_task

        tv_spot = TvSpot.objects.get(pk=object_id)
        origin_version = tv_spot.versions.filter(version_type="origin").first()

        if not origin_version:
            messages.error(request, "No origin version found for this TV spot.")
            return redirect("admin:tvspots_tvspot_change", object_id)

        if request.method == "POST":
            market_id = request.POST.get("market")
            language_id = request.POST.get("language")
            llm_model_id = request.POST.get("llm_model")
            use_pipeline = request.POST.get("use_pipeline") == "on"

            if not market_id:
                messages.error(request, "Please select a target market.")
                return redirect("admin:tvspots_tvspot_create_adaptation", object_id)

            market = AdaptationMarket.objects.get(pk=market_id)

            # Get optional language and model overrides
            language = None
            llm_model = None
            if language_id:
                language = Language.objects.filter(pk=language_id).first()
            if llm_model_id:
                llm_model = LLMModel.objects.filter(pk=llm_model_id).first()

            # Check if adaptation already exists for this market
            existing = tv_spot.versions.filter(market=market).first()
            if existing:
                messages.warning(
                    request, f"An adaptation for {market.name} already exists: {existing.name}"
                )
                return redirect("admin:tvspots_tvspotversion_change", existing.pk)

            # Check for pending/processing adaptation job for this market
            pending_job = tv_spot.adaptation_jobs.filter(
                target_market=market, status__in=["pending", "processing"]
            ).first()
            if pending_job:
                messages.warning(
                    request,
                    f"An adaptation to {market.name} is already in progress "
                    f"(status: {pending_job.get_status_display()}).",
                )
                return redirect("admin:tvspots_adaptationjob_change", pending_job.pk)

            # Create AdaptationJob to track the request
            adaptation_job = AdaptationJob.objects.create(
                tv_spot=tv_spot,
                origin_version=origin_version,
                target_market=market,
                language=language,
                llm_model=llm_model,
                use_pipeline=use_pipeline,
                status="pending",
            )

            # Queue the adaptation task with job ID
            result = create_adaptation_task.apply_async(
                args=[adaptation_job.pk], queue="enhancement"
            )

            # Store the Celery task ID
            adaptation_job.celery_task_id = result.id
            adaptation_job.save(update_fields=["celery_task_id"])

            messages.success(
                request,
                f"Adaptation to {market.name} queued for processing. "
                f"Track progress in the Adaptation Requests section below.",
            )
            return redirect("admin:tvspots_tvspot_change", object_id)

        # Get available markets (exclude markets with existing adaptations or pending jobs)
        existing_market_ids = tv_spot.versions.exclude(market__isnull=True).values_list(
            "market_id", flat=True
        )
        pending_market_ids = tv_spot.adaptation_jobs.filter(
            status__in=["pending", "processing"]
        ).values_list("target_market_id", flat=True)

        markets = AdaptationMarket.objects.filter(is_active=True).exclude(
            id__in=list(existing_market_ids) + list(pending_market_ids)
        ).select_related("default_language")

        # Get all active languages for the dropdown
        languages = Language.objects.filter(is_active=True).select_related("primary_model")

        existing_adaptations = tv_spot.versions.filter(version_type="adaptation").select_related(
            "market"
        )
        pending_jobs = tv_spot.adaptation_jobs.filter(
            status__in=["pending", "processing"]
        ).select_related("target_market")

        return TemplateResponse(
            request,
            "admin/tvspots/tvspot/create_adaptation.html",
            {
                **self.admin_site.each_context(request),
                "title": _("Create Adaptation"),
                "opts": self.model._meta,
                "tv_spot": tv_spot,
                "origin_version": origin_version,
                "markets": markets,
                "languages": languages,
                "existing_adaptations": existing_adaptations,
                "pending_jobs": pending_jobs,
            },
        )


# ---------------------------------------------------------------------------
# TvSpotVersion
# ---------------------------------------------------------------------------


@admin.register(TvSpotVersion)
class TvSpotVersionAdmin(ModelAdmin):
    list_display = [
        "show_title",
        "code",
        "name",
        "version_type",
        "market",
        "language",
        "show_rows_count",
        "show_active",
    ]
    list_filter = ["version_type", "market", "is_active", "tv_spot"]
    search_fields = ["code", "name", "tv_spot__script_title", "tv_spot__job_id"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [TvSpotScriptRowInline]
    actions_detail = ["view_storyboard_action", "generate_storyboard_action"]

    fieldsets = (
        (
            _("Version"),
            {
                "classes": ["tab"],
                "fields": (
                    "tv_spot",
                    ("version_type", "market"),
                    ("code", "name"),
                    "language",
                    "is_active",
                ),
            },
        ),
        (
            _("Visual Style"),
            {
                "classes": ["tab"],
                "fields": ("visual_style_prompt",),
            },
        ),
        (
            _("Metadata"),
            {
                "classes": ["tab"],
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @display(description=_("TV Spot"))
    def show_title(self, obj):
        return obj.tv_spot.script_title

    @display(description=_("Rows"))
    def show_rows_count(self, obj):
        return obj.script_rows.count()

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active

    def get_urls(self):
        """Add custom URLs for storyboard generation and viewing."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/generate-storyboard/",
                self.admin_site.admin_view(self.generate_storyboard_view),
                name="tvspots_tvspotversion_generate_storyboard",
            ),
            path(
                "<int:object_id>/storyboard/",
                self.admin_site.admin_view(self.storyboard_view),
                name="tvspots_tvspotversion_storyboard",
            ),
        ]
        return custom_urls + urls

    @action(
        description=_("View Storyboard"),
        url_path="view-storyboard-action",
        permissions=["view_storyboard_action"],
    )
    def view_storyboard_action(self, request, object_id):
        """Redirect to the storyboard viewer."""
        return redirect("admin:tvspots_tvspotversion_storyboard", object_id)

    def has_view_storyboard_action_permission(self, request, object_id=None):
        """Only show button if there are storyboard images."""
        if object_id:
            try:
                version = TvSpotVersion.objects.get(pk=object_id)
                # Check if there are any storyboard jobs with completed images
                return version.storyboard_jobs.filter(
                    images__diffusion_job__status="completed"
                ).exists()
            except TvSpotVersion.DoesNotExist:
                return False
        return False

    @action(
        description=_("Generate Storyboard"),
        url_path="generate-storyboard-action",
        permissions=["generate_storyboard_action"],
    )
    def generate_storyboard_action(self, request, object_id):
        """Redirect to the generate storyboard view."""
        return redirect("admin:tvspots_tvspotversion_generate_storyboard", object_id)

    def has_generate_storyboard_action_permission(self, request, object_id=None):
        """Only show button if there are script rows."""
        if object_id:
            try:
                version = TvSpotVersion.objects.get(pk=object_id)
                return version.script_rows.exists()
            except TvSpotVersion.DoesNotExist:
                return False
        return False

    def generate_storyboard_view(self, request, object_id):
        """Handle generating a storyboard for a TV spot version."""
        from django.template.response import TemplateResponse

        from cw.diffusion.models import DiffusionModel, LoraModel

        from .tasks import generate_storyboard_task

        version = TvSpotVersion.objects.get(pk=object_id)

        if not version.script_rows.exists():
            messages.error(request, "No script rows found for this version.")
            return redirect("admin:tvspots_tvspotversion_change", object_id)

        if request.method == "POST":
            model_id = request.POST.get("diffusion_model")
            lora_id = request.POST.get("lora_model") or None
            images_per_row = int(request.POST.get("images_per_row", 1))
            enhance_prompts = request.POST.get("enhance_prompts") == "on"

            if not model_id:
                messages.error(request, "Please select a diffusion model.")
                return redirect("admin:tvspots_tvspotversion_generate_storyboard", object_id)

            # Create StoryboardJob
            storyboard_job = StoryboardJob.objects.create(
                tv_spot_version=version,
                diffusion_model_id=model_id,
                lora_model_id=lora_id,
                images_per_row=images_per_row,
                status="pending",
            )

            # Queue the storyboard generation task
            generate_storyboard_task.apply_async(
                args=[storyboard_job.pk, enhance_prompts], queue="enhancement"
            )

            total_images = version.script_rows.count() * images_per_row
            messages.success(
                request,
                f"Storyboard generation queued ({total_images} images). "
                f"Check the Storyboard Jobs page for progress.",
            )
            return redirect("admin:tvspots_storyboardjob_change", storyboard_job.pk)

        # Get available models and LoRAs
        models = DiffusionModel.objects.filter(is_active=True)
        loras = LoraModel.objects.filter(is_active=True)

        existing_jobs = version.storyboard_jobs.all().select_related("diffusion_model")

        return TemplateResponse(
            request,
            "admin/tvspots/tvspotversion/generate_storyboard.html",
            {
                **self.admin_site.each_context(request),
                "title": _("Generate Storyboard"),
                "opts": self.model._meta,
                "version": version,
                "models": models,
                "loras": loras,
                "existing_jobs": existing_jobs,
                "lora_compat_url": reverse("admin:diffusion_diffusionjob_compatible_loras"),
            },
        )

    def storyboard_view(self, request, object_id):
        """Display the storyboard viewer for a TV spot version."""
        import os

        from django.conf import settings as django_settings
        from django.template.response import TemplateResponse

        version = TvSpotVersion.objects.get(pk=object_id)

        # Get the most recent storyboard job
        storyboard_job = version.storyboard_jobs.order_by("-created_at").first()

        # Build frame data from storyboard images
        frames = []
        completed_count = 0
        processing_count = 0
        pending_count = 0

        if storyboard_job:
            for image in (
                storyboard_job.images.all()
                .select_related("script_row", "diffusion_job")
                .order_by("script_row__order_index", "image_index")
            ):
                diffusion_job = image.diffusion_job
                script_row = image.script_row

                # Get image URL if completed
                image_url = None
                if diffusion_job.result_images:
                    # Get the first image path
                    img_path = diffusion_job.result_images[0]
                    image_url = os.path.join(django_settings.MEDIA_URL, img_path)

                # Track status counts
                if diffusion_job.status == "completed":
                    completed_count += 1
                elif diffusion_job.status == "processing":
                    processing_count += 1
                else:
                    pending_count += 1

                frames.append(
                    {
                        "shot_number": script_row.shot_number
                        or f"{script_row.order_index + 1:02d}",
                        "visual_text": script_row.visual_text,
                        "audio_text": script_row.audio_text,
                        "image_url": image_url,
                        "status": diffusion_job.status,
                        "image_index": image.image_index,
                    }
                )

        return TemplateResponse(
            request,
            "admin/tvspots/tvspotversion/storyboard_view.html",
            {
                **self.admin_site.each_context(request),
                "title": _("Storyboard"),
                "opts": self.model._meta,
                "version": version,
                "storyboard_job": storyboard_job,
                "frames": frames,
                "completed_count": completed_count,
                "processing_count": processing_count,
                "pending_count": pending_count,
            },
        )


# ---------------------------------------------------------------------------
# StoryboardJob
# ---------------------------------------------------------------------------


class StoryboardImageInline(TabularInline):
    """Inline display of images for StoryboardJob."""

    model = StoryboardImage
    tab = True
    extra = 0
    fields = ["script_row", "image_index", "diffusion_job", "show_status"]
    readonly_fields = ["script_row", "image_index", "diffusion_job", "show_status"]
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    @display(description=_("Status"))
    def show_status(self, obj):
        return obj.diffusion_job.get_status_display() if obj.diffusion_job else "—"


@admin.register(StoryboardJob)
class StoryboardJobAdmin(ModelAdmin):
    list_display = [
        "show_id",
        "show_version",
        "diffusion_model",
        "lora_model",
        "images_per_row",
        "show_status",
        "created_at",
    ]
    list_filter = ["status", "diffusion_model", "tv_spot_version__tv_spot"]
    search_fields = ["tv_spot_version__tv_spot__script_title", "tv_spot_version__code"]
    readonly_fields = ["created_at", "completed_at"]
    inlines = [StoryboardImageInline]

    fieldsets = (
        (
            _("Configuration"),
            {
                "classes": ["tab"],
                "fields": (
                    "tv_spot_version",
                    ("diffusion_model", "lora_model"),
                    "images_per_row",
                ),
            },
        ),
        (
            _("Status"),
            {
                "classes": ["tab"],
                "fields": ("status", "error_message"),
            },
        ),
        (
            _("Timing"),
            {
                "classes": ["tab"],
                "fields": ("created_at", "completed_at"),
            },
        ),
    )

    @display(description=_("ID"))
    def show_id(self, obj):
        return f"#{obj.pk}"

    @display(description=_("Version"))
    def show_version(self, obj):
        return f"{obj.tv_spot_version.tv_spot.script_title} / {obj.tv_spot_version.code}"

    @display(
        description=_("Status"),
        label={
            "Pending": "info",
            "Processing": "warning",
            "Completed": "success",
            "Failed": "danger",
        },
    )
    def show_status(self, obj):
        return obj.get_status_display()

    def save_model(self, request, obj, form, change):
        """Auto-queue new storyboard jobs on save."""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new and obj.status == "pending":
            from .tasks import generate_storyboard_task

            generate_storyboard_task.apply_async(
                args=[obj.pk, True], queue="enhancement"  # enhance_prompts=True by default
            )
