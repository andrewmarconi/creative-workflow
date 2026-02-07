"""Tests for insights composition functionality (Issue #44).

Tests the multi-level insights composition from:
- Region → Country → Language → Market hierarchy

Run with:
    uv run manage.py test cw.lib.tests.test_insights -v2
"""

from django.test import TestCase

from cw.core.models import Country, Language, LLMModel, Region
from cw.lib.insights import compose_insights, compose_insights_as_markdown
from cw.tvspots.models import AdaptationJob, AdaptationMarket, TvSpot, TvSpotVersion


class InsightsCompositionTest(TestCase):
    """Test insights composition from all levels."""

    def setUp(self):
        """Create test data with insights at all levels."""
        # LLM Model
        self.model = LLMModel.objects.create(
            model_id="Qwen/Qwen2.5-3B-Instruct",
            name="Qwen 2.5 3B",
        )

        # Region with insights
        self.region = Region.objects.create(
            code="NA",
            name="North America",
            insights=[
                {
                    "heading": "Regional values",
                    "points": [
                        "Direct communication preferred",
                        "Aspirational optimism resonates",
                    ],
                }
            ],
        )

        # Country with insights
        self.country = Country.objects.create(
            code="CA",
            name="Canada",
            insights=[
                {
                    "heading": "Regulatory requirements",
                    "points": [
                        "Bill 96 mandates French text size",
                        "CASL requires opt-in for commercial messages",
                    ],
                }
            ],
        )
        self.country.regions.add(self.region)

        # Language with insights
        self.language = Language.objects.create(
            code="fr-CA",
            name="French (Quebec)",
            base_language="fr",
            primary_model=self.model,
            insights=[
                {
                    "heading": "Vocabulary differences",
                    "points": [
                        "Car: 'char' (QC) vs 'voiture' (FR)",
                        "Weekend: 'fin de semaine' (QC) vs 'weekend' (FR)",
                    ],
                }
            ],
        )
        self.language.countries.add(self.country, through_defaults={"is_primary": True})

        # Market with rules
        self.market = AdaptationMarket.objects.create(
            name="Quebec Premium",
            code="qc-premium",
            default_language=self.language,
            rules=[
                {
                    "heading": "Positioning strategy",
                    "points": [
                        "Emphasize quality over price",
                        "Quebec identity and heritage",
                    ],
                }
            ],
        )
        self.market.regions.add(self.region)
        self.market.countries.add(self.country)

        # TV Spot and Version
        self.tv_spot = TvSpot.objects.create(
            client_name="TestClient",
            brand_name="TestBrand",
            script_title="Test Spot",
            total_runtime_seconds=30,
            job_id="TEST-001",
        )
        self.origin_version = TvSpotVersion.objects.create(
            tv_spot=self.tv_spot,
            version_type="origin",
            code="ORIGIN",
            name="Origin",
            language=self.language,
        )

        # Adaptation Job
        self.job = AdaptationJob.objects.create(
            tv_spot=self.tv_spot,
            origin_version=self.origin_version,
            target_market=self.market,
        )

    def test_compose_insights_all_levels(self):
        """Test insights composition includes all 4 levels."""
        insights = compose_insights(self.job)

        self.assertEqual(len(insights), 4)
        self.assertEqual(insights[0]["source"], "Region: North America")
        self.assertEqual(insights[1]["source"], "Country: Canada")
        self.assertEqual(insights[2]["source"], "Language: French (Quebec)")
        self.assertEqual(insights[3]["source"], "Market: Quebec Premium")

    def test_compose_insights_markdown_format(self):
        """Test insights rendered as markdown."""
        insights = compose_insights(self.job)

        # Check region insights markdown
        region_md = insights[0]["markdown"]
        self.assertIn("### Regional values", region_md)
        self.assertIn("- Direct communication preferred", region_md)

        # Check country insights markdown
        country_md = insights[1]["markdown"]
        self.assertIn("### Regulatory requirements", country_md)
        self.assertIn("- Bill 96 mandates French text size", country_md)

    def test_compose_insights_as_markdown_full_document(self):
        """Test full markdown document generation."""
        markdown = compose_insights_as_markdown(self.job)

        self.assertIn("# Adaptation Guidance for Quebec Premium", markdown)
        self.assertIn("## Region: North America", markdown)
        self.assertIn("## Country: Canada", markdown)
        self.assertIn("## Language: French (Quebec)", markdown)
        self.assertIn("## Market: Quebec Premium", markdown)

    def test_compose_insights_partial_levels(self):
        """Test insights composition with missing levels."""
        # Create market without region/country tagging but with rules
        minimal_market = AdaptationMarket.objects.create(
            name="Test Minimal",
            code="test-min",
            default_language=self.language,
            rules=[
                {
                    "heading": "Basic rule",
                    "points": ["Keep it simple"],
                }
            ],
        )
        minimal_job = AdaptationJob.objects.create(
            tv_spot=self.tv_spot,
            origin_version=self.origin_version,
            target_market=minimal_market,
        )

        insights = compose_insights(minimal_job)

        # Should only have language and market levels
        self.assertEqual(len(insights), 2)
        sources = [i["source"] for i in insights]
        self.assertIn("Language: French (Quebec)", sources)
        self.assertIn("Market: Test Minimal", sources)

    def test_compose_insights_empty_when_no_insights(self):
        """Test composition when entities have no insights."""
        # Create minimal entities with no insights
        empty_lang = Language.objects.create(
            code="en",
            name="English",
            primary_model=self.model,
            insights=[],  # No insights
        )
        empty_market = AdaptationMarket.objects.create(
            name="Test Empty",
            code="test-empty",
            default_language=empty_lang,
            rules=[],  # No rules
        )
        empty_job = AdaptationJob.objects.create(
            tv_spot=self.tv_spot,
            origin_version=self.origin_version,
            target_market=empty_market,
        )

        insights = compose_insights(empty_job)
        self.assertEqual(len(insights), 0)

        markdown = compose_insights_as_markdown(empty_job)
        self.assertEqual(markdown, "")


class InsightsHierarchyTest(TestCase):
    """Test insights are properly inherited through hierarchy."""

    def setUp(self):
        """Create a multi-level hierarchy."""
        self.model = LLMModel.objects.create(
            model_id="Qwen/Qwen2.5-3B-Instruct",
            name="Qwen 2.5 3B",
        )

        # Create NORDICS region
        self.nordics = Region.objects.create(
            code="NORDICS",
            name="Nordic Countries",
            insights=[
                {
                    "heading": "Cultural patterns",
                    "points": ["Minimalist aesthetics", "Trust in institutions"],
                }
            ],
        )

        # Create Sweden
        self.sweden = Country.objects.create(
            code="SE",
            name="Sweden",
            insights=[
                {
                    "heading": "Swedish specifics",
                    "points": ["Lagom (moderation) philosophy", "Environmental consciousness"],
                }
            ],
        )
        self.sweden.regions.add(self.nordics)

        # Create Swedish language
        self.swedish = Language.objects.create(
            code="sv-SE",
            name="Swedish",
            base_language="sv",
            primary_model=self.model,
            insights=[
                {
                    "heading": "Language notes",
                    "points": ["Formal 'ni' rarely used in modern advertising"],
                }
            ],
        )
        self.swedish.countries.add(self.sweden, through_defaults={"is_primary": True})

    def test_insights_flow_down_hierarchy(self):
        """Test that insights from all levels are available."""
        market = AdaptationMarket.objects.create(
            name="Sweden Youth",
            code="se-youth",
            default_language=self.swedish,
            rules=[{"heading": "Youth targeting", "points": ["Authentic and informal"]}],
        )
        market.regions.add(self.nordics)
        market.countries.add(self.sweden)

        tv_spot = TvSpot.objects.create(
            client_name="Test",
            brand_name="Test",
            script_title="Test",
            total_runtime_seconds=30,
            job_id="TEST-002",
        )
        origin = TvSpotVersion.objects.create(
            tv_spot=tv_spot,
            version_type="origin",
            code="ORIGIN",
            name="Origin",
            language=self.swedish,
        )
        job = AdaptationJob.objects.create(
            tv_spot=tv_spot,
            origin_version=origin,
            target_market=market,
        )

        markdown = compose_insights_as_markdown(job)

        # Should contain insights from all levels
        self.assertIn("Minimalist aesthetics", markdown)  # Region
        self.assertIn("Lagom (moderation) philosophy", markdown)  # Country
        self.assertIn("Formal 'ni' rarely used", markdown)  # Language
        self.assertIn("Authentic and informal", markdown)  # Market
