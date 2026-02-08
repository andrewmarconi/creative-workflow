"""Tests for core dimensional models (Issue #44).

Tests the Region, Country, Language models and their relationships.

Run with:
    uv run manage.py test cw.core.tests.test_models -v2
"""

from django.test import TestCase

from cw.audiences.models import Country, Language, Region
from cw.core.models import LLMModel


class RegionModelTest(TestCase):
    """Test Region model and insights rendering."""

    def setUp(self):
        """Create test region with insights."""
        self.region = Region.objects.create(
            code="NA",
            name="North America",
            insights=[
                {
                    "heading": "Cultural values",
                    "points": [
                        "Direct communication preferred",
                        "Aspirational optimism resonates",
                    ],
                }
            ],
        )

    def test_region_creation(self):
        """Test region is created with correct attributes."""
        self.assertEqual(self.region.code, "NA")
        self.assertEqual(self.region.name, "North America")
        self.assertEqual(len(self.region.insights), 1)

    def test_region_insights_as_markdown(self):
        """Test insights_as_markdown renders correctly."""
        markdown = self.region.insights_as_markdown()
        self.assertIn("### Cultural values", markdown)
        self.assertIn("- Direct communication preferred", markdown)
        self.assertIn("- Aspirational optimism resonates", markdown)

    def test_region_empty_insights(self):
        """Test region with empty insights returns empty markdown."""
        empty_region = Region.objects.create(
            code="EU",
            name="Europe",
            insights=[],
        )
        self.assertEqual(empty_region.insights_as_markdown(), "")

    def test_region_str_representation(self):
        """Test string representation."""
        self.assertEqual(str(self.region), "North America (NA)")


class CountryModelTest(TestCase):
    """Test Country model and relationships."""

    def setUp(self):
        """Create test country with region."""
        self.region = Region.objects.create(
            code="NA",
            name="North America",
        )
        self.country = Country.objects.create(
            code="CA",
            name="Canada",
            insights=[
                {
                    "heading": "Regulatory requirements",
                    "points": ["Bill 96 mandates French text size"],
                }
            ],
        )
        self.country.regions.add(self.region)

    def test_country_creation(self):
        """Test country is created with correct attributes."""
        self.assertEqual(self.country.code, "CA")
        self.assertEqual(self.country.name, "Canada")

    def test_country_region_relationship(self):
        """Test M2M relationship with regions."""
        self.assertIn(self.region, self.country.regions.all())
        self.assertIn(self.country, self.region.countries.all())

    def test_country_insights_as_markdown(self):
        """Test insights rendering."""
        markdown = self.country.insights_as_markdown()
        self.assertIn("### Regulatory requirements", markdown)
        self.assertIn("- Bill 96 mandates French text size", markdown)

    def test_country_str_representation(self):
        """Test string representation."""
        self.assertEqual(str(self.country), "Canada (CA)")


class LanguageModelTest(TestCase):
    """Test Language model and relationships."""

    def setUp(self):
        """Create test language with models and countries."""
        self.primary_model = LLMModel.objects.create(
            model_id="Qwen/Qwen2.5-3B-Instruct",
            name="Qwen 2.5 3B",
        )
        self.alt_model = LLMModel.objects.create(
            model_id="Qwen/Qwen2.5-7B-Instruct",
            name="Qwen 2.5 7B",
        )
        self.country = Country.objects.create(code="CA", name="Canada")
        self.language = Language.objects.create(
            code="fr-CA",
            name="French (Quebec)",
            base_language="fr",
            primary_model=self.primary_model,
            insights=[
                {
                    "heading": "Vocabulary differences",
                    "points": ["Car: 'char' (QC) vs 'voiture' (FR)"],
                }
            ],
        )
        self.language.alternative_models.add(self.alt_model)
        self.language.countries.add(self.country, through_defaults={"is_primary": True})

    def test_language_creation(self):
        """Test language is created with correct attributes."""
        self.assertEqual(self.language.code, "fr-CA")
        self.assertEqual(self.language.name, "French (Quebec)")
        self.assertEqual(self.language.base_language, "fr")
        self.assertEqual(self.language.primary_model, self.primary_model)

    def test_language_alternative_models(self):
        """Test alternative_models M2M relationship."""
        alts = self.language.alternative_models.all()
        self.assertEqual(alts.count(), 1)
        self.assertIn(self.alt_model, alts)

    def test_language_country_relationship(self):
        """Test M2M relationship with countries through CountryLanguage."""
        countries = self.language.countries.all()
        self.assertEqual(countries.count(), 1)
        self.assertIn(self.country, countries)

        # Check is_primary flag
        from cw.core.models import CountryLanguage

        cl = CountryLanguage.objects.get(language=self.language, country=self.country)
        self.assertTrue(cl.is_primary)

    def test_language_insights_rendering(self):
        """Test insights markdown rendering."""
        markdown = self.language.insights_as_markdown()
        self.assertIn("### Vocabulary differences", markdown)
        self.assertIn("- Car: 'char' (QC) vs 'voiture' (FR)", markdown)

    def test_language_str_representation(self):
        """Test string representation."""
        self.assertEqual(str(self.language), "French (Quebec) (fr-CA)")


class LanguageAlternativeModelTest(TestCase):
    """Test LanguageAlternativeModel through table."""

    def setUp(self):
        """Create language with multiple alternative models."""
        self.primary = LLMModel.objects.create(
            model_id="primary/model", name="Primary"
        )
        self.alt1 = LLMModel.objects.create(model_id="alt/model1", name="Alt 1")
        self.alt2 = LLMModel.objects.create(model_id="alt/model2", name="Alt 2")
        self.language = Language.objects.create(
            code="en", name="English", primary_model=self.primary
        )

    def test_add_alternative_models(self):
        """Test adding alternative models."""
        from cw.core.models import LanguageAlternativeModel

        LanguageAlternativeModel.objects.create(
            language=self.language, llmmodel=self.alt1
        )
        LanguageAlternativeModel.objects.create(
            language=self.language, llmmodel=self.alt2
        )

        # Verify both alternatives added
        alts = self.language.alternative_models.all()
        self.assertEqual(alts.count(), 2)
        self.assertIn(self.alt1, alts)
        self.assertIn(self.alt2, alts)

    def test_unique_constraint(self):
        """Test unique constraint on language+llmmodel."""
        from django.db import IntegrityError

        from cw.core.models import LanguageAlternativeModel

        LanguageAlternativeModel.objects.create(
            language=self.language, llmmodel=self.alt1
        )

        # Attempt to create duplicate should fail
        with self.assertRaises(IntegrityError):
            LanguageAlternativeModel.objects.create(
                language=self.language, llmmodel=self.alt1
            )


class CountryLanguageTest(TestCase):
    """Test CountryLanguage through table."""

    def setUp(self):
        """Create country with primary and secondary languages."""
        self.model = LLMModel.objects.create(model_id="test/model", name="Test")
        self.country = Country.objects.create(code="CA", name="Canada")
        self.english = Language.objects.create(
            code="en-CA", name="English (Canada)", primary_model=self.model
        )
        self.french = Language.objects.create(
            code="fr-CA", name="French (Canada)", primary_model=self.model
        )

    def test_primary_and_secondary_languages(self):
        """Test marking languages as primary or secondary."""
        from cw.core.models import CountryLanguage

        # Add English as primary
        CountryLanguage.objects.create(
            country=self.country, language=self.english, is_primary=True
        )

        # Add French as secondary
        CountryLanguage.objects.create(
            country=self.country, language=self.french, is_primary=False
        )

        # Verify
        primary_langs = self.country.languages.filter(
            countrylanguage__is_primary=True
        )
        self.assertEqual(primary_langs.count(), 1)
        self.assertIn(self.english, primary_langs)

        secondary_langs = self.country.languages.filter(
            countrylanguage__is_primary=False
        )
        self.assertEqual(secondary_langs.count(), 1)
        self.assertIn(self.french, secondary_langs)


class MultipleInsightsSectionTest(TestCase):
    """Test models with multiple insights sections."""

    def test_multiple_sections_in_region(self):
        """Test region with multiple insight sections."""
        region = Region.objects.create(
            code="EU",
            name="Europe",
            insights=[
                {
                    "heading": "Cultural values",
                    "points": ["Privacy important", "Trust institutions"],
                },
                {
                    "heading": "Regulatory",
                    "points": ["GDPR compliance required", "Cookie consent mandatory"],
                },
            ],
        )

        markdown = region.insights_as_markdown()
        self.assertIn("### Cultural values", markdown)
        self.assertIn("### Regulatory", markdown)
        self.assertIn("- Privacy important", markdown)
        self.assertIn("- GDPR compliance required", markdown)

    def test_markdown_section_ordering(self):
        """Test that markdown sections appear in order."""
        country = Country.objects.create(
            code="DE",
            name="Germany",
            insights=[
                {"heading": "First", "points": ["Point 1"]},
                {"heading": "Second", "points": ["Point 2"]},
                {"heading": "Third", "points": ["Point 3"]},
            ],
        )

        markdown = country.insights_as_markdown()
        first_idx = markdown.find("### First")
        second_idx = markdown.find("### Second")
        third_idx = markdown.find("### Third")

        self.assertLess(first_idx, second_idx)
        self.assertLess(second_idx, third_idx)
