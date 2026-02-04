"""
Django admin configuration for diffusion models.

Uses Django Unfold for tabs, display decorators, and styled actions.
"""
from pathlib import Path
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display, action
from huggingface_hub import scan_cache_dir
from django_celery_results.models import TaskResult, GroupResult
from django_celery_results.admin import TaskResultAdmin as BaseTaskResultAdmin
from django_celery_results.admin import GroupResultAdmin as BaseGroupResultAdmin
from .models import (
    DiffusionModel, LoraModel, Prompt, DiffusionJob, BASE_ARCHITECTURE_CHOICES,
    AdaptationMarket, TvSpot, TvSpotVersion, TvSpotScriptRow, StoryboardJob, StoryboardImage,
)


# ---------------------------------------------------------------------------
# Re-register third-party / auth models with Unfold
# ---------------------------------------------------------------------------

admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.unregister(TaskResult)
admin.site.unregister(GroupResult)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    pass


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(TaskResult)
class TaskResultAdmin(BaseTaskResultAdmin, ModelAdmin):
    pass


@admin.register(GroupResult)
class GroupResultAdmin(BaseGroupResultAdmin, ModelAdmin):
    pass


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

class JobInline(TabularInline):
    """Inline display of jobs for Prompts."""
    model = DiffusionJob
    extra = 0
    fields = ['diffusion_model', 'lora_model', 'status', 'num_images', 'created_at']
    readonly_fields = ['status', 'created_at']
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# DiffusionModel
# ---------------------------------------------------------------------------

@admin.register(DiffusionModel)
class DiffusionModelAdmin(ModelAdmin):
    list_display = [
        'label', 'base_architecture', 'show_scheduler', 'token_window', 'vram_in_gb', 'steps',
        'show_resolution', 'show_negative_prompt', 'show_downloaded', 'show_active', 'show_loras_count',
    ]
    list_filter = ['is_active', 'base_architecture', 'pipeline', 'scheduler', 'supports_negative_prompt', 'dtype']
    search_fields = ['label', 'slug', 'path']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_("Model"), {
            "classes": ["tab"],
            "fields": ('label',
                       ('slug', 'path'),
                       ('pipeline', 'base_architecture', 'is_active')
                    ),
        }),
        (_("Generation"), {
            "classes": ["tab"],
            "fields": (
                ('default_width', 'default_height', 'max_pixels'),
                ('steps', 'guidance_scale', 'scheduler'), 
                ('dtype', 'max_sequence_length', 'supports_negative_prompt'),
                ('token_window', 'vram_usage'),
            ),
        }),
        (_("Metadata"), {
            "classes": ["tab"],
            "fields": ('created_at', 'updated_at'),
        }),
    )

    @display(description=_("Size"))
    def show_resolution(self, obj):
        return f"{obj.default_width}×{obj.default_height}"
    show_resolution.short_description="Resolution"

    @display(description=_("Neg Prompt"), boolean=True)
    def show_negative_prompt(self, obj):
        return obj.supports_negative_prompt

    @display(description=_("Downloaded"), boolean=True)
    def show_downloaded(self, obj):
        """Check if model exists in the HuggingFace cache."""
        try:
            cache_info = scan_cache_dir()
            return any(repo.repo_id == obj.path for repo in cache_info.repos)
        except Exception:
            return False

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active

    @display(description=_("LoRAs"))
    def show_loras_count(self, obj):
        count = LoraModel.objects.filter(base_architecture=obj.base_architecture).count()
        if count > 0:
            url = reverse('admin:diffusion_loramodel_changelist')
            return format_html(
                '<a href="{}?base_architecture__exact={}">{}</a>',
                url, obj.base_architecture, count,
            )
        return "0"
    
    @display(description=_("VRAM"))
    def vram_in_gb(self, obj):
        if obj.vram_usage:
            return f"{int(obj.vram_usage/1024)} GB"
        return "—"

    @display(description=_("Scheduler"))
    def show_scheduler(self, obj):
        if obj.scheduler:
            # Shorten common scheduler names for display
            name = obj.scheduler.replace('Scheduler', '').replace('Discrete', '')
            return name
        return "—"




# ---------------------------------------------------------------------------
# LoraModel
# ---------------------------------------------------------------------------

@admin.register(LoraModel)
class LoraModelAdmin(ModelAdmin):
    list_display = ['label', 'theme', 'base_architecture', 'show_downloaded', 'show_active']
    list_filter = ['is_active', 'base_architecture', 'theme']
    search_fields = ['label', 'path', 'air', 'theme']
    readonly_fields = ['created_at', 'updated_at', 'show_token_counts']
    actions = ['refresh_metadata_bulk_action']
    actions_row = ['refresh_metadata_action']

    fieldsets = (
        (_("LoRA"), {
            "classes": ["tab"],
            "fields": (
                ('label', 'is_active'),
                ('path', 'air'),
                ('base_architecture', 'theme'),
           ),
        }),
        (_("Prompt & Settings"), {
            "classes": ["tab"],
            "fields": (
                 ('default_strength', 'guidance_scale', 'clip_skip'),
                 ('prompt_suffix', 'negative_prompt_suffix'),
                 'show_token_counts',
                 'notes',
                ),
        }),
        (_("Metadata"), {
            "classes": ["tab"],
            "fields": ('created_at', 'updated_at'),
        }),
    )

    @display(description=_("CLIP Token Counts"))
    def show_token_counts(self, obj):
        try:
            from transformers import CLIPTokenizer
            tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-large-patch14")
            max_tokens = 75  # 77 minus BOS/EOS

            parts = []
            if obj.prompt_suffix:
                # Strip A1111 tags for accurate count
                import re
                clean = re.sub(r'<lora:[^>]+>', '', obj.prompt_suffix).strip().rstrip(',').strip()
                count = len(tokenizer.encode(clean, add_special_tokens=False))
                remaining = max_tokens - count
                parts.append(f"Prompt suffix: {count}/75 tokens ({remaining} remaining)")
            if obj.negative_prompt_suffix:
                count = len(tokenizer.encode(obj.negative_prompt_suffix, add_special_tokens=False))
                parts.append(f"Negative suffix: {count}/75 tokens")
            return mark_safe("<br>".join(parts)) if parts else "No suffixes set"
        except Exception as e:
            return f"Error: {e}"

    @display(description=_("Compatible With"))
    def show_compatible(self, obj):
        models = DiffusionModel.objects.filter(base_architecture=obj.base_architecture)
        if models.exists():
            return ", ".join(m.label for m in models)
        return "—"

    @display(description=_("Downloaded"), boolean=True)
    def show_downloaded(self, obj):
        """Check if LoRA file exists on disk."""
        import re
        try:
            if obj.path:
                lora_path = Path(obj.path)
                if not lora_path.is_absolute():
                    lora_path = settings.MODEL_BASE_PATH / obj.path
                return lora_path.exists()
            if obj.air:
                match = re.search(r'@(\d+)$', obj.air)
                if match:
                    version_id = match.group(1)
                    return (settings.MODEL_BASE_PATH / 'loras' / f'civitai_{version_id}.safetensors').exists()
            return False
        except Exception:
            return False

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active

    # --- Row actions ---

    @action(description=_("Refresh Metadata"))
    def refresh_metadata_action(self, request, object_id):
        """Refresh metadata from CivitAI for a LoRA."""
        return redirect('admin:refresh_lora_metadata', object_id)

    # --- Bulk actions ---

    @action(description=_("Refresh metadata from CivitAI"))
    def refresh_metadata_bulk_action(self, request, queryset):
        """Refresh metadata from CivitAI for selected LoRAs."""
        from lib.civitai import parse_air, fetch_model_version_metadata, extract_lora_metadata

        # Filter for LoRAs with AIRs
        loras_with_air = queryset.exclude(air='')
        total_selected = queryset.count()
        processable = loras_with_air.count()

        if processable == 0:
            self.message_user(
                request,
                "None of the selected LoRAs have CivitAI AIRs configured.",
                level=messages.WARNING
            )
            return

        updated_count = 0
        failed_count = 0
        skipped_count = 0
        error_messages = []

        for lora in loras_with_air:
            try:
                model_id, version_id = parse_air(lora.air)

                # Fetch fresh metadata from CivitAI
                raw_metadata = fetch_model_version_metadata(version_id, settings.CIVITAI_API_KEY)
                extracted = extract_lora_metadata(raw_metadata)

                # Track if anything changed
                changed = False

                # Update label if it was auto-generated or empty
                if not lora.label or lora.label.startswith('CivitAI Model'):
                    if extracted.get('label') and extracted['label'] != lora.label:
                        lora.label = extracted['label']
                        changed = True

                # Update fields if they differ
                if 'base_architecture' in extracted and lora.base_architecture != extracted['base_architecture']:
                    lora.base_architecture = extracted['base_architecture']
                    changed = True

                if 'prompt_suffix' in extracted and lora.prompt_suffix != extracted['prompt_suffix']:
                    lora.prompt_suffix = extracted['prompt_suffix']
                    changed = True

                if 'negative_prompt_suffix' in extracted and lora.negative_prompt_suffix != extracted['negative_prompt_suffix']:
                    lora.negative_prompt_suffix = extracted['negative_prompt_suffix']
                    changed = True

                if 'guidance_scale' in extracted and lora.guidance_scale != extracted.get('guidance_scale'):
                    lora.guidance_scale = extracted['guidance_scale']
                    changed = True

                if 'notes' in extracted:
                    lora.notes = extracted['notes']
                    changed = True  # Always consider notes as updated (stats change)

                if changed:
                    lora.save()
                    updated_count += 1
                else:
                    skipped_count += 1

            except Exception as e:
                failed_count += 1
                error_messages.append(f"{lora.label}: {str(e)}")

        # Build result message
        messages_list = []
        if updated_count > 0:
            messages_list.append(f"{updated_count} LoRA(s) updated")
        if skipped_count > 0:
            messages_list.append(f"{skipped_count} unchanged")
        if failed_count > 0:
            messages_list.append(f"{failed_count} failed")

        result_message = f"Metadata refresh complete: {', '.join(messages_list)}."

        if failed_count > 0 and len(error_messages) <= 5:
            result_message += f" Errors: {'; '.join(error_messages[:5])}"
        elif failed_count > 5:
            result_message += f" Errors: {'; '.join(error_messages[:5])} (and {failed_count - 5} more)"

        if updated_count > 0:
            self.message_user(request, result_message, level=messages.SUCCESS)
        elif skipped_count > 0:
            self.message_user(request, result_message, level=messages.INFO)
        else:
            self.message_user(request, result_message, level=messages.WARNING)

    def change_form_buttons(self, request, obj=None, add=False):
        """Add custom Download and Refresh Metadata buttons to the change form for LoRAs with AIR."""
        buttons = super().change_form_buttons(request, obj, add)

        if obj and obj.air and not add:
            # Check if already downloaded
            is_downloaded = self.show_downloaded(obj)
            button_title = 'Re-download from CivitAI' if is_downloaded else 'Download from CivitAI'

            buttons.append({
                'title': button_title,
                'url': reverse('admin:download_lora', args=[obj.pk]),
                'attrs': {
                    'class': 'button',
                }
            })

            # Add refresh metadata button
            buttons.append({
                'title': 'Refresh Metadata from CivitAI',
                'url': reverse('admin:refresh_lora_metadata', args=[obj.pk]),
                'attrs': {
                    'class': 'button',
                }
            })

        return buttons

    def get_urls(self):
        """Add custom URL for download action."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:lora_id>/download/',
                self.admin_site.admin_view(self.download_lora_view),
                name='download_lora',
            ),
            path(
                '<int:lora_id>/refresh-metadata/',
                self.admin_site.admin_view(self.refresh_metadata_view),
                name='refresh_lora_metadata',
            ),
            path(
                'import-from-civitai/',
                self.admin_site.admin_view(self.import_from_civitai_view),
                name='import_lora_from_civitai',
            ),
        ]
        return custom_urls + urls

    def download_lora_view(self, request, lora_id):
        """Handle the download action by queuing a Celery task."""
        from .tasks import download_lora_task

        lora = LoraModel.objects.get(pk=lora_id)

        if not lora.air:
            messages.error(request, f'LoRA "{lora.label}" has no CivitAI AIR configured.')
            return redirect('admin:diffusion_loramodel_change', lora_id)

        # Queue the download task
        download_lora_task.apply_async(args=[lora_id], queue='default')

        messages.info(
            request,
            f'Download started for "{lora.label}" in background. '
            f'Check logs or refresh page to verify completion.'
        )

        return redirect('admin:diffusion_loramodel_change', lora_id)

    def refresh_metadata_view(self, request, lora_id):
        """Refresh metadata from CivitAI for an existing LoRA."""
        lora = LoraModel.objects.get(pk=lora_id)

        if not lora.air:
            messages.error(request, f'LoRA "{lora.label}" has no CivitAI AIR configured.')
            return redirect('admin:diffusion_loramodel_change', lora_id)

        try:
            from lib.civitai import parse_air, fetch_model_version_metadata, extract_lora_metadata

            model_id, version_id = parse_air(lora.air)

            # Fetch fresh metadata from CivitAI
            raw_metadata = fetch_model_version_metadata(version_id, settings.CIVITAI_API_KEY)
            extracted = extract_lora_metadata(raw_metadata)

            # Track what fields were updated
            updated_fields = []

            # Update label if it was auto-generated or empty
            if not lora.label or lora.label.startswith('CivitAI Model'):
                if extracted.get('label'):
                    lora.label = extracted['label']
                    updated_fields.append('label')

            # Always update these fields with fresh data
            if 'base_architecture' in extracted:
                old_arch = lora.base_architecture
                lora.base_architecture = extracted['base_architecture']
                if old_arch != lora.base_architecture:
                    updated_fields.append('base_architecture')

            if 'prompt_suffix' in extracted:
                lora.prompt_suffix = extracted['prompt_suffix']
                updated_fields.append('trigger words')

            if 'negative_prompt_suffix' in extracted:
                lora.negative_prompt_suffix = extracted['negative_prompt_suffix']
                updated_fields.append('negative prompt')

            if 'guidance_scale' in extracted:
                lora.guidance_scale = extracted['guidance_scale']
                updated_fields.append('guidance scale')

            if 'notes' in extracted:
                lora.notes = extracted['notes']
                updated_fields.append('notes/stats')

            lora.save()

            if updated_fields:
                messages.success(
                    request,
                    f'Metadata refreshed for "{lora.label}". Updated: {", ".join(updated_fields)}.'
                )
            else:
                messages.info(request, f'Metadata fetched but no changes detected for "{lora.label}".')

        except Exception as e:
            messages.error(request, f'Failed to refresh metadata: {e}')

        return redirect('admin:diffusion_loramodel_change', lora_id)

    def import_from_civitai_view(self, request):
        """Handle importing a LoRA from CivitAI by AIR."""
        from django.template.response import TemplateResponse
        from .tasks import download_lora_task

        # Handle form submission
        if request.method == 'POST':
            air = request.POST.get('air', '').strip()
            label = request.POST.get('label', '').strip()
            base_architecture = request.POST.get('base_architecture', 'sdxl')
            prompt_suffix = request.POST.get('prompt_suffix', '').strip()
            negative_prompt_suffix = request.POST.get('negative_prompt_suffix', '').strip()
            notes = request.POST.get('notes', '').strip()
            guidance_scale_str = request.POST.get('guidance_scale', '').strip()

            # Validate AIR format
            if not air:
                messages.error(request, 'AIR is required.')
                return redirect('admin:import_lora_from_civitai')

            # Parse AIR to validate format
            try:
                from lib.civitai import parse_air
                model_id, version_id = parse_air(air)
            except ValueError as e:
                messages.error(request, f'Invalid AIR format: {e}')
                return redirect('admin:import_lora_from_civitai')

            # Auto-generate label if not provided
            if not label:
                label = f"CivitAI Model {model_id} v{version_id}"

            # Parse guidance_scale if provided
            guidance_scale = None
            if guidance_scale_str:
                try:
                    guidance_scale = float(guidance_scale_str)
                except ValueError:
                    pass

            # Create the LoRA model with all fields
            lora = LoraModel.objects.create(
                label=label,
                air=air,
                base_architecture=base_architecture,
                prompt_suffix=prompt_suffix,
                negative_prompt_suffix=negative_prompt_suffix,
                notes=notes,
                guidance_scale=guidance_scale,
                is_active=True,
            )

            # Queue the download task
            download_lora_task.apply_async(args=[lora.id], queue='default')

            messages.success(
                request,
                f'LoRA "{label}" created and download queued. '
                f'Check the LoRA details page to verify completion.'
            )

            return redirect('admin:diffusion_loramodel_change', lora.id)

        # Handle GET request - optionally fetch metadata if AIR provided
        initial_data = {
            'air': request.GET.get('air', ''),
            'label': '',
            'base_architecture': 'sdxl',
            'prompt_suffix': '',
            'negative_prompt_suffix': '',
            'notes': '',
            'guidance_scale': '',
        }

        metadata_fetched = False
        fetch_error = None

        # If AIR is provided in query params, fetch metadata
        if initial_data['air']:
            try:
                from lib.civitai import parse_air, fetch_model_version_metadata, extract_lora_metadata

                model_id, version_id = parse_air(initial_data['air'])

                # Fetch metadata from CivitAI API
                raw_metadata = fetch_model_version_metadata(version_id, settings.CIVITAI_API_KEY)
                extracted = extract_lora_metadata(raw_metadata)

                # Update initial data with extracted metadata
                initial_data.update(extracted)
                metadata_fetched = True

                messages.info(
                    request,
                    f'Metadata fetched from CivitAI. Review and edit fields below before importing.'
                )

            except Exception as e:
                fetch_error = str(e)
                messages.warning(
                    request,
                    f'Could not fetch metadata from CivitAI: {e}. You can still import manually.'
                )

        # Render the form
        return TemplateResponse(
            request,
            'admin/diffusion/loramodel/import_from_civitai.html',
            {
                **self.admin_site.each_context(request),
                'title': _('Import LoRA from CivitAI'),
                'opts': self.model._meta,
                'base_architecture_choices': BASE_ARCHITECTURE_CHOICES,
                'initial_data': initial_data,
                'metadata_fetched': metadata_fetched,
                'fetch_error': fetch_error,
            },
        )

    def changelist_view(self, request, extra_context=None):
        """Override changelist to add import button context."""
        extra_context = extra_context or {}
        extra_context['import_from_civitai_url'] = reverse('admin:import_lora_from_civitai')
        return super().changelist_view(request, extra_context=extra_context)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

class PromptStatusFilter(admin.SimpleListFilter):
    title = _("Status")
    parameter_name = "is_enhanced"

    def lookups(self, request, model_admin):
        return [
            ("enhanced", _("Enhanced")),
            ("pending", _("Pending")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "enhanced":
            return queryset.exclude(enhanced_prompt="")
        if self.value() == "pending":
            return queryset.filter(enhanced_prompt="")
        return queryset


@admin.register(Prompt)
class PromptAdmin(ModelAdmin):
    list_display = [
        'show_preview', 'enhancement_style',
        'show_status', 'show_jobs', 'created_at',
    ]
    list_filter = ['enhancement_method', 'enhancement_style', PromptStatusFilter, 'created_at']
    search_fields = ['source_prompt', 'enhanced_prompt']
    readonly_fields = ['created_at', 'updated_at', 'enhancement_method']
    actions = ['enhance_prompts_action', 'create_job_for_prompts']
    actions_row = ['enhance_single_action', 'create_job_action']
    inlines = [JobInline]

    fieldsets = (
        (_("Prompt"), {
            "classes": ["tab"],
            "fields": ('source_prompt',),
        }),
        (_("Enhancement"), {
            "classes": ["tab"],
            "fields": (
                ('enhanced_prompt', 'negative_prompt'),
                ('enhancement_method', 'enhancement_style', 'creativity'),
            ),
        }),
        (_("Metadata"), {
            "classes": ["tab"],
            "fields": ('created_at', 'updated_at'),
        }),
    )

    @display(description=_("Prompt"))
    def show_preview(self, obj):
        text = obj.source_prompt[:80]
        if len(obj.source_prompt) > 80:
            text += "…"
        return text

    @display(
        description=_("Status"),
        label={
            "Enhanced": "success",
            "Pending": "warning",
        },
    )
    def show_status(self, obj):
        return "Enhanced" if obj.enhanced_prompt else "Pending"

    @display(description=_("Jobs"))
    def show_jobs(self, obj):
        count = obj.jobs.count()
        if count > 0:
            url = reverse('admin:diffusion_diffusionjob_changelist')
            return format_html(
                '<a href="{}?prompt__id__exact={}">{}</a>',
                url, obj.id, count,
            )
        return "0"

    # --- Row actions ---

    @action(description=_("Enhance"))
    def enhance_single_action(self, request, object_id):
        from . import tasks
        prompt = Prompt.objects.get(id=object_id)
        if prompt.enhanced_prompt:
            messages.warning(request, "Prompt is already enhanced.")
        else:
            tasks.enhance_prompt_task.apply_async(args=[object_id], queue='enhancement')
            messages.success(request, "Prompt queued for enhancement.")
        return redirect('admin:diffusion_prompt_changelist')

    @action(description=_("Create Job"))
    def create_job_action(self, request, object_id):
        return redirect(
            f"{reverse('admin:diffusion_diffusionjob_add')}?prompt={object_id}"
        )

    # --- Bulk actions ---

    @action(description=_("Enhance selected prompts"))
    def enhance_prompts_action(self, request, queryset):
        from . import tasks
        count = 0
        for prompt in queryset:
            if not prompt.enhanced_prompt:
                tasks.enhance_prompt_task.apply_async(args=[prompt.id], queue='enhancement')
                count += 1
        self.message_user(request, f"{count} prompts queued for enhancement.")

    @action(description=_("Create jobs for selected prompts"))
    def create_job_for_prompts(self, request, queryset):
        from django.template.response import TemplateResponse

        # Second pass: user submitted the confirmation form
        if request.POST.get('post') == 'yes':
            from . import tasks

            model_id = request.POST.get('diffusion_model')
            lora_id = request.POST.get('lora_model') or None
            num_images = int(request.POST.get('num_images', 1))

            model = DiffusionModel.objects.get(id=model_id)
            lora = LoraModel.objects.get(id=lora_id) if lora_id else None

            count = 0
            for prompt in queryset:
                job = DiffusionJob.objects.create(
                    prompt=prompt,
                    diffusion_model=model,
                    lora_model=lora,
                    num_images=num_images,
                )
                celery_task = tasks.generate_images_task.apply_async(
                    args=[job.id], queue='default'
                )
                job.rq_job_id = celery_task.id
                job.status = 'queued'
                job.save()
                count += 1

            lora_label = f" with {lora.label}" if lora else ""
            self.message_user(
                request,
                f"{count} jobs created and queued using {model.label}{lora_label}.",
            )
            return

        # First pass: render confirmation page with model/LoRA selection
        models = DiffusionModel.objects.filter(is_active=True)
        loras = LoraModel.objects.filter(is_active=True)

        return TemplateResponse(
            request,
            'admin/diffusion/prompt/create_jobs_confirmation.html',
            {
                **self.admin_site.each_context(request),
                'title': _("Create jobs for selected prompts"),
                'prompts': queryset,
                'models': models,
                'loras': loras,
                'opts': self.model._meta,
            },
        )


# ---------------------------------------------------------------------------
# DiffusionJob
# ---------------------------------------------------------------------------

@admin.register(DiffusionJob)
class DiffusionJobAdmin(ModelAdmin):
    change_form_template = 'admin/diffusion/diffusionjob/change_form.html'

    class Media:
        js = ('diffusion/js/filter_loras.js',)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'compatible-loras/',
                self.admin_site.admin_view(self.compatible_loras_view),
                name='diffusion_diffusionjob_compatible_loras',
            ),
        ]
        return custom + urls

    def compatible_loras_view(self, request):
        model_id = request.GET.get('model_id')
        if not model_id:
            return JsonResponse({'lora_ids': []})
        try:
            model = DiffusionModel.objects.get(id=model_id)
        except DiffusionModel.DoesNotExist:
            return JsonResponse({'lora_ids': []})
        lora_ids = list(
            LoraModel.objects.filter(
                is_active=True, base_architecture=model.base_architecture
            ).values_list('id', flat=True)
        )
        return JsonResponse({'lora_ids': lora_ids})

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['lora_compat_url'] = reverse(
            'admin:diffusion_diffusionjob_compatible_loras'
        )
        return super().changeform_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter LoRA choices based on the selected model's architecture."""
        if db_field.name == "lora_model":
            # Get the job being edited (if any)
            object_id = request.resolver_match.kwargs.get('object_id')
            if object_id:
                try:
                    job = DiffusionJob.objects.get(pk=object_id)
                    if job.diffusion_model:
                        # Filter LoRAs to match the job's model architecture
                        kwargs["queryset"] = LoraModel.objects.filter(
                            is_active=True,
                            base_architecture=job.diffusion_model.base_architecture
                        )
                except DiffusionJob.DoesNotExist:
                    pass
            # For new jobs, show only active LoRAs (JavaScript will filter dynamically)
            if "queryset" not in kwargs:
                kwargs["queryset"] = LoraModel.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    list_display = [
        'show_id', 'identifier', 'show_status', 'diffusion_model', 'lora_model', 'show_scheduler',
        'show_prompt', 'num_images', 'created_at', 'show_duration',
    ]
    list_filter = ['status', 'diffusion_model', 'lora_model', 'scheduler', 'created_at']
    search_fields = ['rq_job_id', 'prompt__source_prompt']
    readonly_fields = [
        'rq_job_id', 'status', 'created_at', 'started_at', 'completed_at',
        'show_result_images', 'show_generation_metadata', 'show_duration',
    ]
    actions = ['queue_jobs_action', 'cancel_jobs_action', 'retry_failed_jobs']
    actions_row = ['queue_single_action', 'retry_single_action', 'cancel_single_action']

    fieldsets = (
        (_("Configuration"), {
            "classes": ["tab"],
            "fields": ('diffusion_model', 'lora_model', 'prompt', 'identifier'),
        }),
        (_("Parameters"), {
            "classes": ["tab"],
            "fields": (
                ('width', 'height'), ('steps', 'guidance_scale'),
                ('scheduler', 'lora_strength'), ('seed', 'num_images'),
            ),
            "description": _("Leave blank to use model/LoRA defaults."),
        }),
        (_("Status"), {
            "classes": ["tab"],
            "fields": (
                'status', 'rq_job_id', 'error_message',
            ),
        }),
        (_("Results"), {
            "classes": ["tab"],
            "fields": ('show_result_images', 'show_generation_metadata'),
        }),
        (_("Timing"), {
            "classes": ["tab"],
            "fields": ('created_at', 'started_at', 'completed_at', 'show_duration'),
        }),
    )

    @display(description=_("ID"))
    def show_id(self, obj):
        return f"#{obj.pk}"

    @display(
        description=_("Status"),
        label={
            "Pending": "info",
            "Queued": "info",
            "Processing": "warning",
            "Completed": "success",
            "Failed": "danger",
            "Cancelled": "info",
        },
    )
    def show_status(self, obj):
        return obj.get_status_display()

    @display(description=_("Prompt"))
    def show_prompt(self, obj):
        text = obj.prompt.source_prompt[:50]
        if len(obj.prompt.source_prompt) > 50:
            text += "…"
        return text

    @display(description=_("Duration"))
    def show_duration(self, obj):
        if obj.started_at and obj.completed_at:
            delta = obj.completed_at - obj.started_at
            seconds = int(delta.total_seconds())
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                return f"{seconds // 60}m {seconds % 60}s"
            return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
        return "—"

    @display(description=_("Scheduler"))
    def show_scheduler(self, obj):
        # Show job override or model default
        scheduler = obj.scheduler or (obj.diffusion_model.scheduler if obj.diffusion_model else None)
        if scheduler:
            # Shorten common scheduler names for display
            name = scheduler.replace('Scheduler', '').replace('Discrete', '')
            # Indicate if it's an override vs model default
            if obj.scheduler:
                return format_html('<span title="Job override">{}</span>', name)
            return format_html('<span title="Model default" style="opacity: 0.7">{}</span>', name)
        return "—"

    @display(description=_("Generated Images"))
    def show_result_images(self, obj):
        if not obj.result_images:
            return "No images"
        from django.conf import settings
        import os
        html_parts = []
        for img_path in obj.result_images:
            media_url = settings.MEDIA_URL
            if img_path.startswith(str(settings.MEDIA_ROOT)):
                rel_path = os.path.relpath(img_path, settings.MEDIA_ROOT)
                img_url = os.path.join(media_url, rel_path)
            else:
                img_url = os.path.join(media_url, img_path)
            html_parts.append(
                f'<a href="{img_url}" target="_blank">'
                f'<img src="{img_url}" style="max-width: 200px; max-height: 200px; margin: 5px;" />'
                f'</a>'
            )
        return mark_safe(''.join(html_parts))

    @display(description=_("Generation Metadata"))
    def show_generation_metadata(self, obj):
        """Display generation metadata as formatted JSON"""
        if not obj.generation_metadata:
            return "No metadata available"

        import json
        formatted_json = json.dumps(obj.generation_metadata, indent=2, ensure_ascii=False)
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; max-height: 500px;">{}</pre>',
            formatted_json
        )

    # --- Row actions ---

    @action(description=_("Queue"))
    def queue_single_action(self, request, object_id):
        from . import tasks
        job = DiffusionJob.objects.get(id=object_id)
        if job.status != 'pending':
            messages.warning(request, f"Job #{object_id} is not pending (status: {job.status}).")
        else:
            celery_task = tasks.generate_images_task.apply_async(args=[object_id], queue='default')
            job.rq_job_id = celery_task.id
            job.status = 'queued'
            job.save()
            messages.success(request, f"Job #{object_id} queued for processing.")
        return redirect('admin:diffusion_diffusionjob_changelist')

    @action(description=_("Retry"))
    def retry_single_action(self, request, object_id):
        from . import tasks
        job = DiffusionJob.objects.get(id=object_id)
        if job.status != 'failed':
            messages.warning(request, f"Job #{object_id} is not failed (status: {job.status}).")
        else:
            job.status = 'pending'
            job.error_message = ''
            job.rq_job_id = ''
            job.save()
            celery_task = tasks.generate_images_task.apply_async(args=[object_id], queue='default')
            job.rq_job_id = celery_task.id
            job.status = 'queued'
            job.save()
            messages.success(request, f"Job #{object_id} queued for retry.")
        return redirect('admin:diffusion_diffusionjob_changelist')

    @action(description=_("Cancel"))
    def cancel_single_action(self, request, object_id):
        job = DiffusionJob.objects.get(id=object_id)
        if job.status not in ['pending', 'queued']:
            messages.warning(request, f"Job #{object_id} cannot be cancelled (status: {job.status}).")
        else:
            job.status = 'cancelled'
            job.save()
            messages.success(request, f"Job #{object_id} cancelled.")
        return redirect('admin:diffusion_diffusionjob_changelist')

    # --- Bulk actions ---

    @action(description=_("Queue selected jobs"))
    def queue_jobs_action(self, request, queryset):
        from . import tasks
        count = 0
        for job in queryset.filter(status='pending'):
            celery_task = tasks.generate_images_task.apply_async(args=[job.id], queue='default')
            job.rq_job_id = celery_task.id
            job.status = 'queued'
            job.save()
            count += 1
        self.message_user(request, f"{count} jobs queued for processing.")

    @action(description=_("Cancel selected jobs"))
    def cancel_jobs_action(self, request, queryset):
        count = queryset.filter(status__in=['pending', 'queued']).update(status='cancelled')
        self.message_user(request, f"{count} jobs cancelled.")

    @action(description=_("Retry failed jobs"))
    def retry_failed_jobs(self, request, queryset):
        from . import tasks
        count = 0
        for job in queryset.filter(status='failed'):
            job.status = 'pending'
            job.error_message = ''
            job.rq_job_id = ''
            job.save()
            celery_task = tasks.generate_images_task.apply_async(args=[job.id], queue='default')
            job.rq_job_id = celery_task.id
            job.status = 'queued'
            job.save()
            count += 1
        self.message_user(request, f"{count} failed jobs queued for retry.")

    def save_model(self, request, obj, form, change):
        """Auto-queue new jobs on save."""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new and obj.status == 'pending':
            from . import tasks
            celery_task = tasks.generate_images_task.apply_async(args=[obj.id], queue='default')
            obj.rq_job_id = celery_task.id
            obj.status = 'queued'
            obj.save()


# ---------------------------------------------------------------------------
# AdaptationMarket
# ---------------------------------------------------------------------------

@admin.register(AdaptationMarket)
class AdaptationMarketAdmin(ModelAdmin):
    list_display = ['name', 'code', 'show_active', 'show_versions_count', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'rules']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_("Market"), {
            "classes": ["tab"],
            "fields": ('name', 'code', 'is_active'),
        }),
        (_("Rules"), {
            "classes": ["tab"],
            "fields": ('rules',),
        }),
        (_("Metadata"), {
            "classes": ["tab"],
            "fields": ('created_at', 'updated_at'),
        }),
    )

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active

    @display(description=_("Versions"))
    def show_versions_count(self, obj):
        count = obj.versions.count()
        if count > 0:
            url = reverse('admin:diffusion_tvspotversion_changelist')
            return format_html(
                '<a href="{}?market__id__exact={}">{}</a>',
                url, obj.id, count,
            )
        return "0"


# ---------------------------------------------------------------------------
# TV Spot Inlines
# ---------------------------------------------------------------------------

class TvSpotScriptRowInline(TabularInline):
    """Inline display of script rows for TvSpotVersion."""
    model = TvSpotScriptRow
    extra = 0
    fields = ['order_index', 'shot_number', 'timecode_start', 'duration_seconds', 'visual_text', 'audio_text']
    ordering = ['order_index']


class TvSpotVersionInline(TabularInline):
    """Inline display of versions for TvSpot."""
    model = TvSpotVersion
    extra = 0
    fields = ['code', 'name', 'version_type', 'market', 'language', 'is_active']
    readonly_fields = ['code', 'name', 'version_type', 'market', 'language']
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# TvSpot
# ---------------------------------------------------------------------------

@admin.register(TvSpot)
class TvSpotAdmin(ModelAdmin):
    list_display = ['script_title', 'client_name', 'brand_name', 'job_id', 'show_trt', 'show_versions_count', 'created_at']
    list_filter = ['client_name', 'created_at']
    search_fields = ['script_title', 'client_name', 'brand_name', 'job_id']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TvSpotVersionInline]

    fieldsets = (
        (_("Project"), {
            "classes": ["tab"],
            "fields": (
                ('client_name', 'brand_name'),
                ('script_title', 'job_id'),
                'total_runtime_seconds',
            ),
        }),
        (_("Notes"), {
            "classes": ["tab"],
            "fields": ('notes',),
        }),
        (_("Metadata"), {
            "classes": ["tab"],
            "fields": ('created_at', 'updated_at'),
        }),
    )

    @display(description=_("TRT"))
    def show_trt(self, obj):
        return f"{obj.total_runtime_seconds}s"

    @display(description=_("Versions"))
    def show_versions_count(self, obj):
        count = obj.versions.count()
        if count > 0:
            url = reverse('admin:diffusion_tvspotversion_changelist')
            return format_html(
                '<a href="{}?tv_spot__id__exact={}">{}</a>',
                url, obj.id, count,
            )
        return "0"

    def get_urls(self):
        """Add custom URLs for import and adaptation actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                'import/',
                self.admin_site.admin_view(self.import_tvspot_view),
                name='diffusion_tvspot_import',
            ),
            path(
                '<int:object_id>/create-adaptation/',
                self.admin_site.admin_view(self.create_adaptation_view),
                name='diffusion_tvspot_create_adaptation',
            ),
        ]
        return custom_urls + urls

    def import_tvspot_view(self, request):
        """Handle importing a TV spot from JSON."""
        from django.template.response import TemplateResponse
        from django.db import transaction
        import json

        if request.method == 'POST':
            json_data = request.POST.get('json_data', '').strip()

            if not json_data:
                messages.error(request, 'JSON data is required.')
                return redirect('admin:diffusion_tvspot_import')

            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                messages.error(request, f'Invalid JSON: {e}')
                return redirect('admin:diffusion_tvspot_import')

            # Validate required fields
            errors = self._validate_tvspot_json(data)
            if errors:
                for error in errors:
                    messages.error(request, error)
                return redirect('admin:diffusion_tvspot_import')

            # Check for duplicate job_id
            job_id = data['job_id']
            if TvSpot.objects.filter(job_id=job_id).exists():
                messages.error(request, f"TV Spot with job_id '{job_id}' already exists.")
                return redirect('admin:diffusion_tvspot_import')

            # Create records
            try:
                with transaction.atomic():
                    tv_spot = TvSpot.objects.create(
                        client_name=data['client_name'],
                        brand_name=data.get('brand_name', ''),
                        script_title=data['script_title'],
                        total_runtime_seconds=data['total_runtime_seconds'],
                        job_id=job_id,
                        notes=data.get('notes', ''),
                    )

                    version = TvSpotVersion.objects.create(
                        tv_spot=tv_spot,
                        version_type='origin',
                        code='ORIGIN',
                        name='Origin',
                        language=data.get('language', 'en-US'),
                    )

                    for idx, row_data in enumerate(data['script_rows']):
                        TvSpotScriptRow.objects.create(
                            tv_spot_version=version,
                            order_index=idx,
                            shot_number=row_data.get('shot_number', f"{idx + 1:02d}"),
                            timecode_start=row_data.get('timecode_start', ''),
                            duration_seconds=row_data.get('duration_seconds'),
                            visual_text=row_data['visual_text'],
                            audio_text=row_data['audio_text'],
                        )

                messages.success(
                    request,
                    f"Created TV Spot '{tv_spot.script_title}' with {len(data['script_rows'])} script rows."
                )
                return redirect('admin:diffusion_tvspot_change', tv_spot.pk)

            except Exception as e:
                messages.error(request, f'Failed to create TV Spot: {e}')
                return redirect('admin:diffusion_tvspot_import')

        # Render import form
        return TemplateResponse(
            request,
            'admin/diffusion/tvspot/import_tvspot.html',
            {
                **self.admin_site.each_context(request),
                'title': _('Import TV Spot from JSON'),
                'opts': self.model._meta,
            },
        )

    def _validate_tvspot_json(self, data: dict) -> list:
        """Validate JSON against expected schema. Returns list of errors."""
        errors = []

        required = ['client_name', 'script_title', 'total_runtime_seconds', 'job_id', 'script_rows']
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        if errors:
            return errors

        if not isinstance(data['script_rows'], list):
            errors.append("script_rows must be an array")
            return errors

        if len(data['script_rows']) == 0:
            errors.append("script_rows must have at least one row")

        if not isinstance(data['total_runtime_seconds'], int) or data['total_runtime_seconds'] <= 0:
            errors.append("total_runtime_seconds must be a positive integer")

        for idx, row in enumerate(data['script_rows']):
            if not isinstance(row, dict):
                errors.append(f"script_rows[{idx}] must be an object")
                continue
            if 'visual_text' not in row or not row['visual_text']:
                errors.append(f"script_rows[{idx}] missing or empty visual_text")
            if 'audio_text' not in row or not row['audio_text']:
                errors.append(f"script_rows[{idx}] missing or empty audio_text")

        return errors

    def changelist_view(self, request, extra_context=None):
        """Override changelist to add import button context."""
        extra_context = extra_context or {}
        extra_context['import_tvspot_url'] = reverse('admin:diffusion_tvspot_import')
        return super().changelist_view(request, extra_context=extra_context)

    def change_form_buttons(self, request, obj=None, add=False):
        """Add custom Create Adaptation button to the change form."""
        buttons = super().change_form_buttons(request, obj, add)

        if obj and not add:
            # Only show button if there's an origin version
            origin = obj.versions.filter(version_type='origin').first()
            if origin:
                buttons.append({
                    'title': 'Create Adaptation',
                    'url': reverse('admin:diffusion_tvspot_create_adaptation', args=[obj.pk]),
                    'attrs': {
                        'class': 'button',
                    }
                })

        return buttons

    def create_adaptation_view(self, request, object_id):
        """Handle creating an adaptation of a TV spot."""
        from django.template.response import TemplateResponse
        from .tasks import create_adaptation_task

        tv_spot = TvSpot.objects.get(pk=object_id)
        origin_version = tv_spot.versions.filter(version_type='origin').first()

        if not origin_version:
            messages.error(request, 'No origin version found for this TV spot.')
            return redirect('admin:diffusion_tvspot_change', object_id)

        if request.method == 'POST':
            market_id = request.POST.get('market')

            if not market_id:
                messages.error(request, 'Please select a target market.')
                return redirect('admin:diffusion_tvspot_create_adaptation', object_id)

            # Check if adaptation already exists for this market
            market = AdaptationMarket.objects.get(pk=market_id)
            existing = tv_spot.versions.filter(market=market).first()
            if existing:
                messages.warning(
                    request,
                    f"An adaptation for {market.name} already exists: {existing.name}"
                )
                return redirect('admin:diffusion_tvspotversion_change', existing.pk)

            # Queue the adaptation task
            create_adaptation_task.apply_async(
                args=[origin_version.pk, market_id],
                queue='enhancement'
            )

            messages.success(
                request,
                f"Adaptation to {market.name} queued for processing. "
                f"Check back in 1-2 minutes for the new version."
            )
            return redirect('admin:diffusion_tvspot_change', object_id)

        # Get available markets (exclude markets with existing adaptations)
        existing_market_ids = tv_spot.versions.exclude(
            market__isnull=True
        ).values_list('market_id', flat=True)

        markets = AdaptationMarket.objects.filter(
            is_active=True
        ).exclude(id__in=existing_market_ids)

        existing_adaptations = tv_spot.versions.filter(
            version_type='adaptation'
        ).select_related('market')

        return TemplateResponse(
            request,
            'admin/diffusion/tvspot/create_adaptation.html',
            {
                **self.admin_site.each_context(request),
                'title': _('Create Adaptation'),
                'opts': self.model._meta,
                'tv_spot': tv_spot,
                'origin_version': origin_version,
                'markets': markets,
                'existing_adaptations': existing_adaptations,
            },
        )


# ---------------------------------------------------------------------------
# TvSpotVersion
# ---------------------------------------------------------------------------

@admin.register(TvSpotVersion)
class TvSpotVersionAdmin(ModelAdmin):
    list_display = ['show_title', 'code', 'name', 'version_type', 'market', 'language', 'show_rows_count', 'show_active']
    list_filter = ['version_type', 'market', 'is_active', 'tv_spot']
    search_fields = ['code', 'name', 'tv_spot__script_title', 'tv_spot__job_id']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TvSpotScriptRowInline]

    fieldsets = (
        (_("Version"), {
            "classes": ["tab"],
            "fields": (
                'tv_spot',
                ('version_type', 'market'),
                ('code', 'name'),
                'language',
                'is_active',
            ),
        }),
        (_("Visual Style"), {
            "classes": ["tab"],
            "fields": ('visual_style_prompt',),
        }),
        (_("Metadata"), {
            "classes": ["tab"],
            "fields": ('created_at', 'updated_at'),
        }),
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
                '<int:object_id>/generate-storyboard/',
                self.admin_site.admin_view(self.generate_storyboard_view),
                name='diffusion_tvspotversion_generate_storyboard',
            ),
            path(
                '<int:object_id>/storyboard/',
                self.admin_site.admin_view(self.storyboard_view),
                name='diffusion_tvspotversion_storyboard',
            ),
        ]
        return custom_urls + urls

    def change_form_buttons(self, request, obj=None, add=False):
        """Add custom storyboard buttons to the change form."""
        buttons = super().change_form_buttons(request, obj, add)

        if obj and not add and obj.script_rows.exists():
            # Add View Storyboard button if there are any storyboard images
            has_storyboard = obj.storyboard_jobs.filter(
                images__diffusion_job__result_images__len__gt=0
            ).exists()

            if has_storyboard:
                buttons.append({
                    'title': 'View Storyboard',
                    'url': reverse('admin:diffusion_tvspotversion_storyboard', args=[obj.pk]),
                    'attrs': {
                        'class': 'button',
                    }
                })

            buttons.append({
                'title': 'Generate Storyboard',
                'url': reverse('admin:diffusion_tvspotversion_generate_storyboard', args=[obj.pk]),
                'attrs': {
                    'class': 'button',
                }
            })

        return buttons

    def generate_storyboard_view(self, request, object_id):
        """Handle generating a storyboard for a TV spot version."""
        from django.template.response import TemplateResponse
        from .tasks import generate_storyboard_task

        version = TvSpotVersion.objects.get(pk=object_id)

        if not version.script_rows.exists():
            messages.error(request, 'No script rows found for this version.')
            return redirect('admin:diffusion_tvspotversion_change', object_id)

        if request.method == 'POST':
            model_id = request.POST.get('diffusion_model')
            lora_id = request.POST.get('lora_model') or None
            images_per_row = int(request.POST.get('images_per_row', 1))
            enhance_prompts = request.POST.get('enhance_prompts') == 'on'

            if not model_id:
                messages.error(request, 'Please select a diffusion model.')
                return redirect('admin:diffusion_tvspotversion_generate_storyboard', object_id)

            # Create StoryboardJob
            storyboard_job = StoryboardJob.objects.create(
                tv_spot_version=version,
                diffusion_model_id=model_id,
                lora_model_id=lora_id,
                images_per_row=images_per_row,
                status='pending',
            )

            # Queue the storyboard generation task
            generate_storyboard_task.apply_async(
                args=[storyboard_job.pk, enhance_prompts],
                queue='enhancement'
            )

            total_images = version.script_rows.count() * images_per_row
            messages.success(
                request,
                f"Storyboard generation queued ({total_images} images). "
                f"Check the Storyboard Jobs page for progress."
            )
            return redirect('admin:diffusion_storyboardjob_change', storyboard_job.pk)

        # Get available models and LoRAs
        models = DiffusionModel.objects.filter(is_active=True)
        loras = LoraModel.objects.filter(is_active=True)

        existing_jobs = version.storyboard_jobs.all().select_related('diffusion_model')

        return TemplateResponse(
            request,
            'admin/diffusion/tvspotversion/generate_storyboard.html',
            {
                **self.admin_site.each_context(request),
                'title': _('Generate Storyboard'),
                'opts': self.model._meta,
                'version': version,
                'models': models,
                'loras': loras,
                'existing_jobs': existing_jobs,
            },
        )

    def storyboard_view(self, request, object_id):
        """Display the storyboard viewer for a TV spot version."""
        from django.template.response import TemplateResponse
        from django.conf import settings as django_settings
        import os

        version = TvSpotVersion.objects.get(pk=object_id)

        # Get the most recent storyboard job
        storyboard_job = version.storyboard_jobs.order_by('-created_at').first()

        # Build frame data from storyboard images
        frames = []
        completed_count = 0
        processing_count = 0
        pending_count = 0

        if storyboard_job:
            for image in storyboard_job.images.all().select_related(
                'script_row', 'diffusion_job'
            ).order_by('script_row__order_index', 'image_index'):
                diffusion_job = image.diffusion_job
                script_row = image.script_row

                # Get image URL if completed
                image_url = None
                if diffusion_job.result_images:
                    # Get the first image path
                    img_path = diffusion_job.result_images[0]
                    image_url = os.path.join(django_settings.MEDIA_URL, img_path)

                # Track status counts
                if diffusion_job.status == 'completed':
                    completed_count += 1
                elif diffusion_job.status == 'processing':
                    processing_count += 1
                else:
                    pending_count += 1

                frames.append({
                    'shot_number': script_row.shot_number or f"{script_row.order_index + 1:02d}",
                    'visual_text': script_row.visual_text,
                    'audio_text': script_row.audio_text,
                    'image_url': image_url,
                    'status': diffusion_job.status,
                    'image_index': image.image_index,
                })

        return TemplateResponse(
            request,
            'admin/diffusion/tvspotversion/storyboard_view.html',
            {
                **self.admin_site.each_context(request),
                'title': _('Storyboard'),
                'opts': self.model._meta,
                'version': version,
                'storyboard_job': storyboard_job,
                'frames': frames,
                'completed_count': completed_count,
                'processing_count': processing_count,
                'pending_count': pending_count,
            },
        )


# ---------------------------------------------------------------------------
# StoryboardJob
# ---------------------------------------------------------------------------

class StoryboardImageInline(TabularInline):
    """Inline display of images for StoryboardJob."""
    model = StoryboardImage
    extra = 0
    fields = ['script_row', 'image_index', 'diffusion_job', 'show_status']
    readonly_fields = ['script_row', 'image_index', 'diffusion_job', 'show_status']
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    @display(description=_("Status"))
    def show_status(self, obj):
        return obj.diffusion_job.get_status_display() if obj.diffusion_job else "—"


@admin.register(StoryboardJob)
class StoryboardJobAdmin(ModelAdmin):
    list_display = ['show_id', 'show_version', 'diffusion_model', 'lora_model', 'images_per_row', 'show_status', 'created_at']
    list_filter = ['status', 'diffusion_model', 'tv_spot_version__tv_spot']
    search_fields = ['tv_spot_version__tv_spot__script_title', 'tv_spot_version__code']
    readonly_fields = ['created_at', 'completed_at']
    inlines = [StoryboardImageInline]

    fieldsets = (
        (_("Configuration"), {
            "classes": ["tab"],
            "fields": (
                'tv_spot_version',
                ('diffusion_model', 'lora_model'),
                'images_per_row',
            ),
        }),
        (_("Status"), {
            "classes": ["tab"],
            "fields": ('status', 'error_message'),
        }),
        (_("Timing"), {
            "classes": ["tab"],
            "fields": ('created_at', 'completed_at'),
        }),
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
