"""Add ControlNet wireframe fields to Storyboard and key_frame FK to StoryboardImage.

Supports keyframe-based (ControlNet) storyboard generation alongside
the existing text-based (script row) generation.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("diffusion", "0003_add_controlnet_to_diffusionjob"),
        ("tvspots", "0012_add_celery_task_id_to_adunitmedia"),
    ]

    operations = [
        # Storyboard: source_type field
        migrations.AddField(
            model_name="storyboard",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("text", "Text (Script Rows)"),
                    ("keyframe", "Keyframe (ControlNet)"),
                ],
                default="text",
                help_text="Generate from script text or from video keyframes via ControlNet",
                max_length=20,
            ),
        ),
        # Storyboard: controlnet_model FK
        migrations.AddField(
            model_name="storyboard",
            name="controlnet_model",
            field=models.ForeignKey(
                blank=True,
                help_text="ControlNet model for keyframe-based wireframe generation",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="storyboards",
                to="diffusion.controlnetmodel",
            ),
        ),
        # Storyboard: preprocessing_type
        migrations.AddField(
            model_name="storyboard",
            name="preprocessing_type",
            field=models.CharField(
                blank=True,
                help_text="Override ControlNet's default preprocessing type",
                max_length=20,
            ),
        ),
        # Storyboard: conditioning_scale
        migrations.AddField(
            model_name="storyboard",
            name="conditioning_scale",
            field=models.FloatField(
                blank=True,
                help_text="Override ControlNet conditioning scale (0.0-2.0)",
                null=True,
            ),
        ),
        # Storyboard: control_guidance_end
        migrations.AddField(
            model_name="storyboard",
            name="control_guidance_end",
            field=models.FloatField(
                blank=True,
                help_text="Override when to stop applying ControlNet (0.0-1.0)",
                null=True,
            ),
        ),
        # Storyboard: style_prompt
        migrations.AddField(
            model_name="storyboard",
            name="style_prompt",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Visual style prompt for wireframe generation "
                    "(e.g., 'clean line drawing, architectural wireframe, black and white')"
                ),
            ),
        ),
        # StoryboardImage: key_frame FK
        migrations.AddField(
            model_name="storyboardimage",
            name="key_frame",
            field=models.ForeignKey(
                blank=True,
                help_text="Source keyframe (for wireframe/ControlNet storyboards)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="storyboard_images",
                to="tvspots.keyframe",
            ),
        ),
    ]
