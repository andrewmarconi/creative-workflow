"""Tests for TVSpotAdaptation model (Issue #44).

Tests the alternative flat adaptation model with flexible dimensional tagging
and self-referential hierarchy for adaptation chains.

Run with:
    uv run manage.py test cw.tvspots.tests.test_tvspot_adaptation -v2
"""

from django.test import TestCase

from cw.core.models import Country, Language, LLMModel, Region
from cw.tvspots.models import TVSpotAdaptation


class TVSpotAdaptationCreationTest(TestCase):
    """Test basic TVSpotAdaptation creation and fields."""

    def setUp(self):
        """Create minimal test data."""
        self.model = LLMModel.objects.create(
            model_id="Qwen/Qwen2.5-3B-Instruct",
            name="Qwen 2.5 3B",
        )
        self.language = Language.objects.create(
            code="en-US",
            name="English (United States)",
            base_language="en",
            primary_model=self.model,
        )

    def test_minimal_adaptation_creation(self):
        """Test creating adaptation with minimal required fields."""
        adaptation = TVSpotAdaptation.objects.create(
            job_id="TEST-001",
            title="Global Master",
            script_data={
                "client_name": "TestClient",
                "brand_name": "TestBrand",
                "script_rows": [],
            },
        )

        self.assertEqual(adaptation.job_id, "TEST-001")
        self.assertEqual(adaptation.title, "Global Master")
        self.assertIsNotNone(adaptation.script_data)
        self.assertIsNone(adaptation.source_adaptation)
        self.assertIsNone(adaptation.region)
        self.assertIsNone(adaptation.country)
        self.assertIsNone(adaptation.language)

    def test_adaptation_with_dimensional_tagging(self):
        """Test creating adaptation with full dimensional context."""
        region = Region.objects.create(code="EU", name="Europe")
        country = Country.objects.create(code="DE", name="Germany")
        country.regions.add(region)

        adaptation = TVSpotAdaptation.objects.create(
            job_id="TEST-002",
            title="German Adaptation",
            region=region,
            country=country,
            language=self.language,
            script_data={"script_rows": []},
        )

        self.assertEqual(adaptation.region, region)
        self.assertEqual(adaptation.country, country)
        self.assertEqual(adaptation.language, self.language)

    def test_adaptation_unique_job_id(self):
        """Test job_id uniqueness constraint."""
        from django.db import IntegrityError

        TVSpotAdaptation.objects.create(
            job_id="UNIQUE-001",
            title="First",
            script_data={},
        )

        # Attempt to create duplicate job_id should fail
        with self.assertRaises(IntegrityError):
            TVSpotAdaptation.objects.create(
                job_id="UNIQUE-001",
                title="Second",
                script_data={},
            )

    def test_adaptation_str_representation(self):
        """Test string representation returns title."""
        adaptation = TVSpotAdaptation.objects.create(
            job_id="TEST-003",
            title="My Adaptation Title",
            script_data={},
        )
        self.assertEqual(str(adaptation), "My Adaptation Title")


class TVSpotAdaptationChainTest(TestCase):
    """Test self-referential hierarchy and adaptation chains."""

    def setUp(self):
        """Create a chain of adaptations."""
        # Root adaptation (no parent)
        self.root = TVSpotAdaptation.objects.create(
            job_id="ROOT-001",
            title="Global Master",
            script_data={"version": "root"},
        )

        # Regional adaptation (parent = root)
        self.regional = TVSpotAdaptation.objects.create(
            job_id="REGIONAL-001",
            title="European Adaptation",
            source_adaptation=self.root,
            script_data={"version": "regional"},
        )

        # Country adaptation (parent = regional)
        self.country = TVSpotAdaptation.objects.create(
            job_id="COUNTRY-001",
            title="German Adaptation",
            source_adaptation=self.regional,
            script_data={"version": "country"},
        )

        # Language variant (parent = country)
        self.language_variant = TVSpotAdaptation.objects.create(
            job_id="LANG-001",
            title="German Swiss Variant",
            source_adaptation=self.country,
            script_data={"version": "language"},
        )

    def test_get_adaptation_chain_root(self):
        """Test adaptation chain for root node."""
        chain = self.root.get_adaptation_chain()
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0], self.root)

    def test_get_adaptation_chain_deep(self):
        """Test adaptation chain for deep nested node."""
        chain = self.language_variant.get_adaptation_chain()
        self.assertEqual(len(chain), 4)
        self.assertEqual(chain[0], self.root)
        self.assertEqual(chain[1], self.regional)
        self.assertEqual(chain[2], self.country)
        self.assertEqual(chain[3], self.language_variant)

    def test_get_depth_root(self):
        """Test depth calculation for root node."""
        self.assertEqual(self.root.get_depth(), 0)

    def test_get_depth_nested(self):
        """Test depth calculation for nested nodes."""
        self.assertEqual(self.regional.get_depth(), 1)
        self.assertEqual(self.country.get_depth(), 2)
        self.assertEqual(self.language_variant.get_depth(), 3)

    def test_child_adaptations_relationship(self):
        """Test reverse relationship from parent to children."""
        children = self.root.child_adaptations.all()
        self.assertEqual(children.count(), 1)
        self.assertIn(self.regional, children)

        regional_children = self.regional.child_adaptations.all()
        self.assertEqual(regional_children.count(), 1)
        self.assertIn(self.country, regional_children)

    def test_multiple_children(self):
        """Test adaptation with multiple child branches."""
        # Create sibling adaptations from regional
        german_alt = TVSpotAdaptation.objects.create(
            job_id="COUNTRY-002",
            title="German Alt Adaptation",
            source_adaptation=self.regional,
            script_data={},
        )
        french = TVSpotAdaptation.objects.create(
            job_id="COUNTRY-003",
            title="French Adaptation",
            source_adaptation=self.regional,
            script_data={},
        )

        children = self.regional.child_adaptations.all()
        self.assertEqual(children.count(), 3)  # country + german_alt + french
        self.assertIn(self.country, children)
        self.assertIn(german_alt, children)
        self.assertIn(french, children)


class TVSpotAdaptationDeletionTest(TestCase):
    """Test deletion behavior with SET_NULL on source_adaptation."""

    def test_parent_deletion_sets_null(self):
        """Test that deleting parent sets source_adaptation to NULL on children."""
        parent = TVSpotAdaptation.objects.create(
            job_id="PARENT-001",
            title="Parent",
            script_data={},
        )
        child = TVSpotAdaptation.objects.create(
            job_id="CHILD-001",
            title="Child",
            source_adaptation=parent,
            script_data={},
        )

        # Delete parent
        parent.delete()

        # Child should still exist with NULL source_adaptation
        child.refresh_from_db()
        self.assertIsNone(child.source_adaptation)

    def test_chain_after_middle_deletion(self):
        """Test adaptation chain after deleting middle node."""
        root = TVSpotAdaptation.objects.create(
            job_id="ROOT-002",
            title="Root",
            script_data={},
        )
        middle = TVSpotAdaptation.objects.create(
            job_id="MIDDLE-001",
            title="Middle",
            source_adaptation=root,
            script_data={},
        )
        leaf = TVSpotAdaptation.objects.create(
            job_id="LEAF-001",
            title="Leaf",
            source_adaptation=middle,
            script_data={},
        )

        # Delete middle node
        middle.delete()

        # Leaf should have NULL parent now
        leaf.refresh_from_db()
        self.assertIsNone(leaf.source_adaptation)

        # Leaf's chain should only contain itself
        chain = leaf.get_adaptation_chain()
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0], leaf)


class TVSpotAdaptationWithDimensionsTest(TestCase):
    """Test interactions between adaptations and dimensional models."""

    def setUp(self):
        """Create dimensional reference data."""
        self.model = LLMModel.objects.create(
            model_id="Qwen/Qwen2.5-3B-Instruct",
            name="Qwen 2.5 3B",
        )
        self.region = Region.objects.create(code="NORDICS", name="Nordic Countries")
        self.country = Country.objects.create(code="SE", name="Sweden")
        self.country.regions.add(self.region)
        self.language = Language.objects.create(
            code="sv-SE",
            name="Swedish",
            base_language="sv",
            primary_model=self.model,
        )
        self.language.countries.add(self.country, through_defaults={"is_primary": True})

    def test_dimensional_reverse_relationships(self):
        """Test reverse relationships from dimensions to adaptations."""
        adaptation = TVSpotAdaptation.objects.create(
            job_id="NORDIC-001",
            title="Nordic Adaptation",
            region=self.region,
            country=self.country,
            language=self.language,
            script_data={},
        )

        # Test reverse relationships
        self.assertIn(adaptation, self.region.adaptations.all())
        self.assertIn(adaptation, self.country.adaptations.all())
        self.assertIn(adaptation, self.language.adaptations.all())

    def test_protect_deletion_of_referenced_dimensions(self):
        """Test PROTECT constraint prevents deletion of referenced dimensions."""
        from django.db import IntegrityError

        adaptation = TVSpotAdaptation.objects.create(
            job_id="PROTECTED-001",
            title="Protected Adaptation",
            region=self.region,
            country=self.country,
            language=self.language,
            script_data={},
        )

        # Attempt to delete referenced region should fail
        with self.assertRaises(IntegrityError):
            self.region.delete()

        # Attempt to delete referenced country should fail
        with self.assertRaises(IntegrityError):
            self.country.delete()

        # Attempt to delete referenced language should fail
        with self.assertRaises(IntegrityError):
            self.language.delete()


class TVSpotAdaptationScriptDataTest(TestCase):
    """Test script_data JSON field handling."""

    def test_script_data_structure(self):
        """Test storing complex script data as JSON."""
        script_data = {
            "client_name": "Acme Corp",
            "brand_name": "SuperProduct",
            "script_title": "Launch Campaign",
            "total_runtime_seconds": 30,
            "script_rows": [
                {
                    "shot_number": "01",
                    "timecode_start": "00:00:00:00",
                    "duration_seconds": 5.0,
                    "visual_text": "Product hero shot",
                    "audio_text": "VO: Introducing SuperProduct",
                },
                {
                    "shot_number": "02",
                    "timecode_start": "00:00:05:00",
                    "duration_seconds": 10.0,
                    "visual_text": "Product in action",
                    "audio_text": "Music: upbeat instrumental",
                },
            ],
        }

        adaptation = TVSpotAdaptation.objects.create(
            job_id="SCRIPT-001",
            title="Script Test",
            script_data=script_data,
        )

        # Verify structure is preserved
        self.assertEqual(adaptation.script_data["client_name"], "Acme Corp")
        self.assertEqual(len(adaptation.script_data["script_rows"]), 2)
        self.assertEqual(
            adaptation.script_data["script_rows"][0]["visual_text"],
            "Product hero shot",
        )

    def test_adaptation_notes_field(self):
        """Test adaptation_notes text field."""
        notes = """
        Creative Direction:
        - Use warm color palette
        - Emphasize family values
        - Include local landmarks

        Client Feedback:
        - Approved on 2024-12-15
        - Request for subtitle adjustments
        """

        adaptation = TVSpotAdaptation.objects.create(
            job_id="NOTES-001",
            title="Notes Test",
            adaptation_notes=notes,
            script_data={},
        )

        self.assertIn("Creative Direction", adaptation.adaptation_notes)
        self.assertIn("Client Feedback", adaptation.adaptation_notes)


class TVSpotAdaptationQueryTest(TestCase):
    """Test querying and filtering adaptations."""

    def setUp(self):
        """Create test data for querying."""
        self.model = LLMModel.objects.create(
            model_id="test/model",
            name="Test Model",
        )
        self.region_na = Region.objects.create(code="NA", name="North America")
        self.region_eu = Region.objects.create(code="EU", name="Europe")
        self.country_us = Country.objects.create(code="US", name="United States")
        self.country_de = Country.objects.create(code="DE", name="Germany")
        self.country_us.regions.add(self.region_na)
        self.country_de.regions.add(self.region_eu)

        self.lang_en = Language.objects.create(
            code="en-US", name="English", primary_model=self.model
        )
        self.lang_de = Language.objects.create(
            code="de-DE", name="German", primary_model=self.model
        )

        # Create adaptations for different markets
        self.us_adaptation = TVSpotAdaptation.objects.create(
            job_id="US-001",
            title="US Campaign",
            region=self.region_na,
            country=self.country_us,
            language=self.lang_en,
            script_data={},
        )

        self.de_adaptation = TVSpotAdaptation.objects.create(
            job_id="DE-001",
            title="German Campaign",
            region=self.region_eu,
            country=self.country_de,
            language=self.lang_de,
            script_data={},
        )

    def test_filter_by_region(self):
        """Test filtering adaptations by region."""
        na_adaptations = TVSpotAdaptation.objects.filter(region=self.region_na)
        self.assertEqual(na_adaptations.count(), 1)
        self.assertIn(self.us_adaptation, na_adaptations)

    def test_filter_by_country(self):
        """Test filtering adaptations by country."""
        de_adaptations = TVSpotAdaptation.objects.filter(country=self.country_de)
        self.assertEqual(de_adaptations.count(), 1)
        self.assertIn(self.de_adaptation, de_adaptations)

    def test_filter_by_language(self):
        """Test filtering adaptations by language."""
        en_adaptations = TVSpotAdaptation.objects.filter(language=self.lang_en)
        self.assertEqual(en_adaptations.count(), 1)
        self.assertIn(self.us_adaptation, en_adaptations)

    def test_filter_root_adaptations(self):
        """Test finding root adaptations (no parent)."""
        # Create child adaptation
        TVSpotAdaptation.objects.create(
            job_id="US-002",
            title="US Variant",
            source_adaptation=self.us_adaptation,
            script_data={},
        )

        # Find all root adaptations
        roots = TVSpotAdaptation.objects.filter(source_adaptation__isnull=True)
        self.assertEqual(roots.count(), 2)  # us_adaptation, de_adaptation
        self.assertIn(self.us_adaptation, roots)
        self.assertIn(self.de_adaptation, roots)

    def test_ordering_by_created_at(self):
        """Test default ordering by created_at descending."""
        adaptations = TVSpotAdaptation.objects.all()
        # Most recent first
        self.assertEqual(adaptations[0], self.de_adaptation)
        self.assertEqual(adaptations[1], self.us_adaptation)
