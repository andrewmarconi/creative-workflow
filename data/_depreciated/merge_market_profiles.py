#!/usr/bin/env python3
"""
Merge market_profiles.json data into reference data files.

Strategy:
1. Single-country markets → country insights
2. Multi-country linguistic zones → both region and country insights
3. Language-specific rules → language insights
"""

import json
from pathlib import Path
from typing import Dict, List, Any


def load_json(filepath: Path) -> Any:
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filepath: Path, data: Any) -> None:
    """Save JSON file with pretty formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {filepath}")


def merge_insights(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    Merge insights, avoiding duplicates.
    If a heading exists, append unique points; otherwise add the whole insight.
    """
    merged = existing.copy()

    for new_insight in new:
        # Find if this heading already exists
        existing_insight = next(
            (i for i in merged if i['heading'] == new_insight['heading']),
            None
        )

        if existing_insight:
            # Merge points, avoiding duplicates
            existing_points = set(existing_insight['points'])
            for point in new_insight['points']:
                if point not in existing_points:
                    existing_insight['points'].append(point)
        else:
            # Add new insight
            merged.append(new_insight)

    return merged


def extract_country_code_from_name(country_name: str, countries_data: List[Dict]) -> str:
    """Try to find country code from country name."""
    # Exact match first
    for country in countries_data:
        if country['name'].lower() == country_name.lower():
            return country['code']

    # Partial match
    for country in countries_data:
        if country_name.lower() in country['name'].lower() or \
           country['name'].lower() in country_name.lower():
            return country['code']

    return None


def main():
    data_dir = Path('data')

    # Load all data files
    print("Loading data files...")
    market_profiles = load_json(data_dir / 'market_profiles.json')
    countries = load_json(data_dir / 'countries.json')
    languages = load_json(data_dir / 'languages.json')
    regions = load_json(data_dir / 'regions.json')

    # Create lookup dictionaries
    countries_by_code = {c['code']: c for c in countries}
    countries_by_name = {c['name'].lower(): c for c in countries}
    languages_by_code = {l['code']: l for l in languages}
    regions_by_code = {r['code']: r for r in regions}

    # Track what we've merged
    merged_count = {'countries': 0, 'languages': 0, 'regions': 0}

    print("\nProcessing market profiles...")

    for market in market_profiles['markets']:
        market_name = market['name']
        market_code = market['code']
        rules = market['rules']

        print(f"\n→ Processing: {market_name}")

        # Convert rules to insights format (heading + points)
        insights = rules  # Already in the right format

        # Strategy 1: Single-country markets
        # These are markets where the name is essentially a country name
        single_country_markets = {
            'Japan': 'JP',
            'South Korea': 'KR',
            'Türkiye': 'TR',
            'Brazil (Brazilian Portuguese)': 'BR',
            'India (Multi-language)': 'IN',
            'Spain (European Spanish)': 'ES',
        }

        if market_name in single_country_markets:
            country_code = single_country_markets[market_name]
            if country_code in countries_by_code:
                country = countries_by_code[country_code]
                country['insights'] = merge_insights(country['insights'], insights)
                merged_count['countries'] += 1
                print(f"  ✓ Merged into country: {country_code}")

        # Strategy 2: Language zones - merge into both regions and constituent countries
        elif market_name in ['French Language Zone', 'German Language Zone (DACH)']:
            # Get primary regions (countries)
            primary_regions = market.get('primary_regions', [])

            # Map to region codes
            region_mapping = {
                'French Language Zone': None,  # No single region
                'German Language Zone (DACH)': 'DACH',
            }

            region_code = region_mapping.get(market_name)
            if region_code and region_code in regions_by_code:
                region = regions_by_code[region_code]
                region['insights'] = merge_insights(region['insights'], insights)
                merged_count['regions'] += 1
                print(f"  ✓ Merged into region: {region_code}")

            # Also merge into individual countries
            for region_name in primary_regions:
                country_code = extract_country_code_from_name(region_name, countries)
                if country_code and country_code in countries_by_code:
                    country = countries_by_code[country_code]
                    # Use a subset of insights (cultural + regulatory, not all language-specific ones)
                    country_insights = [
                        i for i in insights
                        if i['heading'] not in ['Language segmentation']  # Skip pure language rules
                    ]
                    country['insights'] = merge_insights(country['insights'], country_insights)
                    merged_count['countries'] += 1
                    print(f"  ✓ Merged into country: {country_code}")

        # Strategy 3: Regional/multi-country markets
        elif market_name in ['US Hispanic/Latino', 'United Kingdom and Ireland',
                             'MENA Arabic Markets', 'Southeast Asia',
                             'Sub-Saharan Africa', 'Nordic Markets',
                             'Central and Eastern Europe', 'Canada (Bilingual)',
                             'Mainland China (Mandarin/Simplified Chinese)',
                             'Greater China - Traditional Chinese Markets',
                             'Spanish Language Zone - Latin America',
                             'Australia and New Zealand']:

            # Map market to region code
            market_to_region = {
                'US Hispanic/Latino': None,  # US subset, not a region
                'United Kingdom and Ireland': 'UK_IE',
                'MENA Arabic Markets': 'MENA',
                'Southeast Asia': 'SEA',
                'Sub-Saharan Africa': 'SSA',
                'Nordic Markets': 'NORDICS',
                'Central and Eastern Europe': 'CEE',
                'Canada (Bilingual)': None,  # Single country
                'Mainland China (Mandarin/Simplified Chinese)': 'GREATER_CHINA',
                'Greater China - Traditional Chinese Markets': 'GREATER_CHINA',
                'Spanish Language Zone - Latin America': 'LATAM',
                'Australia and New Zealand': 'ANZ',
            }

            region_code = market_to_region.get(market_name)

            # Merge into region if applicable
            if region_code and region_code in regions_by_code:
                region = regions_by_code[region_code]
                region['insights'] = merge_insights(region['insights'], insights)
                merged_count['regions'] += 1
                print(f"  ✓ Merged into region: {region_code}")

            # Also merge into constituent countries
            primary_regions = market.get('primary_regions', [])
            for region_name in primary_regions:
                # Special handling for multi-word country names
                country_code = None

                # Try direct lookup
                country_code = extract_country_code_from_name(region_name, countries)

                # Manual mappings for tricky ones
                manual_mappings = {
                    'United States': 'US',
                    'United States (Hispanic/Latino communities)': 'US',
                    'United Kingdom': 'GB',
                    'Ireland': 'IE',
                    'Saudi Arabia': 'SA',
                    'UAE': 'AE',
                    'Egypt': 'EG',
                    'Indonesia': 'ID',
                    'Thailand': 'TH',
                    'Vietnam': 'VN',
                    'Philippines': 'PH',
                    'Malaysia': 'MY',
                    'Singapore': 'SG',
                    'Nigeria': 'NG',
                    'South Africa': 'ZA',
                    'Kenya': 'KE',
                    'Ghana': 'GH',
                    'Sweden': 'SE',
                    'Norway': 'NO',
                    'Denmark': 'DK',
                    'Finland': 'FI',
                    'Poland': 'PL',
                    'Czech Republic': 'CZ',
                    'Hungary': 'HU',
                    'Romania': 'RO',
                    'Canada': 'CA',
                    'Mainland China': 'CN',
                    'Taiwan': 'TW',
                    'Hong Kong': 'HK',
                    'Macau': None,  # Not in our countries
                    'Mexico': 'MX',
                    'Colombia': 'CO',
                    'Argentina': 'AR',
                    'Peru': 'PE',
                    'Chile': 'CL',
                    'Venezuela': 'VE',
                    'Australia': 'AU',
                    'New Zealand': 'NZ',
                }

                if region_name in manual_mappings:
                    country_code = manual_mappings[region_name]

                if country_code and country_code in countries_by_code:
                    country = countries_by_code[country_code]
                    country['insights'] = merge_insights(country['insights'], insights)
                    merged_count['countries'] += 1
                    print(f"  ✓ Merged into country: {country_code} ({region_name})")

    # Save updated data
    print("\n" + "="*60)
    print("Saving updated files...")
    save_json(data_dir / 'countries.json', countries)
    save_json(data_dir / 'regions.json', regions)
    save_json(data_dir / 'languages.json', languages)

    print("\n" + "="*60)
    print("Summary:")
    print(f"  Countries updated: {merged_count['countries']}")
    print(f"  Regions updated: {merged_count['regions']}")
    print(f"  Languages updated: {merged_count['languages']}")
    print("\nMerge complete! ✓")


if __name__ == '__main__':
    main()
