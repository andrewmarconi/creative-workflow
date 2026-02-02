#!/usr/bin/env python
"""Quick test to verify admin methods work correctly."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'queerchaos.settings')
django.setup()

from queerchaos.diffusion.models import Prompt
from queerchaos.diffusion.admin import PromptAdmin
from django.contrib.admin.sites import AdminSite

# Get a prompt
prompts = Prompt.objects.all()[:1]
if not prompts:
    print("No prompts found in database")
    exit(1)

prompt = prompts[0]
admin = PromptAdmin(Prompt, AdminSite())

# Test each list_display method
print("Testing admin methods...")
print(f"✓ preview: {admin.preview(prompt)}")
print(f"✓ has_enhancement: {admin.has_enhancement(prompt)}")
print(f"✓ jobs_count: {admin.jobs_count(prompt)}")
print(f"✓ row_actions: {admin.row_actions(prompt)[:50]}...")
print("\nAll methods work correctly!")
