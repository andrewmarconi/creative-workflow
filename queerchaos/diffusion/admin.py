"""
Django admin configuration for diffusion models.

Provides admin interface with tabs, inlines, and row actions.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.contrib import messages
from .models import DiffusionModel, LoraModel, Prompt, DiffusionJob


# Inline admin classes

class JobInline(admin.TabularInline):
    """Inline display of jobs for Prompts."""
    model = DiffusionJob
    extra = 0
    fields = ['diffusion_model', 'lora_model', 'status', 'num_images', 'created_at']
    readonly_fields = ['status', 'created_at']
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(DiffusionModel)
class DiffusionModelAdmin(admin.ModelAdmin):
    """Admin interface for Diffusion Models."""

    list_display = [
        'label', 'slug', 'pipeline', 'steps', 'guidance_scale',
        'default_resolution', 'supports_negative_prompt', 'is_active',
        'compatible_loras_count'
    ]
    list_filter = ['is_active', 'pipeline', 'supports_negative_prompt', 'dtype']
    search_fields = ['label', 'slug', 'path']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('label', 'slug', 'path', 'pipeline', 'is_active')
        }),
        ('Generation Settings', {
            'fields': (
                'steps', 'guidance_scale',
                ('default_width', 'default_height'), 'max_pixels',
                'scheduler', 'dtype', 'max_sequence_length'
            )
        }),
        ('Features', {
            'fields': ('supports_negative_prompt',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def default_resolution(self, obj):
        return f"{obj.default_width}×{obj.default_height}"
    default_resolution.short_description = "Default Size"

    def compatible_loras_count(self, obj):
        count = obj.compatible_loras.count()
        if count > 0:
            url = reverse('admin:diffusion_loramodel_changelist')
            return format_html(
                '<a href="{}?compatible_models__id__exact={}">{} LoRAs</a>',
                url, obj.id, count
            )
        return "0 LoRAs"
    compatible_loras_count.short_description = "Compatible LoRAs"


@admin.register(LoraModel)
class LoraModelAdmin(admin.ModelAdmin):
    """Admin interface for LoRA Models."""

    list_display = [
        'label', 'default_strength', 'compatible_models_list', 'is_active'
    ]
    list_filter = ['is_active', 'compatible_models']
    search_fields = ['label', 'path', 'air']
    filter_horizontal = ['compatible_models']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('label', 'path', 'air', 'is_active')
        }),
        ('Compatibility', {
            'fields': ('compatible_models',)
        }),
        ('Prompt & Settings', {
            'fields': ('prompt_suffix', 'default_strength')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def compatible_models_list(self, obj):
        models = obj.compatible_models.all()
        if models.exists():
            return ", ".join([m.label for m in models])
        return "(None)"
    compatible_models_list.short_description = "Compatible With"


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    """Admin interface for Prompts with tabs and row actions."""

    list_display = [
        'preview', 'enhancement_method', 'enhancement_style',
        'has_enhancement', 'jobs_count', 'created_at', 'row_actions'
    ]
    list_filter = ['enhancement_method', 'enhancement_style', 'created_at']
    search_fields = ['source_prompt', 'enhanced_prompt']
    readonly_fields = ['created_at', 'updated_at', 'enhancement_method']
    actions = ['enhance_prompts_action', 'create_job_for_prompts']
    inlines = [JobInline]

    # Use tabs for better organization
    fieldsets = (
        ('Original Prompt', {
            'fields': ('source_prompt',)
        }),
        ('Enhanced Prompts', {
            'fields': ('enhanced_prompt', 'negative_prompt', 'enhancement_method')
        }),
        ('Enhancement Settings', {
            'fields': ('enhancement_style', 'creativity')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def preview(self, obj):
        text = obj.source_prompt[:60]
        if len(obj.source_prompt) > 60:
            text += "..."
        return text
    preview.short_description = "Prompt"

    def has_enhancement(self, obj):
        if obj.enhanced_prompt:
            return mark_safe('<span style="color: green;">✓ Enhanced</span>')
        return mark_safe('<span style="color: gray;">○ Not Enhanced</span>')
    has_enhancement.short_description = "Status"

    def jobs_count(self, obj):
        count = obj.jobs.count()
        if count > 0:
            url = reverse('admin:diffusion_diffusionjob_changelist')
            return format_html(
                '<a href="{}?prompt__id__exact={}">{} jobs</a>',
                url, obj.id, count
            )
        return "0"
    jobs_count.short_description = "Jobs"

    def row_actions(self, obj):
        """Row-level actions for individual prompts."""
        actions = []

        # Enhance action
        if not obj.enhanced_prompt:
            enhance_url = reverse('admin:diffusion_prompt_enhance', args=[obj.pk])
            actions.append(
                f'<a class="button" href="{enhance_url}" '
                f'style="padding: 5px 10px; background: #417690; color: white; '
                f'text-decoration: none; border-radius: 3px; font-size: 11px;">Enhance</a>'
            )

        # Create job action
        create_job_url = reverse('admin:diffusion_prompt_createjob', args=[obj.pk])
        actions.append(
            f'<a class="button" href="{create_job_url}" '
            f'style="padding: 5px 10px; background: #28a745; color: white; '
            f'text-decoration: none; border-radius: 3px; font-size: 11px;">Create Job</a>'
        )

        return mark_safe(' '.join(actions))
    row_actions.short_description = "Actions"

    def get_urls(self):
        """Add custom URLs for row actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:prompt_id>/enhance/',
                self.admin_site.admin_view(self.enhance_single_prompt),
                name='diffusion_prompt_enhance',
            ),
            path(
                '<int:prompt_id>/create-job/',
                self.admin_site.admin_view(self.create_job_for_prompt),
                name='diffusion_prompt_createjob',
            ),
        ]
        return custom_urls + urls

    def enhance_single_prompt(self, request, prompt_id):
        """Row action: Queue a single prompt for enhancement."""
        from . import tasks

        prompt = Prompt.objects.get(id=prompt_id)
        if prompt.enhanced_prompt:
            messages.warning(request, f"Prompt is already enhanced.")
        else:
            tasks.enhance_prompt_task.apply_async(args=[prompt_id], queue='enhancement')
            messages.success(request, f"Prompt queued for enhancement.")

        return redirect('admin:diffusion_prompt_change', prompt_id)

    def create_job_for_prompt(self, request, prompt_id):
        """Row action: Create a new job for this prompt."""
        return redirect(
            f"{reverse('admin:diffusion_diffusionjob_add')}?prompt={prompt_id}"
        )

    @admin.action(description="Enhance selected prompts")
    def enhance_prompts_action(self, request, queryset):
        """Bulk action: Queue selected prompts for enhancement."""
        from . import tasks

        count = 0
        for prompt in queryset:
            if not prompt.enhanced_prompt:
                tasks.enhance_prompt_task.apply_async(args=[prompt.id], queue='enhancement')
                count += 1

        self.message_user(
            request,
            f"{count} prompts queued for enhancement."
        )

    @admin.action(description="Create diffusion jobs for selected prompts")
    def create_job_for_prompts(self, request, queryset):
        """Bulk action: Create jobs for selected prompts."""
        prompt_ids = ','.join(str(p.id) for p in queryset)
        return redirect(
            f"{reverse('admin:diffusion_diffusionjob_add')}?prompts={prompt_ids}"
        )


@admin.register(DiffusionJob)
class DiffusionJobAdmin(admin.ModelAdmin):
    """Admin interface for Diffusion Jobs with row actions."""

    list_display = [
        'job_id', 'status_badge', 'diffusion_model', 'lora_model',
        'prompt_preview', 'num_images', 'created_at', 'duration', 'row_actions'
    ]
    list_filter = ['status', 'diffusion_model', 'lora_model', 'created_at']
    search_fields = ['rq_job_id', 'prompt__source_prompt']
    readonly_fields = [
        'rq_job_id', 'status', 'created_at', 'started_at', 'completed_at',
        'result_images_display', 'duration'
    ]
    actions = ['queue_jobs_action', 'cancel_jobs_action', 'retry_failed_jobs']

    fieldsets = (
        ('Job Configuration', {
            'fields': (
                'diffusion_model', 'lora_model', 'prompt'
            )
        }),
        ('Generation Parameters (Optional Overrides)', {
            'fields': (
                ('width', 'height'), 'steps', 'guidance_scale',
                'lora_strength', 'seed', 'num_images'
            ),
            'description': 'Leave blank to use model/LoRA defaults'
        }),
        ('Status & Results', {
            'fields': (
                'status', 'rq_job_id', 'result_images_display', 'error_message'
            )
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration'),
            'classes': ('collapse',)
        }),
    )

    def job_id(self, obj):
        return f"#{obj.pk}"
    job_id.short_description = "ID"

    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'queued': 'blue',
            'processing': 'orange',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'darkgray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def prompt_preview(self, obj):
        text = obj.prompt.source_prompt[:40]
        if len(obj.prompt.source_prompt) > 40:
            text += "..."
        return text
    prompt_preview.short_description = "Prompt"

    def duration(self, obj):
        if obj.started_at and obj.completed_at:
            delta = obj.completed_at - obj.started_at
            seconds = int(delta.total_seconds())
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                return f"{seconds // 60}m {seconds % 60}s"
            else:
                return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
        return "-"
    duration.short_description = "Duration"

    def result_images_display(self, obj):
        if not obj.result_images:
            return "No images"

        html_parts = []
        for img_path in obj.result_images:
            # Assuming images are stored in MEDIA_ROOT
            from django.conf import settings
            import os
            media_url = settings.MEDIA_URL
            # Convert absolute path to media URL if needed
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
    result_images_display.short_description = "Generated Images"

    @admin.action(description="Queue selected jobs for processing")
    def queue_jobs_action(self, request, queryset):
        """Queue selected jobs for processing."""
        from . import tasks

        count = 0
        for job in queryset.filter(status='pending'):
            celery_task = tasks.generate_images_task.apply_async(args=[job.id], queue='default')
            job.rq_job_id = celery_task.id
            job.status = 'queued'
            job.save()
            count += 1

        self.message_user(
            request,
            f"{count} jobs queued for processing."
        )

    @admin.action(description="Cancel selected jobs")
    def cancel_jobs_action(self, request, queryset):
        """Cancel selected jobs."""
        count = queryset.filter(
            status__in=['pending', 'queued']
        ).update(status='cancelled')

        self.message_user(
            request,
            f"{count} jobs cancelled."
        )

    def row_actions(self, obj):
        """Row-level actions for individual jobs."""
        actions = []

        # Queue action for pending jobs
        if obj.status == 'pending':
            queue_url = reverse('admin:diffusion_diffusionjob_queue', args=[obj.pk])
            actions.append(
                f'<a class="button" href="{queue_url}" '
                f'style="padding: 5px 10px; background: #417690; color: white; '
                f'text-decoration: none; border-radius: 3px; font-size: 11px;">Queue</a>'
            )

        # Retry action for failed jobs
        if obj.status == 'failed':
            retry_url = reverse('admin:diffusion_diffusionjob_retry', args=[obj.pk])
            actions.append(
                f'<a class="button" href="{retry_url}" '
                f'style="padding: 5px 10px; background: #ffc107; color: black; '
                f'text-decoration: none; border-radius: 3px; font-size: 11px;">Retry</a>'
            )

        # Cancel action for pending/queued jobs
        if obj.status in ['pending', 'queued']:
            cancel_url = reverse('admin:diffusion_diffusionjob_cancel', args=[obj.pk])
            actions.append(
                f'<a class="button" href="{cancel_url}" '
                f'style="padding: 5px 10px; background: #dc3545; color: white; '
                f'text-decoration: none; border-radius: 3px; font-size: 11px;">Cancel</a>'
            )

        return mark_safe(' '.join(actions)) if actions else '-'
    row_actions.short_description = "Actions"

    def get_urls(self):
        """Add custom URLs for row actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:job_id>/queue/',
                self.admin_site.admin_view(self.queue_single_job),
                name='diffusion_diffusionjob_queue',
            ),
            path(
                '<int:job_id>/retry/',
                self.admin_site.admin_view(self.retry_single_job),
                name='diffusion_diffusionjob_retry',
            ),
            path(
                '<int:job_id>/cancel/',
                self.admin_site.admin_view(self.cancel_single_job),
                name='diffusion_diffusionjob_cancel',
            ),
        ]
        return custom_urls + urls

    def queue_single_job(self, request, job_id):
        """Row action: Queue a single job."""
        from . import tasks
        job = DiffusionJob.objects.get(id=job_id)

        if job.status != 'pending':
            messages.warning(request, f"Job #{job_id} is not pending (status: {job.status}).")
        else:
            celery_task = tasks.generate_images_task.apply_async(args=[job_id], queue='default')
            job.rq_job_id = celery_task.id
            job.status = 'queued'
            job.save()
            messages.success(request, f"Job #{job_id} queued for processing.")

        return redirect('admin:diffusion_diffusionjob_change', job_id)

    def retry_single_job(self, request, job_id):
        """Row action: Retry a failed job."""
        from . import tasks
        job = DiffusionJob.objects.get(id=job_id)

        if job.status != 'failed':
            messages.warning(request, f"Job #{job_id} is not failed (status: {job.status}).")
        else:
            # Reset job status
            job.status = 'pending'
            job.error_message = ''
            job.rq_job_id = ''
            job.save()

            # Queue it
            celery_task = tasks.generate_images_task.apply_async(args=[job_id], queue='default')
            job.rq_job_id = celery_task.id
            job.status = 'queued'
            job.save()
            messages.success(request, f"Job #{job_id} queued for retry.")

        return redirect('admin:diffusion_diffusionjob_change', job_id)

    def cancel_single_job(self, request, job_id):
        """Row action: Cancel a job."""
        job = DiffusionJob.objects.get(id=job_id)

        if job.status not in ['pending', 'queued']:
            messages.warning(request, f"Job #{job_id} cannot be cancelled (status: {job.status}).")
        else:
            job.status = 'cancelled'
            job.save()
            messages.success(request, f"Job #{job_id} cancelled.")

        return redirect('admin:diffusion_diffusionjob_change', job_id)

    @admin.action(description="Retry failed jobs")
    def retry_failed_jobs(self, request, queryset):
        """Bulk action: Retry failed jobs."""
        from . import tasks

        count = 0
        for job in queryset.filter(status='failed'):
            # Reset status
            job.status = 'pending'
            job.error_message = ''
            job.rq_job_id = ''
            job.save()

            # Queue it
            celery_task = tasks.generate_images_task.apply_async(args=[job.id], queue='default')
            job.rq_job_id = celery_task.id
            job.status = 'queued'
            job.save()
            count += 1

        self.message_user(
            request,
            f"{count} failed jobs queued for retry."
        )

    def save_model(self, request, obj, form, change):
        """Auto-queue new jobs on save if they're pending."""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new and obj.status == 'pending':
            from . import tasks
            celery_task = tasks.generate_images_task.apply_async(args=[obj.id], queue='default')
            obj.rq_job_id = celery_task.id
            obj.status = 'queued'
            obj.save()
