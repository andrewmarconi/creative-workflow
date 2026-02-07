# Default Reference Data

**Issue:** #44
**Last Updated:** 2026-02-06

---

## Overview

This document defines the **starter reference data** that will be seeded when the expanded context metadata system is deployed. This data provides a foundation for common adaptation scenarios.

---

## Data File Structure

Default data will be stored in: `data/reference_data.json`

```text
{
  "llm_models": [...],      // Existing, from core_data.json
  "regions": [...],          // NEW
  "countries": [...],        // NEW
  "cultures": [...],         // NEW
  "languages": [...],        // UPDATED: locale-specific codes
  "country_regions": [...],  // M2M mappings
  "country_languages": [...],// M2M mappings with is_primary
  "region_cultures": [...]   // M2M mappings
}
```

---

## Regions

**Purpose:** Broad cultural/market groupings that share common characteristics

```text
{
  "regions": [
    {
      "code": "NA",
      "name": "North America",
      "description": "USA, Canada, and northern Mexico market cluster",
      "insights": [
        {
          "heading": "Cultural values",
          "points": [
            "Direct, benefit-oriented messaging resonates",
            "Casual tone and informal address acceptable in most contexts",
            "Aspirational optimism and personal achievement themes",
            "Fast-paced, attention-grabbing creative preferred"
          ]
        },
        {
          "heading": "Media environment",
          "points": [
            "Highly fragmented media landscape across digital and traditional",
            "Short-form content (15s, 30s) dominates",
            "Regional diversity significant: Northeast formal, West Coast casual, South traditional"
          ]
        }
      ]
    },
    {
      "code": "LATAM",
      "name": "Latin America",
      "description": "Spanish and Portuguese-speaking Americas",
      "insights": [
        {
          "heading": "Cultural values",
          "points": [
            "Family-oriented messaging resonates strongly ('familia' as central value)",
            "Warm, relationship-focused tone preferred over transactional",
            "Emotional storytelling and music/celebration cultural touchpoints",
            "Respect for tradition alongside aspirational modernity"
          ]
        },
        {
          "heading": "Regional diversity",
          "points": [
            "Mexican Spanish differs from Argentine, Colombian, or Caribbean variants",
            "Brazil (Portuguese) requires separate creative from Spanish LATAM",
            "Socioeconomic diversity wide - avoid one-size-fits-all approaches"
          ]
        }
      ]
    },
    {
      "code": "NORDICS",
      "name": "Nordics",
      "description": "Scandinavian countries: Sweden, Norway, Denmark, Finland, Iceland",
      "insights": [
        {
          "heading": "Cultural values",
          "points": [
            "Egalitarianism and modesty (Jantelagen) - avoid bragging or superiority claims",
            "Nature and sustainability deeply valued across all Nordic countries",
            "High trust in institutions and preference for evidence-based messaging",
            "Quality and functionality emphasized over luxury or status"
          ]
        },
        {
          "heading": "Visual aesthetics",
          "points": [
            "Clean, minimalist design language resonates strongly",
            "Muted color palettes preferred over bright, saturated colors",
            "Functionality emphasized over decoration",
            "Simplicity and clarity valued in messaging"
          ]
        }
      ]
    },
    {
      "code": "DACH",
      "name": "DACH",
      "description": "Germany, Austria, Switzerland (German-speaking)",
      "insights": [
        {
          "heading": "Cultural values",
          "points": [
            "Precision, engineering excellence, and quality craftsmanship resonate",
            "Formal address (Sie) expected in most advertising contexts",
            "Factual accuracy and substantive claims valued over emotional appeals",
            "Privacy and data protection paramount concerns"
          ]
        },
        {
          "heading": "Tone and register",
          "points": [
            "German audiences value informative advertising with clear product benefits",
            "Austrian audiences appreciate warmth alongside quality",
            "Swiss audiences prioritize discretion, reliability, and understatement"
          ]
        }
      ]
    },
    {
      "code": "EU-WEST",
      "name": "Western Europe",
      "description": "France, Belgium, Netherlands, Luxembourg, UK, Ireland",
      "insights": [
        {
          "heading": "Cultural considerations",
          "points": [
            "Diverse markets with strong national identities - avoid pan-European assumptions",
            "Heritage, quality, and authenticity resonate across region",
            "Language protection important (France Toubon Law, Quebec Bill 96)",
            "Environmental consciousness widespread"
          ]
        }
      ]
    },
    {
      "code": "APAC",
      "name": "Asia Pacific",
      "description": "East Asia, Southeast Asia, Oceania",
      "insights": [
        {
          "heading": "Regional diversity",
          "points": [
            "Extreme diversity - no single 'Asian' approach works",
            "Collectivist values in East/Southeast Asia vs individualism in Australia/NZ",
            "Respect for hierarchy and formality varies significantly by market",
            "Mobile-first markets in Southeast Asia"
          ]
        }
      ]
    }
  ]
}
```

---

## Countries

**Purpose:** Political/regulatory entities with country-specific rules

```text
{
  "countries": [
    {
      "code": "US",
      "name": "United States",
      "default_language": "en-US",
      "regions": ["NA"],
      "insights": [
        {
          "heading": "Regulatory environment",
          "points": [
            "FTC regulates truth in advertising - substantiation required for claims",
            "Industry-specific regulations (pharma, finance, alcohol vary by state)",
            "Opt-in required for email/SMS marketing under CAN-SPAM and TCPA",
            "Children's advertising heavily regulated under COPPA"
          ]
        },
        {
          "heading": "Cultural considerations",
          "points": [
            "Regional diversity significant: Northeast formal, West Coast casual, South traditional, Midwest practical",
            "Multicultural audiences: 19% Hispanic, 13% Black, 6% Asian - consider specific targeting",
            "Direct, benefit-oriented messaging resonates",
            "Aspirational optimism and personal achievement themes"
          ]
        }
      ]
    },
    {
      "code": "CA",
      "name": "Canada",
      "default_language": "en-CA",
      "regions": ["NA"],
      "insights": [
        {
          "heading": "Regulatory requirements",
          "points": [
            "Quebec: Bill 96 mandates French text at least 2x size of English in advertising",
            "CRTC regulates broadcast advertising; Canadian content requirements apply",
            "Truth in Advertising guidelines enforced by Competition Bureau",
            "CASL (anti-spam law) requires explicit opt-in for commercial electronic messages"
          ]
        },
        {
          "heading": "Cultural considerations",
          "points": [
            "Distinct French-Canadian (Québécois) vs European French cultural identity",
            "Regional differences: BC progressive, Alberta conservative, Quebec francophone",
            "Avoid conflating Canadian with American culture - unique national identity",
            "Multiculturalism official policy - diverse representation expected"
          ]
        },
        {
          "heading": "Language segmentation",
          "points": [
            "English Canada: 56% (varies by province)",
            "French Canada (Quebec): 21% - requires separate creative",
            "Bilingual markets (Montreal, Ottawa) need dual-language or market-specific versions"
          ]
        }
      ]
    },
    {
      "code": "MX",
      "name": "Mexico",
      "default_language": "es-MX",
      "regions": ["LATAM", "NA"],
      "insights": [
        {
          "heading": "Cultural considerations",
          "points": [
            "Family-oriented messaging resonates strongly",
            "Regional diversity: Mexico City cosmopolitan, northern states US-influenced, southern states traditional",
            "Humor and warmth appreciated in advertising",
            "Music and celebration powerful cultural touchpoints"
          ]
        },
        {
          "heading": "Language",
          "points": [
            "Mexican Spanish has distinct vocabulary and expressions vs Spain or other LATAM",
            "Informal 'tú' more common than formal 'usted' in advertising",
            "Regional slang varies - use neutral Mexican Spanish for broad reach"
          ]
        }
      ]
    },
    {
      "code": "SE",
      "name": "Sweden",
      "default_language": "sv-SE",
      "regions": ["NORDICS"],
      "insights": [
        {
          "heading": "Regulatory environment",
          "points": [
            "Swedish Consumer Agency (Konsumentverket) oversees advertising",
            "Strict regulations on advertising to children under 12",
            "Environmental claims must be substantiated",
            "Gender stereotypes in advertising discouraged"
          ]
        },
        {
          "heading": "Cultural considerations",
          "points": [
            "Jantelagen (Law of Jante) - avoid boastful or superiority claims",
            "Sustainability and environmental consciousness paramount",
            "Egalitarian values - inclusive representation expected",
            "Minimalist aesthetics and functionality valued"
          ]
        }
      ]
    },
    {
      "code": "NO",
      "name": "Norway",
      "default_language": "no-NO",
      "regions": ["NORDICS"],
      "insights": [
        {
          "heading": "Language considerations",
          "points": [
            "Two written standards: Bokmål (90%) and Nynorsk (10%)",
            "Bokmål recommended for advertising unless targeting rural/western regions",
            "High English proficiency but Norwegian-language advertising performs better"
          ]
        }
      ]
    },
    {
      "code": "DK",
      "name": "Denmark",
      "default_language": "da-DK",
      "regions": ["NORDICS"],
      "insights": []
    },
    {
      "code": "FI",
      "name": "Finland",
      "default_language": "fi-FI",
      "regions": ["NORDICS"],
      "insights": [
        {
          "heading": "Language considerations",
          "points": [
            "Finnish (87%) and Swedish (5%) both official languages",
            "Finnish-language advertising reaches majority; Swedish for Swedish-speaking minority",
            "English proficiency high but Finnish-language advertising preferred"
          ]
        }
      ]
    },
    {
      "code": "DE",
      "name": "Germany",
      "default_language": "de-DE",
      "regions": ["DACH"],
      "insights": [
        {
          "heading": "Regulatory environment",
          "points": [
            "Strict regulations under Unfair Competition Act (UWG)",
            "Claims must be substantiable; comparative advertising has specific requirements",
            "GDPR compliance mandatory for data collection",
            "Industry self-regulation (Deutscher Werberat) sets ethical standards"
          ]
        },
        {
          "heading": "Cultural considerations",
          "points": [
            "Precision, engineering excellence, and quality resonate",
            "Formal address (Sie) expected in most contexts",
            "Factual, informative advertising valued over emotional appeals",
            "Environmental sustainability important consideration"
          ]
        }
      ]
    },
    {
      "code": "AT",
      "name": "Austria",
      "default_language": "de-AT",
      "regions": ["DACH"],
      "insights": [
        {
          "heading": "Regulatory environment",
          "points": [
            "Telecommunications Act (TKG 2021) strictly prohibits email marketing without explicit prior consent",
            "Violations can result in fines up to €37,000",
            "Austrian Consumer Protection Act enforces advertising standards"
          ]
        },
        {
          "heading": "Language",
          "points": [
            "Austrian German has distinct vocabulary: 'Grüß Gott' (greeting), 'Jänner' (January), 'Erdapfel' (potato)",
            "Using Austrian German signals cultural awareness and local relevance"
          ]
        }
      ]
    },
    {
      "code": "CH",
      "name": "Switzerland",
      "default_language": "de-CH",
      "regions": ["DACH", "EU-WEST"],
      "insights": [
        {
          "heading": "Language segmentation",
          "points": [
            "German-speaking (63%) - Standard German for written, Schweizerdeutsch for spoken",
            "French-speaking Romandie (23%) - Swiss French with distinct expressions",
            "Italian-speaking Ticino (8%) - requires separate adaptation",
            "Romansh (0.5%) - niche but official language"
          ]
        },
        {
          "heading": "Cultural considerations",
          "points": [
            "Discretion, reliability, and quality emphasized",
            "Understatement valued - avoid superlatives without substantiation",
            "Four distinct cultural regions with different characteristics",
            "Privacy and banking secrecy cultural values"
          ]
        }
      ]
    },
    {
      "code": "FR",
      "name": "France",
      "default_language": "fr-FR",
      "regions": ["EU-WEST"],
      "insights": [
        {
          "heading": "Regulatory environment",
          "points": [
            "Toubon Law requires French-language versions of all advertising",
            "ARPP (advertising self-regulation) provides ethical guidance",
            "Comparative advertising allowed but heavily regulated",
            "Environmental claims must be substantiated (greenwashing prohibited)"
          ]
        },
        {
          "heading": "Cultural considerations",
          "points": [
            "Intellectual wit, understated elegance, and cultural sophistication resonate",
            "Overt hard-sell tactics perceived as unsophisticated",
            "Food, wine, gastronomy carry deep cultural significance",
            "Heritage, quality, and craftsmanship valued",
            "Avoid excessive Anglicisms (language protection values)"
          ]
        }
      ]
    },
    {
      "code": "BE",
      "name": "Belgium",
      "default_language": "nl-BE",
      "regions": ["EU-WEST"],
      "insights": [
        {
          "heading": "Language segmentation",
          "points": [
            "Dutch (Flemish) in Flanders (60%)",
            "French in Wallonia (40%)",
            "Brussels officially bilingual - dual-language or targeted placement",
            "German-speaking community (1%) in eastern Belgium"
          ]
        },
        {
          "heading": "Cultural considerations",
          "points": [
            "Flemish Belgians respond to more direct product benefit messaging",
            "Francophone Belgians expect formal address and sophistication",
            "Regional sensitivities - avoid conflating Flanders and Wallonia",
            "JEP (Jury d'Éthique Publicitaire) oversees advertising ethics"
          ]
        }
      ]
    }
  ]
}
```

---

## Languages

**Key Change:** Locale-specific codes (e.g., `en-US`, `fr-CA`) instead of base codes (e.g., `en`, `fr`)

```text
{
  "languages": [
    {
      "code": "en-US",
      "name": "English (United States)",
      "base_language": "en",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": ["CohereForAI/aya-expanse-8b"],
      "insights": [
        {
          "heading": "Language characteristics",
          "points": [
            "American spelling: color, honor, organize (not colour, honour, organise)",
            "Informal tone acceptable in most advertising contexts",
            "Active voice and direct phrasing preferred",
            "Contractions common and natural (it's, you're, we've)"
          ]
        }
      ]
    },
    {
      "code": "en-CA",
      "name": "English (Canada)",
      "base_language": "en",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": ["CohereForAI/aya-expanse-8b"],
      "insights": [
        {
          "heading": "Language characteristics",
          "points": [
            "Canadian spelling: colour, honour, centre (British-influenced)",
            "Mix of British and American vocabulary: 'truck' (US) but 'tap' not 'faucet' (UK)",
            "Distinct idioms: 'toque' (winter hat), 'parkade' (parking garage)",
            "'Eh?' as conversation filler characteristic but avoid stereotyping"
          ]
        }
      ]
    },
    {
      "code": "en-GB",
      "name": "English (United Kingdom)",
      "base_language": "en",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": ["CohereForAI/aya-expanse-8b"],
      "insights": []
    },
    {
      "code": "fr-FR",
      "name": "French (France)",
      "base_language": "fr",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": ["CohereForAI/aya-expanse-8b", "mistralai/Mistral-7B-Instruct-v0.3"],
      "insights": [
        {
          "heading": "Language characteristics",
          "points": [
            "Formal register (vous) expected in most advertising",
            "Informal (tu) reserved for youth-oriented or digital-native contexts",
            "Avoid excessive Anglicisms - French equivalents preferred",
            "Subjunctive mood and formal constructions common"
          ]
        }
      ]
    },
    {
      "code": "fr-CA",
      "name": "French (Quebec)",
      "base_language": "fr",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": ["CohereForAI/aya-expanse-8b"],
      "insights": [
        {
          "heading": "Vocabulary differences from France",
          "points": [
            "Car: 'char' (QC) vs 'voiture' (FR)",
            "Breakfast: 'déjeuner' (QC) vs 'petit-déjeuner' (FR)",
            "Weekend: 'fin de semaine' (QC) vs 'weekend' (FR)",
            "Parking: 'stationnement' (QC) vs 'parking' (FR)",
            "Email: 'courriel' (QC) vs 'mail/email' (FR)"
          ]
        },
        {
          "heading": "Pronunciation and idioms",
          "points": [
            "Quebec French has distinct phonology - MUST use Quebec VO talent, not European",
            "Local idioms: 'C'est le fun' (it's fun), 'Tiguidou' (great/okay)",
            "Informal 'tu' more common than formal 'vous' in advertising",
            "Sacres (religious swear words) exist but avoid in advertising"
          ]
        },
        {
          "heading": "Legal and compliance",
          "points": [
            "Office québécois de la langue française enforces French language use",
            "Bill 101 (Charter of the French Language) sets commercial French requirements",
            "Bill 96 mandates French text at least 2x size of English",
            "All product descriptions, warnings, and supers MUST be in French"
          ]
        }
      ]
    },
    {
      "code": "fr-BE",
      "name": "French (Belgium)",
      "base_language": "fr",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": ["CohereForAI/aya-expanse-8b"],
      "insights": [
        {
          "heading": "Language characteristics",
          "points": [
            "Belgian French closer to France French than Quebec French",
            "Distinct vocabulary: 'septante' (70), 'nonante' (90) instead of soixante-dix, quatre-vingt-dix",
            "Formal 'vous' expected in advertising",
            "Flemish influence in Brussels - bilingual considerations"
          ]
        }
      ]
    },
    {
      "code": "fr-CH",
      "name": "French (Switzerland)",
      "base_language": "fr",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": [],
      "insights": [
        {
          "heading": "Language characteristics",
          "points": [
            "Swiss French (Romandie) uses 'septante' (70), 'huitante' (80), 'nonante' (90)",
            "Distinct expressions and vocabulary vs France French",
            "Formal and precise language expected",
            "Understatement and discretion valued in Swiss culture"
          ]
        }
      ]
    },
    {
      "code": "es-MX",
      "name": "Spanish (Mexico)",
      "base_language": "es",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": ["CohereForAI/aya-expanse-8b", "mistralai/Mistral-7B-Instruct-v0.3"],
      "insights": [
        {
          "heading": "Vocabulary and expressions",
          "points": [
            "Car: 'carro' (MX) vs 'coche' (ES) vs 'auto' (AR)",
            "Computer: 'computadora' (MX) vs 'ordenador' (ES)",
            "Bus: 'camión' (MX) vs 'autobús' (ES)",
            "Avoid Castilian 'vosotros' - use 'ustedes' for plural 'you'"
          ]
        },
        {
          "heading": "Cultural expressions",
          "points": [
            "Informal 'tú' acceptable in advertising",
            "Diminutives common and affectionate: '-ito/-ita' endings",
            "Regional slang varies within Mexico - neutral Mexican Spanish for broad reach"
          ]
        }
      ]
    },
    {
      "code": "es-US",
      "name": "Spanish (United States)",
      "base_language": "es",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": ["CohereForAI/aya-expanse-8b"],
      "insights": [
        {
          "heading": "Audience diversity",
          "points": [
            "Mexican origin (63%), Puerto Rican (9%), Cuban (4%), Central/South American",
            "Use neutral 'Spanish' avoiding Mexico/PR/Cuba-specific slang unless targeted",
            "Spanglish acceptable for younger, acculturated audiences",
            "First-generation vs second-generation preferences vary significantly"
          ]
        }
      ]
    },
    {
      "code": "es-ES",
      "name": "Spanish (Spain)",
      "base_language": "es",
      "primary_model": "Qwen/Qwen2.5-7B-Instruct",
      "alternative_models": [],
      "insights": [
        {
          "heading": "Language characteristics",
          "points": [
            "Uses 'vosotros' for plural 'you' (not used in Latin America)",
            "Ceceo/distinción: 'c' and 'z' pronounced differently than in LATAM",
            "Castilian vocabulary: 'coche' (car), 'ordenador' (computer)",
            "Formal 'usted' for advertising unless youth-targeted"
          ]
        }
      ]
    },
    {
      "code": "de-DE",
      "name": "German (Germany)",
      "base_language": "de",
      "primary_model": "mistralai/Mistral-7B-Instruct-v0.3",
      "alternative_models": ["Qwen/Qwen2.5-7B-Instruct"],
      "insights": [
        {
          "heading": "Language characteristics",
          "points": [
            "Formal address (Sie) expected in most advertising",
            "Compound words common - keep messaging concise",
            "Precision and accuracy valued - avoid vague claims",
            "Gender-neutral language increasingly expected"
          ]
        }
      ]
    },
    {
      "code": "de-AT",
      "name": "German (Austria)",
      "base_language": "de",
      "primary_model": "mistralai/Mistral-7B-Instruct-v0.3",
      "alternative_models": [],
      "insights": [
        {
          "heading": "Vocabulary differences from Germany",
          "points": [
            "Greeting: 'Grüß Gott' (AT) vs 'Hallo/Guten Tag' (DE)",
            "January: 'Jänner' (AT) vs 'Januar' (DE)",
            "Potato: 'Erdapfel' (AT) vs 'Kartoffel' (DE)",
            "Tomato: 'Paradeiser' (AT) vs 'Tomate' (DE)"
          ]
        }
      ]
    },
    {
      "code": "de-CH",
      "name": "German (Switzerland)",
      "base_language": "de",
      "primary_model": "mistralai/Mistral-7B-Instruct-v0.3",
      "alternative_models": [],
      "insights": [
        {
          "heading": "Language considerations",
          "points": [
            "Swiss Standard German (Hochdeutsch) for written advertising",
            "Schweizerdeutsch (Swiss German) for spoken VO - significantly different from Standard German",
            "Helvetisms: Swiss-specific vocabulary and expressions",
            "Formal and precise language expected"
          ]
        }
      ]
    },
    {
      "code": "sv-SE",
      "name": "Swedish",
      "base_language": "sv",
      "primary_model": "microsoft/Phi-3.5-mini-instruct",
      "alternative_models": ["Qwen/Qwen2.5-7B-Instruct"],
      "insights": []
    },
    {
      "code": "no-NO",
      "name": "Norwegian (Bokmål)",
      "base_language": "no",
      "primary_model": "microsoft/Phi-3.5-mini-instruct",
      "alternative_models": [],
      "insights": [
        {
          "heading": "Language considerations",
          "points": [
            "Bokmål (90%) recommended for broad reach",
            "Nynorsk (10%) for rural/western regions if targeted",
            "High English proficiency but Norwegian-language advertising performs better"
          ]
        }
      ]
    },
    {
      "code": "da-DK",
      "name": "Danish",
      "base_language": "da",
      "primary_model": "microsoft/Phi-3.5-mini-instruct",
      "alternative_models": [],
      "insights": []
    },
    {
      "code": "fi-FI",
      "name": "Finnish",
      "base_language": "fi",
      "primary_model": "microsoft/Phi-3.5-mini-instruct",
      "alternative_models": [],
      "insights": []
    }
  ]
}
```

---

## Cultures

**Purpose:** Cultural themes that can span multiple regions

```text
{
  "cultures": [
    {
      "code": "nordic-minimalism",
      "name": "Nordic Minimalism",
      "description": "Clean design, understatement, nature connection, egalitarianism. Characteristic of Scandinavian countries."
    },
    {
      "code": "germanic-formality",
      "name": "Germanic Formality",
      "description": "Precision, engineering excellence, formal address, data privacy, quality craftsmanship. Dominant in DACH region."
    },
    {
      "code": "french-sophistication",
      "name": "French Sophistication",
      "description": "Intellectual wit, cultural refinement, gastronomy, heritage, understated elegance. Core to French-speaking markets."
    },
    {
      "code": "north-american-directness",
      "name": "North American Directness",
      "description": "Casual tone, direct benefit messaging, aspirational optimism, fast-paced communication. Common in USA and English Canada."
    },
    {
      "code": "latin-warmth",
      "name": "Latin Warmth",
      "description": "Family-oriented, relationship-focused, emotional storytelling, celebration and music as cultural touchpoints. Prevalent across Latin America and Hispanic markets."
    },
    {
      "code": "asian-collectivism",
      "name": "Asian Collectivism",
      "description": "Group harmony, respect for hierarchy, indirect communication, family and community emphasis. Common across East and Southeast Asia."
    }
  ]
}
```

---

## M2M Relationship Mappings

### Country → Region

```text
{
  "country_regions": [
    {"country": "US", "region": "NA"},
    {"country": "CA", "region": "NA"},
    {"country": "MX", "region": "LATAM"},
    {"country": "MX", "region": "NA"},
    {"country": "SE", "region": "NORDICS"},
    {"country": "NO", "region": "NORDICS"},
    {"country": "DK", "region": "NORDICS"},
    {"country": "FI", "region": "NORDICS"},
    {"country": "DE", "region": "DACH"},
    {"country": "AT", "region": "DACH"},
    {"country": "CH", "region": "DACH"},
    {"country": "CH", "region": "EU-WEST"},
    {"country": "FR", "region": "EU-WEST"},
    {"country": "BE", "region": "EU-WEST"}
  ]
}
```

### Country → Language (with is_primary flag)

```text
{
  "country_languages": [
    {"country": "US", "language": "en-US", "is_primary": true},
    {"country": "US", "language": "es-US", "is_primary": false},

    {"country": "CA", "language": "en-CA", "is_primary": true},
    {"country": "CA", "language": "fr-CA", "is_primary": false},

    {"country": "MX", "language": "es-MX", "is_primary": true},

    {"country": "SE", "language": "sv-SE", "is_primary": true},
    {"country": "NO", "language": "no-NO", "is_primary": true},
    {"country": "DK", "language": "da-DK", "is_primary": true},
    {"country": "FI", "language": "fi-FI", "is_primary": true},

    {"country": "DE", "language": "de-DE", "is_primary": true},
    {"country": "AT", "language": "de-AT", "is_primary": true},

    {"country": "CH", "language": "de-CH", "is_primary": true},
    {"country": "CH", "language": "fr-CH", "is_primary": false},
    {"country": "CH", "language": "it-CH", "is_primary": false},

    {"country": "FR", "language": "fr-FR", "is_primary": true},

    {"country": "BE", "language": "nl-BE", "is_primary": true},
    {"country": "BE", "language": "fr-BE", "is_primary": false},
    {"country": "BE", "language": "de-BE", "is_primary": false}
  ]
}
```

### Region → Culture

```text
{
  "region_cultures": [
    {"region": "NORDICS", "culture": "nordic-minimalism"},
    {"region": "DACH", "culture": "germanic-formality"},
    {"region": "EU-WEST", "culture": "french-sophistication"},
    {"region": "NA", "culture": "north-american-directness"},
    {"region": "LATAM", "culture": "latin-warmth"},
    {"region": "APAC", "culture": "asian-collectivism"}
  ]
}
```

---

## Import Command

Create management command: `import_reference_data`

```bash
uv run manage.py import_reference_data
uv run manage.py import_reference_data --file data/custom_reference.json
uv run manage.py import_reference_data --dry-run
```

This command will:
1. Import/update LLMModels (existing logic)
2. Import/update Regions with insights
3. Import/update Countries with insights
4. Import/update Cultures
5. Import/update Languages with locale codes and insights
6. Create M2M relationships (CountryRegion, CountryLanguage, RegionCulture)

---

## References

- [PRD](./prd.md)
- [Data Model](./data_model.md)
- [Implementation Plan](./implementation_plan.md)
