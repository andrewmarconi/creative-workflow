"""
Django admin configuration for diffusion models.

Uses Django Unfold for tabs, display decorators, and styled actions.
"""
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
from django_celery_results.models import TaskResult, GroupResult
from django_celery_results.admin import TaskResultAdmin as BaseTaskResultAdmin
from django_celery_results.admin import GroupResultAdmin as BaseGroupResultAdmin
from .models import DiffusionModel, LoraModel, Prompt, DiffusionJob


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
        'label', 'slug', 'pipeline', 'steps', 'guidance_scale',
        'show_resolution', 'show_negative_prompt', 'show_active',
        'show_loras_count',
    ]
    list_filter = ['is_active', 'pipeline', 'supports_negative_prompt', 'dtype']
    search_fields = ['label', 'slug', 'path']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_("Model"), {
            "classes": ["tab"],
            "fields": ('label', 
                       ('slug', 'path'), 
                       ('pipeline', 'is_active')
                    ),
        }),
        (_("Generation"), {
            "classes": ["tab"],
            "fields": (
                ('default_width', 'default_height', 'max_pixels'),
                ('steps', 'guidance_scale', 'scheduler'), 
                ('dtype', 'max_sequence_length', 'supports_negative_prompt'),
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

    @display(description=_("Neg Prompt"), label=True)
    def show_negative_prompt(self, obj):
        return obj.supports_negative_prompt

    @display(description=_("Active"), label=True)
    def show_active(self, obj):
        return obj.is_active

    @display(description=_("LoRAs"))
    def show_loras_count(self, obj):
        count = obj.compatible_loras.count()
        if count > 0:
            url = reverse('admin:diffusion_loramodel_changelist')
            return format_html(
                '<a href="{}?compatible_models__id__exact={}">{}</a>',
                url, obj.id, count,
            )
        return "0"


# ---------------------------------------------------------------------------
# LoraModel
# ---------------------------------------------------------------------------

@admin.register(LoraModel)
class LoraModelAdmin(ModelAdmin):
    list_display = ['label', 'default_strength', 'show_compatible', 'show_active']
    list_filter = ['is_active', 'compatible_models']
    search_fields = ['label', 'path', 'air']
    filter_horizontal = ['compatible_models']
    readonly_fields = ['created_at', 'updated_at', 'show_token_counts']

    fieldsets = (
        (_("LoRA"), {
            "classes": ["tab"],
            "fields": (
                ('label', 'is_active'),
                ('path', 'air')
           ),
        }),
        (_("Compatibility"), {
            "classes": ["tab"],
            "fields": ('compatible_models',),
        }),
        (_("Prompt & Settings"), {
            "classes": ["tab"],
            "fields": (
                 'default_strength',
                 ('prompt_suffix', 'negative_prompt_suffix'),
                 'show_token_counts',
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
        models = obj.compatible_models.all()
        if models.exists():
            return ", ".join(m.label for m in models)
        return "—"

    @display(description=_("Active"), label=True)
    def show_active(self, obj):
        return obj.is_active


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
        loras = LoraModel.objects.filter(is_active=True).prefetch_related('compatible_models')

        # Attach comma-separated compatible model IDs for JS filtering
        for lora in loras:
            lora.compatible_model_ids = ','.join(
                str(m.pk) for m in lora.compatible_models.all()
            )

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
        lora_ids = list(
            LoraModel.objects.filter(
                is_active=True, compatible_models__id=model_id
            ).values_list('id', flat=True)
        )
        return JsonResponse({'lora_ids': lora_ids})

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['lora_compat_url'] = reverse(
            'admin:diffusion_diffusionjob_compatible_loras'
        )
        return super().changeform_view(request, object_id, form_url, extra_context)

    list_display = [
        'show_id', 'show_status', 'diffusion_model', 'lora_model',
        'show_prompt', 'num_images', 'created_at', 'show_duration',
    ]
    list_filter = ['status', 'diffusion_model', 'lora_model', 'created_at']
    search_fields = ['rq_job_id', 'prompt__source_prompt']
    readonly_fields = [
        'rq_job_id', 'status', 'created_at', 'started_at', 'completed_at',
        'show_result_images', 'show_duration',
    ]
    actions = ['queue_jobs_action', 'cancel_jobs_action', 'retry_failed_jobs']
    actions_row = ['queue_single_action', 'retry_single_action', 'cancel_single_action']

    fieldsets = (
        (_("Configuration"), {
            "classes": ["tab"],
            "fields": ('diffusion_model', 'lora_model', 'prompt'),
        }),
        (_("Parameters"), {
            "classes": ["tab"],
            "fields": (
                ('width', 'height'), 'steps', 'guidance_scale',
                'lora_strength', 'seed', 'num_images',
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
            "fields": ('show_result_images',),
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
