"""
Django management command to import TV spot from JSON.

Usage:
    uv run manage.py import_tvspot path/to/spot.json
    uv run manage.py import_tvspot path/to/spot.json --dry-run
"""
import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from cw.diffusion.models import TvSpot, TvSpotVersion, TvSpotScriptRow
from pathlib import Path


class Command(BaseCommand):
    help = 'Import a TV spot from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to JSON file')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate only, do not create records'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        dry_run = options['dry_run']

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(f"Reading TV spot from: {file_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - validating only"))

        # Load and validate JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON: {e}")

        # Validate required fields
        errors = self._validate_json(data)
        if errors:
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  ✗ {error}"))
            raise CommandError("Validation failed")

        # Check for duplicate job_id
        job_id = data['job_id']
        if TvSpot.objects.filter(job_id=job_id).exists():
            raise CommandError(f"TV Spot with job_id '{job_id}' already exists")

        self.stdout.write(self.style.SUCCESS("  ✓ JSON validation passed"))
        self.stdout.write(f"\nTV Spot Details:")
        self.stdout.write(f"  Client: {data['client_name']}")
        self.stdout.write(f"  Title: {data['script_title']}")
        self.stdout.write(f"  TRT: {data['total_runtime_seconds']}s")
        self.stdout.write(f"  Job ID: {job_id}")
        self.stdout.write(f"  Script rows: {len(data['script_rows'])}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\nValidation complete (dry run)"))
            return

        # Create records
        with transaction.atomic():
            # Create TvSpot
            tv_spot = TvSpot.objects.create(
                client_name=data['client_name'],
                brand_name=data.get('brand_name', ''),
                script_title=data['script_title'],
                total_runtime_seconds=data['total_runtime_seconds'],
                job_id=job_id,
                notes=data.get('notes', ''),
            )
            self.stdout.write(self.style.SUCCESS(f"\n  ✓ Created TvSpot #{tv_spot.pk}"))

            # Create origin version
            version = TvSpotVersion.objects.create(
                tv_spot=tv_spot,
                version_type='origin',
                code='ORIGIN',
                name='Origin',
                language=data.get('language', 'en-US'),
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created TvSpotVersion #{version.pk} (origin)"))

            # Create script rows
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
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created {len(data['script_rows'])} script rows"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  TV Spot ID: {tv_spot.pk}")
        self.stdout.write(f"  Version ID: {version.pk}")
        self.stdout.write("=" * 60)

    def _validate_json(self, data: dict) -> list:
        """Validate JSON against expected schema. Returns list of errors."""
        errors = []

        # Required top-level fields
        required = ['client_name', 'script_title', 'total_runtime_seconds', 'job_id', 'script_rows']
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        if errors:
            return errors

        # Type validations
        if not isinstance(data['script_rows'], list):
            errors.append("script_rows must be an array")
            return errors

        if len(data['script_rows']) == 0:
            errors.append("script_rows must have at least one row")

        if not isinstance(data['total_runtime_seconds'], int) or data['total_runtime_seconds'] <= 0:
            errors.append("total_runtime_seconds must be a positive integer")

        # Validate each script row
        for idx, row in enumerate(data['script_rows']):
            if not isinstance(row, dict):
                errors.append(f"script_rows[{idx}] must be an object")
                continue
            if 'visual_text' not in row or not row['visual_text']:
                errors.append(f"script_rows[{idx}] missing or empty visual_text")
            if 'audio_text' not in row or not row['audio_text']:
                errors.append(f"script_rows[{idx}] missing or empty audio_text")

        return errors
