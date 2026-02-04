"""
Django management command to import adaptation markets from specs.

Usage:
    uv run manage.py import_markets
    uv run manage.py import_markets --dry-run
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from cw.diffusion.models import AdaptationMarket
from pathlib import Path
import re


class Command(BaseCommand):
    help = 'Import adaptation markets from specs/005_adaptations/adaptation_rules.md'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='specs/005_adaptations/adaptation_rules.md',
            help='Path to adaptation_rules.md'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        dry_run = options['dry_run']

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(f"Reading markets from: {file_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        # Parse the markdown file
        markets = self._parse_adaptation_rules(file_path)

        if not markets:
            raise CommandError("No markets found in file")

        self.stdout.write(f"Found {len(markets)} markets to import\n")

        if dry_run:
            for market in markets:
                self.stdout.write(f"  Would create: {market['name']} ({market['code']})")
            return

        # Import within transaction
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for market_data in markets:
                market, created = AdaptationMarket.objects.update_or_create(
                    code=market_data['code'],
                    defaults={
                        'name': market_data['name'],
                        'rules': market_data['rules'],
                        'is_active': True,
                    }
                )

                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Created: {market.name}"))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"  ↻ Updated: {market.name}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Updated: {updated_count}")
        self.stdout.write("=" * 60)

    def _parse_adaptation_rules(self, file_path: Path) -> list:
        """Parse adaptation_rules.md into market dicts."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Define markets with their codes and section headers
        market_mappings = [
            ('US Hispanic', 'us-hispanic', '## US Hispanic Market'),
            ('French & Benelux', 'fr-benelux', '## 2. French & Benelux Market'),
            ('Turkish', 'tr', '## 3. Turkish Market'),
            ('Japanese', 'jp', '## 4. Japanese Market'),
            ('South Korean', 'kr', '## 5. South Korean Market'),
        ]

        markets = []

        for name, code, section_header in market_mappings:
            # Find section start
            start_idx = content.find(section_header)
            if start_idx == -1:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Section not found: {section_header}")
                )
                continue

            # Find next section (or end of file)
            remaining = content[start_idx + len(section_header):]
            next_section_match = re.search(r'\n## \d+\.', remaining)
            if next_section_match:
                rules_text = remaining[:next_section_match.start()]
            else:
                rules_text = remaining

            markets.append({
                'name': name,
                'code': code,
                'rules': rules_text.strip(),
            })

        return markets
