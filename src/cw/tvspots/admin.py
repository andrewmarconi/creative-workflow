"""
Django admin configuration for campaigns and video ad units.

Uses Django Unfold for tabs, display decorators, and styled actions.
"""

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from cw.core.widgets import InsightsEditorWidget, ScriptEditorWidget, VideoPlayerWidget

from .models import (
    AdUnitMedia,
    AdUnitScriptRow,
    Brand,
    Campaign,
    KeyFrame,
    Storyboard,
    StoryboardImage,
    VideoAdUnit,
    VideoProcessingResult,
)

# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ["name", "code", "show_active", "show_campaign_count", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "description", "guidelines"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            _("Brand"),
            {
                "classes": ["tab"],
                "fields": ("code", "name", "is_active"),
            },
        ),
        (
            _("Description"),
            {
                "classes": ["tab"],
                "fields": ("description",),
            },
        ),
        (
            _("Guidelines"),
            {
                "classes": ["tab"],
                "fields": ("guidelines",),
            },
        ),
        (
            _("Insights"),
            {
                "classes": ["tab"],
                "fields": ("insights",),
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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "insights":
            kwargs["widget"] = InsightsEditorWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active

    @display(description=_("Campaigns"))
    def show_campaign_count(self, obj):
        return obj.campaigns.count()


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


class AdUnitMediaInline(TabularInline):
    """Inline display of uploaded videos for Campaign."""

    model = AdUnitMedia
    tab = True
    extra = 1
    fields = ["video_file", "show_status", "show_metadata", "show_actions"]
    readonly_fields = ["show_status", "show_metadata", "show_actions"]
    show_change_link = True

    @display(
        description=_("Status"),
        label={
            "pending": "info",
            "uploaded": "info",
            "processing": "warning",
            "completed": "success",
            "failed": "danger",
            "reviewed": "success",
        },
    )
    def show_status(self, obj):
        if obj.pk:
            return obj.get_status_display()
        return "-"

    @display(description=_("Video Info"))
    def show_metadata(self, obj):
        if not obj.pk or not obj.duration:
            return "-"

        parts = []
        if obj.duration:
            parts.append(f"{obj.duration:.1f}s")
        if obj.resolution_width and obj.resolution_height:
            parts.append(f"{obj.resolution_width}×{obj.resolution_height}")
        if obj.file_size:
            # Convert bytes to MB
            size_mb = obj.file_size / (1024 * 1024)
            parts.append(f"{size_mb:.1f}MB")

        return " • ".join(parts) if parts else "-"

    @display(description=_("Actions"))
    def show_actions(self, obj):
        if not obj.pk:
            return "-"

        links = []

        # Link to processing result
        if obj.result_id:
            result_url = reverse("admin:tvspots_videoprocessingresult_change", args=[obj.result_id])
            links.append(format_html('<a href="{}">View Results</a>', result_url))

        # Link to created ad unit
        if obj.video_ad_unit_id:
            ad_unit_url = reverse("admin:tvspots_videoadunit_change", args=[obj.video_ad_unit_id])
            links.append(format_html('<a href="{}">View Ad Unit</a>', ad_unit_url))

        from django.utils.safestring import mark_safe
        return mark_safe(" • ".join(str(link) for link in links)) if links else "-"


class VideoAdUnitInline(TabularInline):
    """Inline display of ad units for Campaign."""

    model = VideoAdUnit
    tab = True
    extra = 0
    fields = ["code", "title", "origin_or_adaptation", "language", "show_status"]
    readonly_fields = ["code", "title", "origin_or_adaptation", "language", "show_status"]
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

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
            "Format Evaluation": "warning",
            "Cultural Evaluation": "warning",
            "Concept Evaluation": "warning",
            "Evaluating Brand": "warning",
            "Revising": "warning",
        },
    )
    def show_status(self, obj):
        return obj.get_status_display()


@admin.register(Campaign)
class CampaignAdmin(ModelAdmin):
    list_display = [
        "script_title",
        "client_name",
        "product_name",
        "job_id",
        "show_ad_units_count",
    ]
    list_filter = ["client_name", "brand"]
    search_fields = ["script_title", "client_name", "job_id"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [AdUnitMediaInline, VideoAdUnitInline]
    actions_list = ["import_campaign_action"]
    actions_detail = ["create_origin_ad_unit_action", "create_adaptation_action"]

    fieldsets = (
        (
            _("Project"),
            {
                "classes": ["tab"],
                "fields": (
                    ("client_name", "brand"),
                    ("product_name", "job_id"),
                    "script_title",
                ),
            },
        ),
        (
            _("Original Script Data"),
            {
                "classes": ["tab"],
                "fields": ("original_script_data",),
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

    @display(description=_("Ad Units"))
    def show_ad_units_count(self, obj):
        count = obj.ad_units.count()
        if count > 0:
            url = reverse("admin:tvspots_videoadunit_changelist")
            return format_html(
                '<a href="{}?campaign__id__exact={}">{}</a>',
                url,
                obj.id,
                count,
            )
        return "0"

    def save_formset(self, request, form, formset, change):
        """Handle saving inline formsets and auto-queue video processing."""
        # Only process AdUnitMedia formsets
        if formset.model != AdUnitMedia:
            super().save_formset(request, form, formset, change)
            return

        instances = formset.save(commit=False)

        # Track new AdUnitMedia instances with videos
        new_videos = []

        for instance in instances:
            # Check if this is a new AdUnitMedia with a video file
            if not instance.pk and instance.video_file:
                instance.status = "uploaded"
                instance.save()
                new_videos.append(instance)
            else:
                instance.save()

        # Save many-to-many relationships
        formset.save_m2m()

        # Delete any marked for deletion
        for obj in formset.deleted_objects:
            obj.delete()

        # Queue processing tasks for new videos
        if new_videos:
            from .tasks import analyze_video_task

            for media in new_videos:
                analyze_video_task.apply_async(args=[media.pk], queue="default")
                messages.info(
                    request,
                    f"Video processing queued for {media.video_file.name}",
                )

    def get_urls(self):
        """Add custom URLs for import, origin creation, and adaptation actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_campaign_view),
                name="tvspots_campaign_import",
            ),
            path(
                "<int:object_id>/create-origin/",
                self.admin_site.admin_view(self.create_origin_ad_unit_view),
                name="tvspots_campaign_create_origin",
            ),
            path(
                "<int:object_id>/create-adaptation/",
                self.admin_site.admin_view(self.create_adaptation_view),
                name="tvspots_campaign_create_adaptation",
            ),
            path(
                "language-models/<int:language_id>/",
                self.admin_site.admin_view(self.language_models_api),
                name="tvspots_campaign_language_models_api",
            ),
        ]
        return custom_urls + urls

    def import_campaign_view(self, request):
        """Handle importing a campaign from JSON."""
        import json

        from django.db import transaction
        from django.template.response import TemplateResponse

        if request.method == "POST":
            # Check for uploaded file first, then fallback to pasted JSON
            json_file = request.FILES.get("json_file")
            json_data = None

            if json_file:
                try:
                    json_data = json_file.read().decode("utf-8")
                except Exception as e:
                    messages.error(request, f"Error reading file: {e}")
                    return redirect("admin:tvspots_campaign_import")
            else:
                json_data = request.POST.get("json_data", "").strip()

            if not json_data:
                messages.error(request, "JSON data or file is required.")
                return redirect("admin:tvspots_campaign_import")

            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                messages.error(request, f"Invalid JSON: {e}")
                return redirect("admin:tvspots_campaign_import")

            # Validate required fields
            errors = self._validate_campaign_json(data)
            if errors:
                for error in errors:
                    messages.error(request, error)
                return redirect("admin:tvspots_campaign_import")

            # Check for duplicate job_id
            job_id = data["job_id"]
            if Campaign.objects.filter(job_id=job_id).exists():
                messages.error(request, f"Campaign with job_id '{job_id}' already exists.")
                return redirect("admin:tvspots_campaign_import")

            # Create records
            try:
                with transaction.atomic():
                    from cw.audiences.models import Language

                    # Lookup Language by code
                    language_code = data.get("language", "en-US")
                    try:
                        language = Language.objects.get(code=language_code)
                    except Language.DoesNotExist:
                        messages.error(
                            request,
                            f"Language '{language_code}' not found. Please create it first or use an existing language code.",
                        )
                        return redirect("admin:tvspots_campaign_import")

                    campaign = Campaign.objects.create(
                        client_name=data["client_name"],
                        product_name=data.get("product_name", ""),
                        script_title=data["script_title"],
                        job_id=job_id,
                        original_script_data=data,
                    )

                    video_ad_unit = VideoAdUnit.objects.create(
                        campaign=campaign,
                        origin_or_adaptation="ORIGIN",
                        code="ORIGIN",
                        title="Origin",
                        language=language,
                        status="completed",
                    )

                    for idx, row_data in enumerate(data["script_rows"]):
                        AdUnitScriptRow.objects.create(
                            ad_unit=video_ad_unit,
                            order_index=idx,
                            shot_number=row_data.get("shot_number", f"{idx + 1:02d}"),
                            timecode=row_data.get("timecode_start", ""),
                            visual_text=row_data["visual_text"],
                            audio_text=row_data["audio_text"],
                        )

                messages.success(
                    request,
                    f"Created Campaign '{campaign.script_title}' with {len(data['script_rows'])} script rows.",
                )
                return redirect("admin:tvspots_campaign_change", campaign.pk)

            except Exception as e:
                messages.error(request, f"Failed to create Campaign: {e}")
                return redirect("admin:tvspots_campaign_import")

        # Render import form
        return TemplateResponse(
            request,
            "admin/tvspots/campaign/import_campaign.html",
            {
                **self.admin_site.each_context(request),
                "title": _("Import Campaign from JSON"),
                "opts": self.model._meta,
            },
        )

    def _validate_campaign_json(self, data: dict) -> list:
        """Validate JSON against expected schema. Returns list of errors."""
        errors = []

        required = ["client_name", "script_title", "job_id", "script_rows"]
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
        description=_("Import Campaign"),
        url_path="import-campaign-action",
    )
    def import_campaign_action(self, request):
        """Redirect to the import campaign view."""
        return redirect("admin:tvspots_campaign_import")

    @action(
        description=_("Create Origin Ad Unit"),
        url_path="create-origin-ad-unit-action",
    )
    def create_origin_ad_unit_action(self, request, object_id):
        """Redirect to the create origin ad unit view."""
        return redirect("admin:tvspots_campaign_create_origin", object_id)

    def create_origin_ad_unit_view(self, request, object_id):
        """Handle creating an origin ad unit for a campaign."""
        import json

        from django.template.response import TemplateResponse

        from cw.audiences.models import Language

        campaign = Campaign.objects.get(pk=object_id)

        if request.method == "POST":
            from cw.audiences.models import Persona

            title = request.POST.get("title")
            code = request.POST.get("code")
            language_id = request.POST.get("language")
            brand_id = request.POST.get("brand")
            persona_id = request.POST.get("persona")
            script_data_raw = request.POST.get("script_data", "")

            # Validate required fields
            if not title or not code:
                messages.error(request, "Please provide both title and code.")
                return redirect("admin:tvspots_campaign_create_origin", object_id)

            # Get the dimension objects
            language = Language.objects.filter(pk=language_id).first() if language_id else None
            brand = Brand.objects.filter(pk=brand_id).first() if brand_id else campaign.brand
            persona = Persona.objects.filter(pk=persona_id).first() if persona_id else None

            # Parse script data if provided
            script_data = None
            if script_data_raw:
                try:
                    script_data = json.loads(script_data_raw)
                except json.JSONDecodeError:
                    messages.error(request, "Invalid JSON in script data.")
                    return redirect("admin:tvspots_campaign_create_origin", object_id)

            # Check for existing origin with same code
            existing_origin = campaign.ad_units.filter(
                origin_or_adaptation="ORIGIN",
                code=code
            ).first()
            if existing_origin:
                messages.warning(
                    request,
                    f"An origin ad unit with code '{code}' already exists.",
                )
                return redirect("admin:tvspots_videoadunit_change", existing_origin.pk)

            # Create VideoAdUnit for origin
            origin = VideoAdUnit.objects.create(
                campaign=campaign,
                origin_or_adaptation="ORIGIN",
                code=code,
                title=title,
                language=language,
                brand=brand,
                persona=persona,
                use_pipeline=False,  # Origins don't use pipeline
                status="draft",
            )

            # Create script rows if script data provided
            if script_data and "scenes" in script_data:
                for scene in script_data["scenes"]:
                    AdUnitScriptRow.objects.create(
                        ad_unit=origin,
                        shot_number=scene.get("scene_number", 0),
                        visual_description=scene.get("visual", ""),
                        audio_voiceover=scene.get("audio", {}).get("voiceover", ""),
                        audio_music=scene.get("audio", {}).get("music", ""),
                        audio_sfx=scene.get("audio", {}).get("sfx", ""),
                        notes=scene.get("action", ""),
                    )

            messages.success(
                request,
                f"Origin ad unit '{title}' created successfully.",
            )
            return redirect("admin:tvspots_videoadunit_change", origin.pk)

        # Get available dimensions
        from cw.audiences.models import Persona

        languages = Language.objects.filter(is_active=True).select_related("primary_model").order_by("name")
        brands = Brand.objects.filter(is_active=True).order_by("name")
        personas = Persona.objects.filter(is_active=True).order_by("name")

        return TemplateResponse(
            request,
            "admin/tvspots/campaign/create_origin.html",
            {
                **self.admin_site.each_context(request),
                "title": _("Create Origin Ad Unit"),
                "opts": self.model._meta,
                "campaign": campaign,
                "languages": languages,
                "brands": brands,
                "personas": personas,
                "campaign_brand_id": campaign.brand_id,
            },
        )

    @action(
        description=_("Create Adaptation"),
        url_path="create-adaptation-action",
        permissions=["create_adaptation_action"],
    )
    def create_adaptation_action(self, request, object_id):
        """Redirect to the create adaptation view."""
        return redirect("admin:tvspots_campaign_create_adaptation", object_id)

    def has_create_adaptation_action_permission(self, request, object_id=None):
        """Only show button if there's an origin video ad unit."""
        if object_id:
            try:
                campaign = Campaign.objects.get(pk=object_id)
                return campaign.ad_units.filter(origin_or_adaptation="ORIGIN").exists()
            except Campaign.DoesNotExist:
                return False
        return False

    def create_adaptation_view(self, request, object_id):
        """Handle creating an adaptation of a campaign."""
        import json

        from django.template.response import TemplateResponse

        from cw.audiences.models import Language
        from cw.core.models import LLMModel

        from .tasks import create_adaptation_task

        campaign = Campaign.objects.get(pk=object_id)
        origin_ad_unit = campaign.ad_units.filter(origin_or_adaptation="ORIGIN").first()

        if not origin_ad_unit:
            messages.error(request, "No origin ad unit found for this campaign.")
            return redirect("admin:tvspots_campaign_change", object_id)

        if request.method == "POST":
            from cw.audiences.models import Country, Persona, Region

            region_id = request.POST.get("region")
            country_id = request.POST.get("country")
            language_id = request.POST.get("language")
            llm_model_id = request.POST.get("llm_model")
            brand_id = request.POST.get("brand")
            persona_id = request.POST.get("persona")

            # Validate required fields
            if not region_id or not language_id:
                messages.error(request, "Please select a region and language.")
                return redirect("admin:tvspots_campaign_create_adaptation", object_id)

            # Get the dimension objects
            region = Region.objects.get(pk=region_id)
            country = Country.objects.filter(pk=country_id).first() if country_id else None
            language = Language.objects.get(pk=language_id)
            llm_model = LLMModel.objects.filter(pk=llm_model_id).first() if llm_model_id else None
            brand = Brand.objects.filter(pk=brand_id).first() if brand_id else None
            persona = Persona.objects.filter(pk=persona_id).first() if persona_id else None

            # Build per-node model config from form
            pipeline_model_config = {}
            node_keys = ["concept", "culture", "format_gate", "culture_gate", "concept_gate", "brand_gate"]
            for key in node_keys:
                model_pk = request.POST.get(f"model_{key}")
                if model_pk:
                    pipeline_model_config[key] = int(model_pk)

            # Check for pending/processing adaptation with same dimensions
            pending_adaptation = campaign.ad_units.filter(
                region=region,
                country=country,
                language=language,
                status__in=["pending", "processing"]
            ).first()
            if pending_adaptation:
                target_desc = f"{region.name}"
                if country:
                    target_desc += f" / {country.name}"
                target_desc += f" ({language.code})"
                messages.warning(
                    request,
                    f"An adaptation to {target_desc} is already in progress "
                    f"(status: {pending_adaptation.get_status_display()}).",
                )
                return redirect("admin:tvspots_videoadunit_change", pending_adaptation.pk)

            # Generate code for adaptation
            code_parts = []
            if country:
                code_parts.append(country.code.upper())
            elif region:
                code_parts.append(region.code.upper())
            code_parts.append(language.code.upper())
            code = "-".join(code_parts)

            # Generate title
            title_parts = []
            if country:
                title_parts.append(country.name)
            else:
                title_parts.append(region.name)
            title_parts.append(f"({language.code})")
            title = " ".join(title_parts)

            # Create VideoAdUnit for adaptation (always use pipeline)
            adaptation = VideoAdUnit.objects.create(
                campaign=campaign,
                origin_or_adaptation="ADAPTATION",
                code=code,
                title=title,
                region=region,
                country=country,
                language=language,
                llm_model=llm_model,
                brand=brand,
                persona=persona,
                pipeline_model_config=pipeline_model_config,
                source_ad_unit=origin_ad_unit,
                use_pipeline=True,  # Always use multi-agent pipeline
                status="pending",
            )

            # Queue the adaptation task
            result = create_adaptation_task.apply_async(
                args=[adaptation.pk], queue="default"
            )

            # Store the Celery task ID
            adaptation.celery_task_id = result.id
            adaptation.save(update_fields=["celery_task_id"])

            target_desc = f"{region.name}"
            if country:
                target_desc += f" / {country.name}"
            target_desc += f" ({language.code})"

            messages.success(
                request,
                f"Adaptation to {target_desc} queued for processing.",
            )
            return redirect("admin:tvspots_campaign_change", object_id)

        # Get available dimensions
        from cw.audiences.models import Country, CountryLanguage, CountryRegion, Persona, Region

        regions = Region.objects.filter(is_active=True).order_by("name")
        countries = Country.objects.filter(is_active=True).order_by("name")
        languages = Language.objects.filter(is_active=True).select_related("primary_model").order_by("name")
        brands = Brand.objects.filter(is_active=True).order_by("name")
        personas = Persona.objects.filter(is_active=True).order_by("name")
        llm_models = LLMModel.objects.filter(is_active=True).order_by("name")

        # Build region → countries mapping
        region_countries = {}
        for cr in CountryRegion.objects.select_related("region", "country"):
            if cr.region_id not in region_countries:
                region_countries[cr.region_id] = []
            region_countries[cr.region_id].append(cr.country_id)

        # Build country → languages mapping (with primary languages first)
        country_languages = {}
        for cl in CountryLanguage.objects.select_related("country", "language").order_by("-is_primary"):
            if cl.country_id not in country_languages:
                country_languages[cl.country_id] = []
            country_languages[cl.country_id].append(cl.language_id)

        # Get pending adaptations to show
        pending_adaptations = campaign.ad_units.filter(
            status__in=["pending", "processing"]
        ).select_related("region", "country", "language")

        # Node model fields for template iteration
        node_model_fields = [
            ("concept", _("Concept Analyst Model")),
            ("culture", _("Cultural Researcher Model")),
            ("format_gate", _("Format Gate Model")),
            ("culture_gate", _("Culture Gate Model")),
            ("concept_gate", _("Concept Gate Model")),
            ("brand_gate", _("Brand Gate Model")),
        ]

        return TemplateResponse(
            request,
            "admin/tvspots/campaign/create_adaptation.html",
            {
                **self.admin_site.each_context(request),
                "title": _("Create Adaptation"),
                "opts": self.model._meta,
                "campaign": campaign,
                "origin_ad_unit": origin_ad_unit,
                "regions": regions,
                "countries": countries,
                "languages": languages,
                "brands": brands,
                "personas": personas,
                "llm_models": llm_models,
                "campaign_brand_id": campaign.brand_id,
                "node_model_fields": node_model_fields,
                "pending_adaptations": pending_adaptations,
                "region_countries_json": json.dumps(region_countries),
                "country_languages_json": json.dumps(country_languages),
            },
        )

    def language_models_api(self, request, language_id):
        """API endpoint to fetch available LLM models for a language."""
        from django.http import JsonResponse

        from cw.audiences.models import Language
        from cw.core.models import LLMModel

        try:
            language = Language.objects.get(pk=language_id)
        except Language.DoesNotExist:
            return JsonResponse({"error": "Language not found"}, status=404)

        # Get primary model and alternative models
        models = []
        if language.primary_model:
            models.append({
                "id": language.primary_model.id,
                "name": language.primary_model.name,
                "is_primary": True,
            })

        # Add alternative models
        for alt_model in language.alternative_models.all():
            models.append({
                "id": alt_model.id,
                "name": alt_model.name,
                "is_primary": False,
            })

        return JsonResponse({"models": models})


# ---------------------------------------------------------------------------
# VideoAdUnit
# ---------------------------------------------------------------------------


class AdUnitScriptRowInline(TabularInline):
    """Inline display of script rows for VideoAdUnit."""

    model = AdUnitScriptRow
    tab = True
    extra = 0
    fields = [
        "shot_number",
        "timecode",
        "visual_text",
        "audio_text",
    ]
    ordering = ["order_index"]


@admin.register(VideoAdUnit)
class VideoAdUnitAdmin(ModelAdmin):
    list_display = [
        "show_id",
        "show_campaign",
        "code",
        "title",
        "origin_or_adaptation",
        "show_target",
        "show_pipeline",
        "show_pipeline_progress",
        "show_status",
    ]
    list_filter = ["origin_or_adaptation", "status", "use_pipeline", "region", "country", "language"]
    search_fields = ["campaign__script_title", "code", "title", "error_message"]
    readonly_fields = [
        "campaign",
        "ad_unit_type",
        "code",
        "title",
        "origin_or_adaptation",
        "persona",
        "region",
        "country",
        "language",
        "llm_model",
        "brand",
        "source_ad_unit",
        "status",
        "celery_task_id",
        "error_message",
        "created_at",
        "started_at",
        "completed_at",
        "updated_at",
        "concept_brief",
        "cultural_brief",
        "evaluation_history",
        "pipeline_metadata",
        "pipeline_model_config",
    ]
    inlines = [AdUnitScriptRowInline]
    actions_detail = ["view_storyboard_action", "generate_storyboard_action"]
    actions = ["retry_failed_adaptations"]

    fieldsets = (
        (
            _("Core"),
            {
                "classes": ["tab"],
                "fields": (
                    "campaign",
                    "ad_unit_type",
                    "origin_or_adaptation",
                    ("code", "title"),
                ),
            },
        ),
        (
            _("Adaptation Target"),
            {
                "classes": ["tab"],
                "fields": (
                    "source_ad_unit",
                    "persona",
                    ("region", "country"),
                    ("language", "llm_model"),
                    "brand",
                    "use_pipeline",
                ),
            },
        ),
        (
            _("Video Settings"),
            {
                "classes": ["tab"],
                "fields": (
                    "duration",
                    "visual_style_prompt",
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
                ),
            },
        ),
        (
            _("Timing"),
            {
                "classes": ["tab"],
                "fields": ("created_at", "started_at", "completed_at", "updated_at"),
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
                "fields": ("pipeline_metadata", "pipeline_model_config"),
                "description": "Models used, revision counts, and timing per pipeline phase.",
            },
        ),
    )

    @display(description=_("ID"))
    def show_id(self, obj):
        return f"#{obj.pk}"

    @display(description=_("Campaign"))
    def show_campaign(self, obj):
        return obj.campaign.script_title

    @display(description=_("Target"))
    def show_target(self, obj):
        if obj.origin_or_adaptation == "ORIGIN":
            return "—"
        parts = []
        if obj.region:
            parts.append(obj.region.name)
        if obj.country:
            parts.append(obj.country.name)
        if obj.language:
            parts.append(f"({obj.language.code})")
        return " / ".join(parts) if parts else "—"

    @display(description=_("Pipeline"), boolean=True)
    def show_pipeline(self, obj):
        return obj.use_pipeline

    @display(description=_("Progress"))
    def show_pipeline_progress(self, obj):
        """Display visual progress bar for pipeline stages."""
        # Only show for pipeline adaptations
        if not obj.use_pipeline or obj.origin_or_adaptation == "ORIGIN":
            return "—"

        # Define pipeline stages and their order
        stages = [
            ("pending", "Queue"),
            ("concept_analysis", "Concept"),
            ("cultural_analysis", "Culture"),
            ("writing", "Writer"),
            ("format_evaluation", "Format"),
            ("cultural_evaluation", "Review"),
            ("brand_evaluation", "Brand"),
            ("completed", "Done"),
        ]

        # Map status to stage index
        status_map = {
            "pending": 0,
            "processing": 0,
            "concept_analysis": 1,
            "cultural_analysis": 2,
            "writing": 3,
            "revising": 3,
            "format_evaluation": 4,
            "cultural_evaluation": 5,
            "concept_evaluation": 5,
            "brand_evaluation": 6,
            "completed": 7,
            "failed": -1,
        }

        current_stage = status_map.get(obj.status, 0)

        # Handle failed status
        if obj.status == "failed":
            return mark_safe(
                '<div class="pipeline-progress">'
                '<span class="stage failed">✗ Failed</span>'
                '</div>'
            )

        # Build progress bar HTML
        html_parts = ['<div class="pipeline-progress">']

        for idx, (stage_key, stage_label) in enumerate(stages):
            if idx < current_stage:
                css_class = "stage completed"
                icon = "✓"
            elif idx == current_stage:
                css_class = "stage active"
                icon = "●"
            else:
                css_class = "stage pending"
                icon = "○"

            html_parts.append(
                f'<span class="{css_class}" title="{stage_label}">{icon}</span>'
            )

            # Add connector between stages (except after last)
            if idx < len(stages) - 1:
                connector_class = "connector completed" if idx < current_stage else "connector"
                html_parts.append(f'<span class="{connector_class}">─</span>')

        html_parts.append('</div>')

        return mark_safe(''.join(html_parts))

    show_pipeline_progress.allow_tags = True

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
            "Format Evaluation": "warning",
            "Cultural Evaluation": "warning",
            "Concept Evaluation": "warning",
            "Evaluating Brand": "warning",
            "Revising": "warning",
        },
    )
    def show_status(self, obj):
        return obj.get_status_display()

    @action(description=_("Retry selected failed adaptations"))
    def retry_failed_adaptations(self, request, queryset):
        """Retry failed adaptation video ad units by creating new ones with same parameters."""
        from .tasks import create_adaptation_task

        failed_adaptations = queryset.filter(status="failed", origin_or_adaptation="ADAPTATION")
        if not failed_adaptations.exists():
            self.message_user(
                request,
                _("No failed adaptations selected. Please select adaptations with 'Failed' status."),
                level=messages.WARNING,
            )
            return

        retried_count = 0
        for adaptation in failed_adaptations:
            # Create new adaptation with same parameters
            new_adaptation = VideoAdUnit.objects.create(
                campaign=adaptation.campaign,
                origin_or_adaptation="ADAPTATION",
                code=adaptation.code,
                title=adaptation.title,
                region=adaptation.region,
                country=adaptation.country,
                language=adaptation.language,
                llm_model=adaptation.llm_model,
                source_ad_unit=adaptation.source_ad_unit,
                use_pipeline=adaptation.use_pipeline,
                status="pending",
            )

            # Queue the task
            task = create_adaptation_task.apply_async(
                args=[new_adaptation.pk],
                queue="default",
            )
            new_adaptation.celery_task_id = task.id
            new_adaptation.save(update_fields=["celery_task_id"])
            retried_count += 1

        self.message_user(
            request,
            _(f"Created {retried_count} new adaptation(s) from failed adaptations."),
            level=messages.SUCCESS,
        )

    def get_urls(self):
        """Add custom URLs for storyboard generation and viewing."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/generate-storyboard/",
                self.admin_site.admin_view(self.generate_storyboard_view),
                name="tvspots_videoadunit_generate_storyboard",
            ),
            path(
                "<int:object_id>/storyboard/",
                self.admin_site.admin_view(self.storyboard_view),
                name="tvspots_videoadunit_storyboard",
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
        return redirect("admin:tvspots_videoadunit_storyboard", object_id)

    def has_view_storyboard_action_permission(self, request, object_id=None):
        """Only show button if there are storyboard images."""
        if object_id:
            try:
                video_ad_unit = VideoAdUnit.objects.get(pk=object_id)
                # Check if there are any storyboards with completed images
                return video_ad_unit.storyboards.filter(
                    images__diffusion_job__status="completed"
                ).exists()
            except VideoAdUnit.DoesNotExist:
                return False
        return False

    @action(
        description=_("Generate Storyboard"),
        url_path="generate-storyboard-action",
        permissions=["generate_storyboard_action"],
    )
    def generate_storyboard_action(self, request, object_id):
        """Redirect to the generate storyboard view."""
        return redirect("admin:tvspots_videoadunit_generate_storyboard", object_id)

    def has_generate_storyboard_action_permission(self, request, object_id=None):
        """Only show button if there are script rows."""
        if object_id:
            try:
                video_ad_unit = VideoAdUnit.objects.get(pk=object_id)
                return video_ad_unit.script_rows.exists()
            except VideoAdUnit.DoesNotExist:
                return False
        return False

    def generate_storyboard_view(self, request, object_id):
        """Handle generating a storyboard for a video ad unit."""
        from django.template.response import TemplateResponse

        from cw.diffusion.models import DiffusionModel, LoraModel

        from .tasks import generate_storyboard_task

        video_ad_unit = VideoAdUnit.objects.get(pk=object_id)

        if not video_ad_unit.script_rows.exists():
            messages.error(request, "No script rows found for this video ad unit.")
            return redirect("admin:tvspots_videoadunit_change", object_id)

        if request.method == "POST":
            model_id = request.POST.get("diffusion_model")
            lora_id = request.POST.get("lora_model") or None
            images_per_row = int(request.POST.get("images_per_row", 1))
            enhance_prompts = request.POST.get("enhance_prompts") == "on"

            if not model_id:
                messages.error(request, "Please select a diffusion model.")
                return redirect("admin:tvspots_videoadunit_generate_storyboard", object_id)

            # Create Storyboard
            storyboard = Storyboard.objects.create(
                video_ad_unit=video_ad_unit,
                diffusion_model_id=model_id,
                lora_model_id=lora_id,
                images_per_row=images_per_row,
                status="pending",
            )

            # Queue the storyboard generation task
            generate_storyboard_task.apply_async(
                args=[storyboard.pk, enhance_prompts], queue="default"
            )

            total_images = video_ad_unit.script_rows.count() * images_per_row
            messages.success(
                request,
                f"Storyboard generation queued ({total_images} images). "
                f"Check the Storyboard page for progress.",
            )
            return redirect("admin:tvspots_storyboard_change", storyboard.pk)

        # Get available models and LoRAs
        models = DiffusionModel.objects.filter(is_active=True)
        loras = LoraModel.objects.filter(is_active=True)

        existing_storyboards = video_ad_unit.storyboards.all().select_related("diffusion_model")

        return TemplateResponse(
            request,
            "admin/tvspots/videoadunit/generate_storyboard.html",
            {
                **self.admin_site.each_context(request),
                "title": _("Generate Storyboard"),
                "opts": self.model._meta,
                "video_ad_unit": video_ad_unit,
                "models": models,
                "loras": loras,
                "existing_storyboards": existing_storyboards,
                "lora_compat_url": reverse("admin:diffusion_diffusionjob_compatible_loras"),
            },
        )

    def storyboard_view(self, request, object_id):
        """Display the storyboard viewer for a video ad unit."""
        import os

        from django.conf import settings as django_settings
        from django.template.response import TemplateResponse

        video_ad_unit = VideoAdUnit.objects.get(pk=object_id)

        # Get the most recent storyboard
        storyboard = video_ad_unit.storyboards.order_by("-created_at").first()

        # Build frame data from storyboard images
        frames = []
        completed_count = 0
        processing_count = 0
        pending_count = 0

        if storyboard:
            for image in (
                storyboard.images.all()
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
            "admin/tvspots/videoadunit/storyboard_view.html",
            {
                **self.admin_site.each_context(request),
                "title": _("Storyboard"),
                "opts": self.model._meta,
                "video_ad_unit": video_ad_unit,
                "storyboard": storyboard,
                "frames": frames,
                "completed_count": completed_count,
                "processing_count": processing_count,
                "pending_count": pending_count,
            },
        )



# ---------------------------------------------------------------------------
# Storyboard
# ---------------------------------------------------------------------------


class StoryboardImageInline(TabularInline):
    """Inline display of images for Storyboard."""

    model = StoryboardImage
    tab = True
    extra = 0
    fields = [
        "script_row",
        "image_index",
        "diffusion_job",
        "show_status",
    ]
    readonly_fields = [
        "script_row",
        "image_index",
        "diffusion_job",
        "show_status",
    ]
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    @display(description=_("Status"))
    def show_status(self, obj):
        return obj.diffusion_job.get_status_display() if obj.diffusion_job else "—"


@admin.register(Storyboard)
class StoryboardAdmin(ModelAdmin):
    list_display = [
        "show_id",
        "show_video_ad_unit",
        "diffusion_model",
        "lora_model",
        "images_per_row",
        "show_status",
    ]
    list_filter = ["status", "diffusion_model", "video_ad_unit__campaign"]
    search_fields = ["video_ad_unit__campaign__script_title", "video_ad_unit__code"]
    readonly_fields = ["created_at", "completed_at"]
    inlines = [StoryboardImageInline]

    fieldsets = (
        (
            _("Configuration"),
            {
                "classes": ["tab"],
                "fields": (
                    "video_ad_unit",
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

    @display(description=_("Video Ad Unit"))
    def show_video_ad_unit(self, obj):
        return f"{obj.video_ad_unit.campaign.script_title} / {obj.video_ad_unit.code}"

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
        """Auto-queue new storyboards on save."""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new and obj.status == "pending":
            from .tasks import generate_storyboard_task

            generate_storyboard_task.apply_async(
                args=[obj.pk, True], queue="default"  # enhance_prompts=True by default
            )


# ---------------------------------------------------------------------------
# Ad Unit Media (Video Origin Extraction)
# ---------------------------------------------------------------------------


class KeyFrameInline(TabularInline):
    """Inline display of key frames for VideoProcessingResult."""

    model = KeyFrame
    tab = True
    extra = 0
    fields = ["scene_number", "timestamp", "show_thumbnail", "show_objects_count"]
    readonly_fields = ["scene_number", "timestamp", "show_thumbnail", "show_objects_count"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @display(description=_("Thumbnail"))
    def show_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 120px; max-height: 80px; border-radius: 4px;">',
                obj.image.url,
            )
        return "-"

    @display(description=_("Objects"))
    def show_objects_count(self, obj):
        return len(obj.detected_objects) if obj.detected_objects else 0


@admin.register(VideoProcessingResult)
class VideoProcessingResultAdmin(ModelAdmin):
    """Admin for video processing results with editable script."""

    list_display = ["id", "show_media", "show_scene_count", "processing_time", "created_at"]
    search_fields = ["media__campaign__script_title", "media__campaign__client_name"]
    readonly_fields = [
        "show_video_player",
        "scenes",
        "transcription",
        "visual_style",
        "objects_summary",
        "sentiment_analysis",
        "categories",
        "audience_insights",
        "processing_time",
        "models_used",
        "created_at",
        "updated_at",
    ]
    inlines = [KeyFrameInline]
    actions_detail = ["approve_script_action", "reject_script_action"]

    fieldsets = (
        (
            _("Video Player"),
            {
                "classes": ["tab"],
                "fields": ("show_video_player",),
            },
        ),
        (
            _("Overview"),
            {
                "classes": ["tab"],
                "fields": ("processing_time", "models_used"),
            },
        ),
        (
            _("Edit Script"),
            {
                "classes": ["tab"],
                "fields": ("script",),
                "description": "Edit the generated script. Changes will be saved when you click Save.",
            },
        ),
        (
            _("Scenes"),
            {
                "classes": ["tab"],
                "fields": ("scenes",),
            },
        ),
        (
            _("Transcription"),
            {
                "classes": ["tab"],
                "fields": ("transcription",),
            },
        ),
        (
            _("Visual Analysis"),
            {
                "classes": ["tab"],
                "fields": ("visual_style", "objects_summary"),
            },
        ),
        (
            _("Sentiment & Categories"),
            {
                "classes": ["tab"],
                "fields": ("sentiment_analysis", "categories"),
            },
        ),
        (
            _("Audience Insights"),
            {
                "classes": ["tab"],
                "fields": ("audience_insights",),
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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Use custom widget for script field."""
        if db_field.name == "script":
            kwargs["widget"] = ScriptEditorWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @display(description=_("Video Player"))
    def show_video_player(self, obj):
        """Display video player with scene markers."""
        if hasattr(obj, "media") and obj.media and obj.media.video_file:
            from django.templatetags.static import static

            video_url = obj.media.video_file.url
            scenes = obj.scenes or []

            # Render widget manually
            widget = VideoPlayerWidget(video_url=video_url, scenes=scenes)
            return mark_safe(widget.render("video_player", None, {}))
        return mark_safe('<div class="text-base-500">No video available</div>')

    def has_add_permission(self, request):
        """Results are created by the video processing pipeline only."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion of results."""
        return True

    @display(description=_("Media"))
    def show_media(self, obj):
        if hasattr(obj, "media") and obj.media:
            url = reverse("admin:tvspots_adunitmedia_change", args=[obj.media.pk])
            return format_html('<a href="{}">{}</a>', url, obj.media)
        return "-"

    @display(description=_("Scenes"))
    def show_scene_count(self, obj):
        return len(obj.scenes) if obj.scenes else 0

    @action(description=_("Approve Script"))
    def approve_script_action(self, request, object_id):
        """Approve the edited script and mark media as reviewed."""
        result = VideoProcessingResult.objects.get(pk=object_id)

        if hasattr(result, "media") and result.media:
            if result.media.status != "completed":
                messages.error(
                    request,
                    "Cannot approve script for media that is not in completed status.",
                )
                return redirect(
                    reverse("admin:tvspots_videoprocessingresult_change", args=[object_id])
                )

            # Update media status to reviewed
            result.media.status = "reviewed"
            result.media.save(update_fields=["status"])

            messages.success(
                request,
                f"Script approved for {result.media}. You can now create an origin VideoAdUnit.",
            )
        else:
            messages.warning(request, "No associated media found.")

        return redirect(
            reverse("admin:tvspots_videoprocessingresult_change", args=[object_id])
        )

    @action(description=_("Reject Script"))
    def reject_script_action(self, request, object_id):
        """Reject the script and reset media status for reprocessing."""
        result = VideoProcessingResult.objects.get(pk=object_id)

        if hasattr(result, "media") and result.media:
            # Reset media status to uploaded for reprocessing
            result.media.status = "uploaded"
            result.media.processing_error = "Script rejected - needs reprocessing"
            result.media.save(update_fields=["status", "processing_error"])

            messages.warning(
                request,
                f"Script rejected for {result.media}. Status reset to 'uploaded' for reprocessing.",
            )
        else:
            messages.warning(request, "No associated media found.")

        return redirect(
            reverse("admin:tvspots_videoprocessingresult_change", args=[object_id])
        )


@admin.register(AdUnitMedia)
class AdUnitMediaAdmin(ModelAdmin):
    """Admin for uploaded video files awaiting processing."""

    list_display = [
        "id",
        "campaign",
        "show_status",
        "show_duration",
        "show_resolution",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["campaign__script_title", "campaign__client_name"]
    readonly_fields = [
        "status",
        "duration",
        "resolution_width",
        "resolution_height",
        "frame_rate",
        "audio_channels",
        "audio_sample_rate",
        "file_size",
        "processing_started_at",
        "processing_completed_at",
        "processing_error",
        "result",
        "video_ad_unit",
        "created_at",
        "updated_at",
    ]
    actions_detail = ["reprocess_video_action", "create_origin_ad_unit_action"]

    fieldsets = (
        (
            _("Video Upload"),
            {
                "classes": ["tab"],
                "fields": ("campaign", "video_file", "show_status"),
            },
        ),
        (
            _("Processing Status"),
            {
                "classes": ["tab"],
                "fields": (
                    "status",
                    "processing_started_at",
                    "processing_completed_at",
                    "processing_error",
                ),
            },
        ),
        (
            _("Video Metadata"),
            {
                "classes": ["tab"],
                "fields": (
                    "duration",
                    ("resolution_width", "resolution_height"),
                    "frame_rate",
                    ("audio_channels", "audio_sample_rate"),
                    "file_size",
                ),
            },
        ),
        (
            _("Results"),
            {
                "classes": ["tab"],
                "fields": ("result", "video_ad_unit"),
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

    @display(
        description=_("Status"),
        label={
            "Pending Upload": "info",
            "Uploaded": "info",
            "Processing": "warning",
            "Completed": "success",
            "Failed": "danger",
            "Reviewed": "success",
        },
    )
    def show_status(self, obj):
        return obj.get_status_display()

    @display(description=_("Duration"))
    def show_duration(self, obj):
        if obj.duration:
            mins, secs = divmod(int(obj.duration), 60)
            return f"{mins}:{secs:02d}"
        return "-"

    @display(description=_("Resolution"))
    def show_resolution(self, obj):
        if obj.resolution_width and obj.resolution_height:
            return f"{obj.resolution_width}×{obj.resolution_height}"
        return "-"

    def save_model(self, request, obj, form, change):
        """Auto-trigger processing when video is uploaded."""
        is_new = obj.pk is None
        has_video = bool(obj.video_file)

        super().save_model(request, obj, form, change)

        # Auto-queue processing for newly uploaded videos
        if is_new and has_video:
            obj.status = "uploaded"
            obj.save(update_fields=["status"])

            # Queue processing task
            from .tasks import analyze_video_task

            analyze_video_task.apply_async(args=[obj.pk], queue="default")
            messages.info(
                request,
                f"Video processing queued for {obj}. Check back in a few minutes.",
            )

    @action(description=_("Reprocess Video"))
    def reprocess_video_action(self, request, object_id):
        """Reprocess a failed or completed video."""
        media = AdUnitMedia.objects.get(pk=object_id)

        if media.status not in ["failed", "completed"]:
            messages.error(
                request,
                f"Cannot reprocess video with status '{media.get_status_display()}'. "
                "Only failed or completed videos can be reprocessed.",
            )
            return redirect(
                reverse("admin:tvspots_adunitmedia_change", args=[object_id])
            )

        # Reset status and queue processing
        media.status = "uploaded"
        media.processing_error = ""
        media.save(update_fields=["status", "processing_error"])

        from .tasks import analyze_video_task

        analyze_video_task.apply_async(args=[media.pk], queue="default")

        messages.success(request, f"Video reprocessing queued for {media}.")
        return redirect(reverse("admin:tvspots_adunitmedia_change", args=[object_id]))

    @action(description=_("Create Origin VideoAdUnit"))
    def create_origin_ad_unit_action(self, request, object_id):
        """Create an origin VideoAdUnit from processed results with comprehensive error handling."""
        import logging

        logger = logging.getLogger(__name__)

        try:
            media = AdUnitMedia.objects.get(pk=object_id)
            logger.info(
                f"Creating origin VideoAdUnit for AdUnitMedia {media.id}",
                extra={
                    "ad_unit_media_id": media.id,
                    "campaign_id": media.campaign_id,
                    "user": request.user.username,
                },
            )

            # Validation - Status check
            if media.status != "completed":
                logger.warning(
                    f"Cannot create VideoAdUnit: invalid status '{media.status}'",
                    extra={"ad_unit_media_id": media.id, "status": media.status},
                )
                messages.error(
                    request,
                    f"Cannot create VideoAdUnit from video with status '{media.get_status_display()}'. "
                    "Video must be fully processed first.",
                )
                return redirect(
                    reverse("admin:tvspots_adunitmedia_change", args=[object_id])
                )

            # Validation - Duplicate check
            if media.video_ad_unit:
                logger.info(
                    f"VideoAdUnit already exists for media {media.id}",
                    extra={
                        "ad_unit_media_id": media.id,
                        "existing_ad_unit_id": media.video_ad_unit.pk,
                    },
                )
                messages.warning(
                    request,
                    f"VideoAdUnit already exists for this media: {media.video_ad_unit}",
                )
                return redirect(
                    reverse(
                        "admin:tvspots_videoadunit_change", args=[media.video_ad_unit.pk]
                    )
                )

            # Validation - Script check
            if not media.result:
                logger.error(
                    f"No processing result found for media {media.id}",
                    extra={"ad_unit_media_id": media.id},
                )
                messages.error(request, "No processing result found. Video may not have been processed yet.")
                return redirect(
                    reverse("admin:tvspots_adunitmedia_change", args=[object_id])
                )

            if not media.result.script:
                logger.error(
                    f"No script found in processing results for media {media.id}",
                    extra={"ad_unit_media_id": media.id, "result_id": media.result.pk},
                )
                messages.error(request, "No script found in processing results.")
                return redirect(
                    reverse("admin:tvspots_adunitmedia_change", args=[object_id])
                )

            # Validate script structure
            script_data = media.result.script
            if "script_rows" not in script_data and "scenes" not in script_data:
                logger.error(
                    f"Invalid script structure for media {media.id}: missing script_rows/scenes",
                    extra={"ad_unit_media_id": media.id, "script_keys": list(script_data.keys())},
                )
                messages.error(
                    request,
                    "Invalid script structure. Missing script_rows or scenes data.",
                )
                return redirect(
                    reverse("admin:tvspots_adunitmedia_change", args=[object_id])
                )

            # Create origin VideoAdUnit
            logger.info(f"Creating VideoAdUnit for media {media.id}")
            ad_unit = VideoAdUnit.objects.create(
                campaign=media.campaign,
                ad_unit_type="VIDEO",
                origin_or_adaptation="ORIGIN",
                code=f"ORIGIN-{media.id:04d}",
                title=script_data.get("script_title") or f"Origin from {media.campaign.script_title}",
                status="completed",
                duration=media.duration or script_data.get("total_runtime_seconds", 0),
            )

            logger.info(
                f"VideoAdUnit {ad_unit.id} created for media {media.id}",
                extra={
                    "ad_unit_media_id": media.id,
                    "video_ad_unit_id": ad_unit.id,
                    "campaign_id": media.campaign_id,
                },
            )

            # Create script rows from generated script
            rows_created = 0
            if "script_rows" in script_data:
                # New format: script_rows array
                for idx, row in enumerate(script_data["script_rows"]):
                    AdUnitScriptRow.objects.create(
                        ad_unit=ad_unit,
                        order_index=idx,
                        shot_number=row.get("shot_number", str(idx + 1)),
                        visual_text=row.get("visual_text", ""),
                        audio_text=row.get("audio_text", ""),
                    )
                    rows_created += 1
            elif "scenes" in script_data:
                # Old format: scenes array (Phase 1/2 compatibility)
                for idx, scene in enumerate(script_data["scenes"]):
                    audio_dict = scene.get("audio", {})
                    audio_text = audio_dict.get("voiceover", "") if isinstance(audio_dict, dict) else str(audio_dict)

                    AdUnitScriptRow.objects.create(
                        ad_unit=ad_unit,
                        order_index=idx,
                        shot_number=str(scene.get("scene_number", idx + 1)),
                        visual_text=scene.get("visual", ""),
                        audio_text=audio_text,
                    )
                    rows_created += 1

            logger.info(
                f"Created {rows_created} script rows for VideoAdUnit {ad_unit.id}",
                extra={"video_ad_unit_id": ad_unit.id, "rows_created": rows_created},
            )

            # Link back to media
            media.video_ad_unit = ad_unit
            media.status = "reviewed"
            media.save(update_fields=["video_ad_unit", "status"])

            logger.info(
                f"Origin VideoAdUnit creation complete for media {media.id}",
                extra={
                    "ad_unit_media_id": media.id,
                    "video_ad_unit_id": ad_unit.id,
                    "rows_created": rows_created,
                    "user": request.user.username,
                },
            )

            messages.success(
                request,
                format_html(
                    'Origin VideoAdUnit created: <a href="{}">{}</a>. '
                    'Created {} script row(s). <a href="{}">Create Adaptation →</a>',
                    reverse("admin:tvspots_videoadunit_change", args=[ad_unit.pk]),
                    ad_unit,
                    rows_created,
                    reverse("admin:tvspots_videoadunit_add") + f"?source_ad_unit={ad_unit.pk}",
                ),
            )
            return redirect(reverse("admin:tvspots_videoadunit_change", args=[ad_unit.pk]))

        except AdUnitMedia.DoesNotExist:
            logger.error(
                f"AdUnitMedia {object_id} not found",
                extra={"ad_unit_media_id": object_id, "user": request.user.username},
            )
            messages.error(request, f"AdUnitMedia with ID {object_id} not found.")
            return redirect(reverse("admin:tvspots_adunitmedia_changelist"))

        except Exception as e:
            logger.exception(
                f"Unexpected error creating origin VideoAdUnit for media {object_id}",
                extra={
                    "ad_unit_media_id": object_id,
                    "error": str(e),
                    "user": request.user.username,
                },
            )
            messages.error(
                request,
                f"An unexpected error occurred while creating the VideoAdUnit: {str(e)}. "
                "Please contact support if this persists.",
            )
            return redirect(
                reverse("admin:tvspots_adunitmedia_change", args=[object_id])
            )

    def get_urls(self):
        """Add custom URLs for reprocess and create actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/reprocess/",
                self.admin_site.admin_view(self.reprocess_video_action),
                name="tvspots_adunitmedia_reprocess",
            ),
            path(
                "<int:object_id>/create-ad-unit/",
                self.admin_site.admin_view(self.create_origin_ad_unit_action),
                name="tvspots_adunitmedia_create_ad_unit",
            ),
        ]
        return custom_urls + urls
