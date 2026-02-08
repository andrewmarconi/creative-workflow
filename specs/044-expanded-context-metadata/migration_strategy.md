# Migration Strategy: TvSpotVersion.language CharField → FK

**Issue:** #44
**Last Updated:** 2026-02-06

---

## Overview

This document outlines the detailed strategy for migrating `TvSpotVersion.language` from a `CharField` storing locale codes (e.g., `"en-US"`, `"fr-CA"`) to a `ForeignKey` referencing the `Language` model.

**Critical Constraint:** **Zero data loss**. Every existing TvSpotVersion must have a valid Language reference after migration.

---

## Current State Analysis

### Existing Schema

```python
# src/cw/tvspots/models.py (BEFORE)
class TvSpotVersion(models.Model):
    # ...
    language = models.CharField(
        max_length=50,
        help_text="Primary language (e.g., 'en-US', 'es-MX', 'ja')."
    )
```

### Data Audit Required

Before migration, we need to:

1. **Inventory existing language codes**
   ```sql
   SELECT DISTINCT language, COUNT(*) as count
   FROM diffusion_tvspotversion
   GROUP BY language
   ORDER BY count DESC;
   ```

2. **Identify unmapped codes**
   - Compare existing codes against planned `data/reference_data.json` languages
   - Document any codes that don't have a matching Language entry
   - Create Language entries for missing codes (or map to closest equivalent)

---

## Migration Approach

### Strategy: Multi-Step Migration with Safety Checks

**Why multi-step?**
- Allows validation at each stage
- Enables rollback to any checkpoint
- Reduces risk of data loss
- Provides clear audit trail

### Timeline: 5 Migrations

1. **Migration 0044_add_reference_models** - Add Region, Country, Culture, Language models
2. **Migration 0045_add_language_fk_temp** - Add temporary `language_fk` field to TvSpotVersion
3. **Migration 0046_populate_language_fk** - Data migration: populate `language_fk` from `language` CharField
4. **Migration 0047_verify_language_fk** - Validation: ensure no NULLs
5. **Migration 0048_swap_language_field** - Drop CharField, rename FK to `language`

---

## Detailed Migration Steps

### Migration 1: Add Reference Models

**File:** `0044_add_reference_models.py`

```python
# Generated migration for Region, Country, Culture, Language models
# No data migration - just schema

operations = [
    migrations.CreateModel(
        name='Region',
        fields=[
            ('id', models.BigAutoField(primary_key=True)),
            ('code', models.CharField(max_length=20, unique=True)),
            ('name', models.CharField(max_length=100)),
            ('description', models.TextField(blank=True)),
            ('insights', models.JSONField(default=list)),
            ('is_active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
        ],
        options={'db_table': 'core_region'},
    ),
    # ... Country, Culture, Language, M2M through tables ...
]
```

**Post-Migration Action:**
```bash
# Seed reference data
uv run manage.py import_reference_data
```

**Verification:**
```python
from cw.core.models import Language
assert Language.objects.filter(code='en-US').exists()
assert Language.objects.filter(code='fr-CA').exists()
# ... verify all expected languages
```

---

### Migration 2: Add Temporary FK Field

**File:** `0045_add_language_fk_temp.py`

```python
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_add_reference_models'),
        ('tvspots', '0006_pipeline_fields'),  # Adjust to actual latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='tvspotversion',
            name='language_fk',
            field=models.ForeignKey(
                blank=True,
                null=True,  # Nullable during migration
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tvspot_versions_temp',
                to='core.language',
                help_text='Temporary field during migration from CharField to FK'
            ),
        ),
    ]
```

**Post-Migration State:**
- `TvSpotVersion.language` (CharField) - still populated
- `TvSpotVersion.language_fk` (FK) - NULL for all rows

---

### Migration 3: Populate FK from CharField

**File:** `0046_populate_language_fk.py`

```python
from django.db import migrations

def forward_migrate_language_codes(apps, schema_editor):
    """Map TvSpotVersion.language (CharField) → language_fk (FK)."""
    TvSpotVersion = apps.get_model('tvspots', 'TvSpotVersion')
    Language = apps.get_model('core', 'Language')

    # Track unmapped codes for reporting
    unmapped_codes = set()
    mapped_count = 0
    unmapped_count = 0

    for version in TvSpotVersion.objects.all():
        lang_code = version.language  # CharField value

        if not lang_code:
            # Skip if CharField was already empty
            continue

        try:
            # Look up Language by code
            language = Language.objects.get(code=lang_code)
            version.language_fk = language
            version.save(update_fields=['language_fk'])
            mapped_count += 1

        except Language.DoesNotExist:
            unmapped_codes.add(lang_code)
            unmapped_count += 1
            # Log but don't fail - will handle in next migration

    # Report results
    print(f"\n=== Language Migration Report ===")
    print(f"✓ Mapped: {mapped_count} versions")
    if unmapped_codes:
        print(f"✗ Unmapped codes ({unmapped_count} versions): {sorted(unmapped_codes)}")
        print(f"ACTION REQUIRED: Create Language entries for unmapped codes or map manually")
    print(f"=================================\n")


def reverse_migrate_language_codes(apps, schema_editor):
    """Rollback: Clear language_fk."""
    TvSpotVersion = apps.get_model('tvspots', 'TvSpotVersion')
    TvSpotVersion.objects.update(language_fk=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tvspots', '0045_add_language_fk_temp'),
        ('core', '0044_add_reference_models'),
    ]

    operations = [
        migrations.RunPython(
            forward_migrate_language_codes,
            reverse_migrate_language_codes,
        ),
    ]
```

**Post-Migration Actions:**

1. **If unmapped codes found:**
   ```bash
   # Create missing Language entries
   uv run manage.py shell
   >>> from cw.core.models import Language, LLMModel
   >>> qwen = LLMModel.objects.get(model_id='Qwen/Qwen2.5-7B-Instruct')
   >>> Language.objects.create(
   ...     code='pt-BR',  # Example unmapped code
   ...     name='Portuguese (Brazil)',
   ...     base_language='pt',
   ...     primary_model=qwen,
   ...     insights=[]
   ... )

   # Re-run migration
   uv run manage.py migrate tvspots 0046 --fake
   uv run manage.py migrate tvspots 0046
   ```

2. **Verification:**
   ```python
   from cw.tvspots.models import TvSpotVersion
   total = TvSpotVersion.objects.count()
   mapped = TvSpotVersion.objects.exclude(language_fk__isnull=True).count()
   print(f"Mapped: {mapped}/{total} ({mapped/total*100:.1f}%)")
   ```

---

### Migration 4: Validation

**File:** `0047_verify_language_fk.py`

```python
from django.db import migrations
from django.core.exceptions import ValidationError

def validate_language_fk_populated(apps, schema_editor):
    """Ensure all TvSpotVersion records have language_fk set."""
    TvSpotVersion = apps.get_model('tvspots', 'TvSpotVersion')

    unmapped = TvSpotVersion.objects.filter(language_fk__isnull=True)
    count = unmapped.count()

    if count > 0:
        unmapped_ids = list(unmapped.values_list('pk', flat=True)[:10])
        raise ValidationError(
            f"Migration cannot proceed: {count} TvSpotVersion records have NULL language_fk.\n"
            f"Sample IDs: {unmapped_ids}\n"
            f"ACTION: Manually map these records before continuing."
        )

    print(f"✓ Validation passed: All {TvSpotVersion.objects.count()} records have language_fk")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tvspots', '0046_populate_language_fk'),
    ]

    operations = [
        migrations.RunPython(
            validate_language_fk_populated,
            noop,
        ),
    ]
```

**If validation fails:**
```bash
# Identify unmapped records
uv run manage.py shell
>>> from cw.tvspots.models import TvSpotVersion
>>> unmapped = TvSpotVersion.objects.filter(language_fk__isnull=True)
>>> for v in unmapped:
...     print(f"ID {v.pk}: language='{v.language}' (TV Spot: {v.tv_spot.script_title})")

# Manual mapping
>>> from cw.core.models import Language
>>> fallback_lang = Language.objects.get(code='en-US')  # Fallback
>>> for v in unmapped:
...     v.language_fk = fallback_lang  # Or map appropriately
...     v.save()
```

---

### Migration 5: Swap Fields

**File:** `0048_swap_language_field.py`

**CRITICAL:** This is the point of no return (without rollback).

```python
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('tvspots', '0047_verify_language_fk'),
        ('core', '0044_add_reference_models'),
    ]

    operations = [
        # Step 1: Remove old CharField
        migrations.RemoveField(
            model_name='tvspotversion',
            name='language',
        ),

        # Step 2: Rename language_fk → language
        migrations.RenameField(
            model_name='tvspotversion',
            old_name='language_fk',
            new_name='language',
        ),

        # Step 3: Make FK non-nullable
        migrations.AlterField(
            model_name='tvspotversion',
            name='language',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tvspot_versions',
                to='core.language',
                help_text='Language for this version'
            ),
        ),
    ]
```

**Post-Migration State:**
- `TvSpotVersion.language` is now a ForeignKey
- Old CharField data is gone (but backed up in previous migrations table history)

**Verification:**
```python
from cw.tvspots.models import TvSpotVersion
v = TvSpotVersion.objects.first()
assert hasattr(v.language, 'code')  # Should be Language object
assert v.language.code in ['en-US', 'fr-CA', ...]  # Should be valid locale
print(f"✓ Migration complete: language is {type(v.language)}")
```

---

## Rollback Procedures

### Rollback from Migration 5 (After Swap)

**Difficulty:** Hard (requires recreating CharField from FK)

```python
# Create reverse migration
# 0049_rollback_language_fk.py

operations = [
    # Add back CharField (nullable initially)
    migrations.AddField(
        model_name='tvspotversion',
        name='language_char',
        field=models.CharField(max_length=50, null=True, blank=True),
    ),

    # Data migration: FK → CharField
    migrations.RunPython(
        lambda apps, schema_editor: ...,  # Populate language_char from language.code
        migrations.RunPython.noop
    ),

    # Remove FK
    migrations.RemoveField(
        model_name='tvspotversion',
        name='language',
    ),

    # Rename CharField back
    migrations.RenameField(
        model_name='tvspotversion',
        old_name='language_char',
        new_name='language',
    ),
]
```

### Rollback from Migrations 2-4 (Before Swap)

**Difficulty:** Easy (just remove temp FK)

```bash
uv run manage.py migrate tvspots 0044  # Roll back to before temp FK added
```

---

## Testing Strategy

### Pre-Migration Testing (Staging)

1. **Copy production data to staging**
   ```bash
   pg_dump production_db | psql staging_db
   ```

2. **Run migrations on staging**
   ```bash
   uv run manage.py migrate
   ```

3. **Verify data integrity**
   ```python
   # Check all versions have language FK
   assert TvSpotVersion.objects.filter(language__isnull=True).count() == 0

   # Check language codes match
   for v in TvSpotVersion.objects.all()[:100]:
       # Compare against backed-up CharField values if possible
       pass
   ```

4. **Performance testing**
   ```python
   # Query with FK join
   import time
   start = time.time()
   versions = list(TvSpotVersion.objects.select_related('language').all())
   print(f"Query time: {time.time() - start:.2f}s")
   ```

### Post-Migration Testing (Production)

1. **Smoke tests**
   - Admin UI loads without errors
   - Can create new TvSpotVersion with language selection
   - Existing versions display correctly

2. **Integration tests**
   - Run adaptation job end-to-end
   - Verify language.code used correctly in library code
   - Test pipeline with language insights

---

## Backup Strategy

### Before Migration

```bash
# Full database backup
pg_dump generative_creative_lab > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# Table-specific backups
pg_dump -t diffusion_tvspotversion generative_creative_lab > tvspotversion_backup.sql
pg_dump -t core_language generative_creative_lab > language_backup.sql
```

### Backup Retention

- Keep backups for 30 days minimum
- Store in separate location from database server
- Document restoration procedure

---

## Success Criteria

- [ ] All TvSpotVersion records have valid Language FK
- [ ] No NULL language references
- [ ] Query performance within acceptable range (<10% degradation)
- [ ] Admin UI functional
- [ ] Adaptation jobs running successfully
- [ ] Rollback tested and documented

---

## Communication Plan

### Before Migration

**Email to team (3 days prior):**
> Subject: Database Migration Scheduled - TvSpot Language Refactoring
>
> We'll be migrating the TvSpotVersion.language field from text to relational data on [DATE] at [TIME].
>
> **Impact:**
> - 15-30 minute maintenance window
> - Read-only mode during migration
> - No data loss expected
>
> **What to expect:**
> - Language selection in admin will be dropdown (not text input)
> - Better validation and LLM model recommendations
>
> **Rollback plan available if issues occur.**

### During Migration

- Slack updates every 5 minutes
- Error notifications to engineering channel

### After Migration

**Email to team:**
> Subject: Migration Complete - New Language Features Available
>
> ✓ Migration successful
> ✓ All data verified
> ✓ New features:
>   - Language insights and recommendations
>   - Locale-specific language codes (en-US, fr-CA, etc.)
>   - Better LLM model selection
>
> Documentation: [link]

---

## References

- [PRD](./prd.md)
- [Data Model](./data_model.md)
- [Implementation Plan](./implementation_plan.md)
- [Django Migrations Documentation](https://docs.djangoproject.com/en/5.0/topics/migrations/)
