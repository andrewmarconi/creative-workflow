.. _segmentation:

======================
Audience Segmentation
======================

The segmentation system provides a comprehensive framework for understanding and categorizing audiences based on demographic, behavioral, and psychographic attributes. This dataset reflects marketing best practices from industry frameworks including VALS (Values and Lifestyles), Rogers' Innovation Adoption Curve, AIO (Activities, Interests, Opinions) variables, and contemporary behavioral segmentation models used in audience development and programmatic advertising.

Overview
========

The segmentation architecture consists of two primary models:

1. **Segment** - Individual segmentation attributes organized by category, vector, and value
2. **Persona** - Named collections of segments representing complete target audience profiles

Segment Model
=============

Structure
---------

Each segment represents a single attribute along a specific dimension of audience analysis:

.. code-block:: python

    {
        "category": "DEMOGRAPHIC",           # Segment category
        "vector": "Household Income",        # Dimension being segmented
        "value": "$75K-$100K",              # Position on the dimension
        "description": "",                   # Optional longer description
        "insights": [],                      # Structured insights (future use)
        "is_active": true                    # Whether segment is active
    }

Categories
----------

Segments are organized into three primary categories:

DEMOGRAPHIC
~~~~~~~~~~~

Demographic segments represent objective, measurable characteristics of individuals:

**Age & Generation**
   - Age ranges from 0-4 (Toddlers/Preschoolers) to 65+ (Seniors/Retirees)
   - Generational cohorts: Silent Generation, Baby Boomers, Gen X, Millennials, Gen Z, Gen Alpha

**Income & Economic Status**
   - Household Income brackets from Under $25K to $250K+
   - Income Tiers: Low Income, Lower-Middle, Middle, Upper-Middle, Affluent, High Net Worth

**Education & Employment**
   - Education Level: From "Less than High School" to "Doctoral/Professional Degree"
   - Occupation Type: Professional, Technical, Creative, Healthcare, Education, etc.
   - Employment Status: Full-Time, Part-Time, Self-Employed, Student, Retired, etc.

**Family & Household**
   - Marital Status: Single, Married, Domestic Partnership, Divorced, Separated, Widowed
   - Family Composition: Single - No Children, Nuclear Family, Single Parent, Multi-Generational, Empty Nesters
   - Household Size: 1 to 5+ people
   - Children in Household: Number and age ranges of children

**Identity & Culture**
   - Gender Identity: Male, Female, Non-Binary, Gender Fluid, Prefer Not to Disclose
   - Ethnicity/Race: White/Caucasian, Black/African American, Hispanic/Latino, Asian, Native American, Pacific Islander, Middle Eastern, Multiracial
   - Religion: Christian (Protestant/Catholic), Jewish, Muslim, Hindu, Buddhist, Agnostic/Atheist, Spiritual but Not Religious
   - Language: English - Primary, Spanish - Primary, Bilingual, Multilingual
   - Nationality: Domestic/Native-Born, Naturalized Citizen, Permanent Resident, Temporary Visa, International

**Life Stage & Geography**
   - Life Stage: Young Single, Young Couple, New Parents, Growing Family, Empty Nester, Retiree
   - Home Ownership: Own - Paid Off, Own - With Mortgage, Rent, Live with Family/Friends
   - Urbanicity: Urban Core, Urban Suburbs, Suburban, Rural/Small Town, Remote/Agricultural

**Accessibility**
   - Disability Status: No Disability, Physical, Sensory, Cognitive/Developmental, Chronic Illness

BEHAVIORAL
~~~~~~~~~~

Behavioral segments capture observable actions and patterns of interaction:

**Purchase & Usage Patterns**
   - Purchase Frequency: First-Time Buyer, One-Time/Rare, Occasional, Regular, Frequent, Power User, Lapsed
   - Usage Rate: Non-User, Light User, Medium User, Heavy User, Super User
   - Recency: Active (Last 30 Days), Recent (31-90 Days), Lapsing (91-180 Days), Lapsed (181-365 Days), Dormant (365+ Days)

**Loyalty & Engagement**
   - Customer Loyalty: Brand Switcher, Price-Sensitive, Habitual Buyer, Satisfied Repeat Customer, Brand Loyalist, VIP/Premium Member
   - Loyalty Program Status: Non-Member, Member - Inactive/Bronze/Silver/Gold/Platinum
   - Engagement Level: Non-Engaged/Passive, Low, Moderate, High, Power User/Champion

**Purchase Behavior**
   - Purchase Behavior Type: Complex Decision-Maker, Variety Seeker, Habitual Buyer, Dissonance-Reducing Buyer, Impulse Buyer, Deliberate/Planned Buyer
   - Spending Tier: Budget/Value Buyer, Mid-Range Spender, Premium Buyer, Luxury/High-Ticket Buyer, Whale/Top Spender
   - Average Order Value: Very Low (<$25), Low ($25-$50), Medium ($50-$100), High ($100-$250), Very High ($250+)

**Benefits & Motivations**
   - Benefits Sought: Quality/Performance, Price/Value, Convenience/Speed, Status/Prestige, Innovation, Sustainability/Ethics, Customer Service, Customization, Reliability/Trust
   - Occasion/Timing: Daily Routine, Weekly Routine, Monthly/Recurring, Seasonal, Holiday/Special Event, Birthday/Anniversary, Milestone/Life Event, Emergency/Urgent Need

**Customer Journey**
   - Customer Journey Stage: Awareness, Consideration, Decision/Conversion, Onboarding, Activation/First Use, Retention, Growth/Expansion, Advocacy, Churn Risk, Winback/Reactivation
   - Decision Speed: Immediate/Impulse, Fast (Within 24 hrs), Moderate (1-7 days), Slow/Deliberate (1-4 weeks), Extended Research (1+ months)

**Channel & Digital Behavior**
   - Digital Behavior: Mobile-First User, Desktop-Preferred, Omnichannel User, App Power User, Email Responsive, Social Media Engaged, SMS/Text Preferred, Push Notification Engaged, Web Browser Only
   - Purchase Channel: Online Only, In-Store Only, Omnichannel, Marketplace (Amazon, etc.), Social Commerce, Subscription/Auto-Renew

**Response & Engagement**
   - Price Sensitivity: Highly Price-Sensitive, Moderately Price-Conscious, Value-Balanced Buyer, Premium-Willing, Price-Insensitive/Luxury
   - Promotion Response: Deal Seeker/Coupon User, Sale-Driven Buyer, FOMO Responder, Limited Promotion Response, Non-Promotion Buyer
   - Feature Usage: Core Features Only, Moderate Feature Adoption, Advanced Feature User, Power User (All Features), Under-Utilizing
   - Content Consumption: Passive Consumer, Active Reader/Viewer, Content Creator/Contributor, Community Participant, Influencer/Advocate

**Satisfaction & Support**
   - Customer Satisfaction: Detractor (0-6 NPS), Passive (7-8 NPS), Promoter (9-10 NPS), At-Risk Customer, Champion/Advocate
   - Support Usage: Never Contacted Support, Rare Support User, Occasional Support User, Frequent Support User, High-Touch/Problem Account

PSYCHOGRAPHIC
~~~~~~~~~~~~~

Psychographic segments represent psychological attributes, values, attitudes, and lifestyle characteristics:

**Lifestyle & Personality**
   - Lifestyle - General: Traditional/Conservative, Modern/Progressive, Active/Outdoor Enthusiast, Urban Professional, Suburban Family-Oriented, Rural/Country Living, Minimalist, Luxury/High-End, Bohemian/Alternative, Health & Wellness Focused
   - Personality Type: Extroverted, Introverted, Adventurous/Risk-Taker, Cautious/Risk-Averse, Spontaneous/Impulsive, Planned/Organized, Creative/Artistic, Analytical/Logical, Competitive/Achievement-Oriented, Cooperative/Harmonious, Independent/Self-Reliant, Community-Oriented/Social

**Values & Priorities**
   - Core Values: Family & Relationships, Career & Achievement, Financial Security, Personal Growth & Learning, Health & Wellness, Creativity & Self-Expression, Social Justice & Equality, Environmental Sustainability, Tradition & Heritage, Innovation & Progress, Freedom & Independence, Community & Belonging, Spirituality & Faith, Fun & Enjoyment
   - Life Priorities: Career-Focused, Family-Focused, Health-Focused, Social Life-Focused, Financial Independence-Focused, Adventure/Experience-Focused, Creative Pursuit-Focused, Spiritual Growth-Focused, Work-Life Balance Seeker

**Attitudes & Opinions**
   - Attitudes - Spending: Frugal/Saver, Practical/Value-Conscious, Balanced Spender, Experience-Over-Things, Status-Conscious, Indulgent/Treat-Yourself, Luxury-Seeking
   - Attitudes - Technology: Technophobe/Resistant, Technology Cautious, Pragmatic Tech User, Early Adopter, Tech Enthusiast/Innovator
   - Attitudes - Brand: Brand Agnostic, Value-Brand Preferrer, Quality-Brand Seeker, Premium-Brand Loyal, Luxury-Brand Devotee, Local/Small Business Supporter
   - Attitudes - Environment: Unconcerned, Somewhat Aware, Environmentally Conscious, Eco-Activist/Advocate, Zero-Waste/Extreme Sustainability
   - Opinions - Political: Very Conservative, Conservative, Moderate/Centrist, Liberal, Very Liberal/Progressive, Libertarian, Apolitical/Disengaged

**Social & Cultural**
   - Social Class: Working Class, Lower-Middle Class, Middle Class, Upper-Middle Class, Upper Class, Aspirational (Upward Mobile)

**Activities & Interests**
   - Activities - Recreation: Sports & Fitness, Outdoor Adventures, Arts & Culture, Entertainment & Media, Dining & Culinary, Travel & Exploration, Gaming (Video/Board), Crafts & DIY, Reading & Learning, Social Events & Parties, Home & Garden, Volunteering & Community Service
   - Interests - Hobbies: Sports Fandom, Fitness & Exercise, Cooking & Baking, Fashion & Beauty, Music, Photography, Technology & Gadgets, Automotive, Home Improvement, Pet Care, Parenting & Family, Politics & Current Events, Spirituality & Meditation

**Emotional & Motivational**
   - Emotional Drivers: Security & Safety, Belonging & Connection, Achievement & Success, Recognition & Status, Freedom & Control, Excitement & Novelty, Comfort & Familiarity, Purpose & Meaning, Self-Expression & Identity, Nostalgia & Tradition
   - Motivations - Purchase: Problem-Solving Need, Self-Improvement, Social Acceptance, Status Enhancement, Pleasure & Enjoyment, Time-Saving Convenience, Risk Reduction, Aspirational Identity, Altruism & Giving

**Framework-Based Segments**
   - VALS Framework: Innovators, Thinkers, Achievers, Experiencers, Believers, Strivers, Makers, Survivors
   - Innovation Adoption: Innovators (2.5%), Early Adopters (13.5%), Early Majority (34%), Late Majority (34%), Laggards (16%)

**Media & Shopping**
   - Media Consumption: Traditional TV Viewer, Streaming-First Consumer, Social Media Heavy User, Podcast Listener, Print/News Reader, YouTube Consumer, Radio Listener, Minimal Media Consumer
   - Shopping Style: Researcher/Information Seeker, Bargain Hunter, Brand Loyalist, Trendsetter/Early Adopter, Convenience Shopper, Experience Seeker, Ethical Consumer, Impulse Buyer, Minimalist/Selective Buyer

**Risk & Change**
   - Risk Tolerance: Risk-Averse/Conservative, Cautious/Calculated, Moderate Risk-Taker, Adventurous/High Risk, Thrill-Seeker/Extreme Risk

Theoretical Frameworks
======================

The segmentation dataset incorporates insights from several established marketing and behavioral frameworks:

VALS Framework
--------------

The **Values and Lifestyles (VALS)** framework segments consumers based on psychological traits and resources. The eight VALS types are included as psychographic segments:

- **Innovators** - Successful, sophisticated, active consumers with high self-esteem and abundant resources
- **Thinkers** - Motivated by ideals, mature, reflective, comfortable, practical consumers
- **Achievers** - Goal-oriented, committed to career and family, value stability and self-discovery
- **Experiencers** - Young, enthusiastic, impulsive consumers seeking variety and excitement
- **Believers** - Motivated by ideals, conservative, conventional, with concrete beliefs
- **Strivers** - Trendy and fun-loving, concerned about approval of others, limited resources
- **Makers** - Practical, self-sufficient, traditional consumers who value functionality
- **Survivors** - Elderly, passive, concerned, loyal, limited resources

Rogers' Innovation Adoption Curve
----------------------------------

**Everett Rogers' Diffusion of Innovations** theory categorizes individuals based on their willingness to adopt new products/technologies. The five adopter categories are included with their characteristic distribution percentages:

- **Innovators (2.5%)** - Venturesome, educated, willing to take risks
- **Early Adopters (13.5%)** - Respect, opinion leaders, educated, socially forward
- **Early Majority (34%)** - Deliberate, many informal social contacts
- **Late Majority (34%)** - Skeptical, traditional, lower socioeconomic status
- **Laggards (16%)** - Neighbors and friends are information sources, fear of debt

AIO Variables
-------------

**Activities, Interests, and Opinions (AIO)** segmentation examines how people spend their time, what interests them, and their views on various topics:

**Activities** - Work, hobbies, social events, vacation, entertainment, club membership, community, shopping, sports

**Interests** - Family, home, job, community, recreation, fashion, food, media, achievements

**Opinions** - Political, social issues, business, economics, education, products, future, culture

The dataset includes extensive activity and interest vectors (Recreation, Hobbies) and opinion vectors (Political) under the Psychographic category.

Customer Journey Mapping
-------------------------

The behavioral segments include **Customer Journey Stage** tracking, recognizing that different audiences occupy different stages of the purchase funnel:

- **Awareness** - Learning about a product/service
- **Consideration** - Evaluating options
- **Decision/Conversion** - Making a purchase
- **Onboarding** - Initial setup/learning
- **Activation/First Use** - Achieving first value
- **Retention** - Ongoing usage
- **Growth/Expansion** - Increasing usage/spending
- **Advocacy** - Recommending to others
- **Churn Risk** - At risk of leaving
- **Winback/Reactivation** - Attempting to return

Net Promoter Score (NPS)
-------------------------

Customer satisfaction is measured using the **Net Promoter Score** methodology:

- **Detractor (0-6 NPS)** - Unhappy customers who can damage brand through negative word-of-mouth
- **Passive (7-8 NPS)** - Satisfied but unenthusiastic customers vulnerable to competitive offerings
- **Promoter (9-10 NPS)** - Loyal enthusiasts who keep buying and refer others

Persona Model
=============

Personas combine geographic and non-geographic segments to create complete target audience profiles.

Structure
---------

A Persona consists of:

**Geographic Segments** (optional):
   - **Region** - Cultural/market grouping (e.g., North America, DACH, Nordics)
   - **Country** - Political/regulatory entity (e.g., United States, Germany, Sweden)
   - **Language** - Language variant with locale (e.g., en-US, de-CH, fr-CA)

**Non-Geographic Segments** (optional, multiple):
   - Any combination of Demographic, Behavioral, and Psychographic segments

**Metadata**:
   - **name** - Descriptive persona name (e.g., "Budget-Conscious First-Timer")
   - **description** - Optional detailed description
   - **is_active** - Whether the persona is currently active

Example Persona
---------------

.. code-block:: json

    {
        "name": "Urban Tech-Savvy Millennial",
        "description": "Young professional in urban area, early adopter of technology, values experiences over possessions",
        "region_code": "NA",
        "country_code": "US",
        "language_code": "en-US",
        "segments": [
            "DEMOGRAPHIC: Age → 25-34 (Millennials - Younger)",
            "DEMOGRAPHIC: Urbanicity → Urban Core/City Center",
            "DEMOGRAPHIC: Occupation Type → Professional/White Collar",
            "BEHAVIORAL: Innovation Adoption → Early Adopters (13.5%)",
            "BEHAVIORAL: Digital Behavior → Mobile-First User",
            "PSYCHOGRAPHIC: Attitudes - Technology → Early Adopter",
            "PSYCHOGRAPHIC: Core Values → Innovation & Progress",
            "PSYCHOGRAPHIC: Attitudes - Spending → Experience-Over-Things"
        ]
    }

Data Management
===============

Import/Export
-------------

Segment and persona data can be managed using Django management commands:

.. code-block:: bash

    # Export segments to data/segments.json
    uv run manage.py export_segments

    # Export to custom directory
    uv run manage.py export_segments --dir custom/

    # Import segments from data/segments.json
    uv run manage.py import_segments

    # Preview import without making changes
    uv run manage.py import_segments --dry-run

    # Export personas (creates personas.json + persona_segments.json)
    uv run manage.py export_personas

    # Import personas
    uv run manage.py import_personas

    # Preview persona import
    uv run manage.py import_personas --dry-run

Data Files
----------

Segmentation data is stored in separate JSON files:

- ``data/segments.json`` - All segment definitions
- ``data/personas.json`` - Persona definitions (name, description, geographic references)
- ``data/persona_segments.json`` - Persona-to-Segment mappings (many-to-many relationships)

All data files follow JSON schemas defined in ``data/schemas/``:

- ``segments.schema.json`` - Segment structure validation
- ``personas.schema.json`` - Persona structure validation
- ``persona_segments.schema.json`` - Persona-segment relationship validation

Database Schema
---------------

The segmentation system uses the following database tables:

**audiences_segment**
   - ``category`` - DEMOGRAPHIC, BEHAVIORAL, or PSYCHOGRAPHIC
   - ``vector`` - Dimension being segmented (e.g., "Age", "Household Income")
   - ``value`` - Position on the dimension (e.g., "25-34", "$75K-$100K")
   - ``description`` - Optional longer description
   - ``insights`` - JSONField for structured insights
   - ``is_active`` - Boolean active flag
   - Unique constraint on (category, vector, value)

**audiences_persona**
   - ``name`` - Persona name
   - ``description`` - Optional description
   - ``region_id`` - Foreign key to Region (optional)
   - ``country_id`` - Foreign key to Country (optional)
   - ``language_id`` - Foreign key to Language (optional)
   - ``is_active`` - Boolean active flag

**audiences_persona_segment**
   - ``persona_id`` - Foreign key to Persona
   - ``segment_id`` - Foreign key to Segment
   - ``order_index`` - Display order (lower = earlier)
   - Unique constraint on (persona, segment)

Use Cases
=========

Campaign Targeting
------------------

Personas enable precise audience targeting for marketing campaigns:

1. Define target persona (e.g., "Eco-Conscious Urban Millennial")
2. Persona automatically includes all relevant segments:
   - Geographic: North America / United States / English (en-US)
   - Demographic: Age 25-34, Urban Core, College-Educated
   - Behavioral: Early Adopter, Online Only, High Engagement
   - Psychographic: Environmental Sustainability, Progressive, Experience-Focused

Content Personalization
-----------------------

Segments inform content strategy and messaging:

- **Demographic segments** → Basic personalization (age-appropriate language, income-appropriate pricing)
- **Behavioral segments** → Journey-stage content (awareness vs. retention messaging)
- **Psychographic segments** → Emotional resonance (values-aligned messaging, lifestyle imagery)

Cultural Adaptation
-------------------

Geographic segments guide localization:

- **Region** → Broad cultural patterns (e.g., Nordic minimalism, Latin American warmth)
- **Country** → Regulatory requirements (e.g., health claims, data privacy)
- **Language** → Linguistic localization (e.g., Spanish variants: es-MX vs. es-ES)

Product Development
-------------------

Segment insights inform product roadmap:

- **Benefits Sought** segments → Feature prioritization
- **Feature Usage** segments → UX optimization
- **Price Sensitivity** segments → Pricing strategy
- **Innovation Adoption** segments → Beta testing recruitment

Customer Intelligence
---------------------

Combining segment data creates rich customer profiles:

.. code-block:: python

    # High-value customer profile example
    segments = [
        "DEMOGRAPHIC: Income Tier → Affluent",
        "BEHAVIORAL: Loyalty Program Status → Member - Platinum/Elite",
        "BEHAVIORAL: Customer Satisfaction → Promoter (9-10 NPS)",
        "BEHAVIORAL: Spending Tier → Luxury/High-Ticket Buyer",
        "PSYCHOGRAPHIC: Core Values → Quality & Excellence",
    ]

Best Practices
==============

Segment Selection
-----------------

When building personas:

1. **Start with purpose** - What decision are you informing? (Campaign targeting, product design, content strategy)
2. **Layer thoughtfully** - Combine 3-7 segments that meaningfully differentiate behavior
3. **Balance coverage** - Include demographic (who), behavioral (what), psychographic (why)
4. **Validate relevance** - Each segment should drive actionable differences in approach

Example good persona composition:

.. code-block:: text

    Persona: "Aspirational Homebuyer"
    - DEMOGRAPHIC: Age → 25-34 (Millennials - Younger)
    - DEMOGRAPHIC: Life Stage → Young Couple - No Children
    - BEHAVIORAL: Customer Journey Stage → Consideration
    - BEHAVIORAL: Decision Speed → Extended Research (1+ months)
    - PSYCHOGRAPHIC: Core Values → Financial Security
    - PSYCHOGRAPHIC: Life Priorities → Family-Focused
    - PSYCHOGRAPHIC: Social Class → Aspirational (Upward Mobile)

Avoiding Over-Segmentation
---------------------------

Too many segments can create overly narrow, impractical personas:

❌ **Bad** - Too specific, impractical to target:

.. code-block:: text

    "25-34, Male, Married, 2 Children, $75K-$100K, Bachelor's Degree,
    White Collar, Urban Core, Democrat, iPhone User, Netflix Subscriber,
    Coffee Enthusiast, Dog Owner, Plays Golf"

✅ **Good** - Actionable, meaningful differentiation:

.. code-block:: text

    "Young Urban Professional"
    - DEMOGRAPHIC: Age → 25-34, Urbanicity → Urban Core,
                   Occupation → Professional/White Collar
    - BEHAVIORAL: Digital Behavior → Mobile-First User,
                  Purchase Channel → Online Only
    - PSYCHOGRAPHIC: Life Priorities → Career-Focused,
                     Core Values → Achievement & Success

Data Quality
------------

Maintain segment data quality:

1. **Mutual exclusivity** - Within a vector, values should be mutually exclusive (can't be both "Urban Core" AND "Rural")
2. **Comprehensive coverage** - Values should cover the full range of the dimension
3. **Consistent granularity** - Similar level of detail across related vectors
4. **Clear definitions** - Each value should have unambiguous meaning
5. **Active maintenance** - Regularly review and update segments as market evolves

Technical Reference
===================

Model APIs
----------

**Segment.insights_as_markdown()**
   Returns formatted markdown string of segment insights

**Persona.segment_count()**
   Returns count of attached non-geographic segments

**Persona.__str__()**
   Returns formatted string: "Persona Name (REGION/COUNTRY/LANGUAGE)"

JSON Schemas
-------------

All segmentation data files adhere to formal JSON schemas stored in ``data/schemas/``. These schemas provide validation rules and structure documentation.

Segments Schema
~~~~~~~~~~~~~~~

**Location**: ``data/schemas/segments.schema.json``

**Description**: Validates the structure of segment definitions in ``data/segments.json``

**Schema Type**: Array of segment objects

**Required Fields**:
   - ``category`` - Must be one of: DEMOGRAPHIC, BEHAVIORAL, PSYCHOGRAPHIC
   - ``vector`` - Dimension name (1-100 characters)
   - ``value`` - Position on dimension (1-100 characters)
   - ``is_active`` - Boolean flag

**Optional Fields**:
   - ``description`` - Longer segment description
   - ``insights`` - Array of structured insight objects

**Insights Structure** (when present):
   - ``heading`` (required) - Category heading (e.g., "Core Motivations", "Communication Style")
   - ``points`` (required) - Array of insight points (minimum 1 item)

**Validation Rules**:
   - ``category`` must be an enum value (DEMOGRAPHIC | BEHAVIORAL | PSYCHOGRAPHIC)
   - ``vector`` and ``value`` have minimum length of 1 character
   - ``vector`` and ``value`` have maximum length of 100 characters
   - Additional properties beyond the schema are not allowed

**Example**:

.. code-block:: json

    [
        {
            "category": "PSYCHOGRAPHIC",
            "vector": "VALS Framework",
            "value": "Innovators",
            "description": "Successful, sophisticated consumers with high self-esteem",
            "insights": [
                {
                    "heading": "Characteristics",
                    "points": [
                        "High income and resources",
                        "Active consumers",
                        "Image is important but as expression of taste"
                    ]
                },
                {
                    "heading": "Marketing Implications",
                    "points": [
                        "Receptive to new products and technologies",
                        "Premium and niche offerings",
                        "Sophisticated messaging"
                    ]
                }
            ],
            "is_active": true
        }
    ]

Personas Schema
~~~~~~~~~~~~~~~

**Location**: ``data/schemas/personas.schema.json``

**Description**: Validates the structure of persona definitions in ``data/personas.json``

**Schema Type**: Array of persona objects

**Required Fields**:
   - ``name`` - Persona name (1-200 characters)
   - ``is_active`` - Boolean flag

**Optional Fields**:
   - ``description`` - Persona description
   - ``region_code`` - Region code reference (must match existing Region.code)
   - ``country_code`` - Country ISO code reference (must match existing Country.code)
   - ``language_code`` - Language locale code reference (must match existing Language.code)

**Validation Rules**:
   - ``name`` has minimum length of 1 character, maximum 200 characters
   - ``region_code`` (if present) must match pattern: ``^[A-Z_]+$`` (uppercase letters and underscores)
   - ``country_code`` (if present) must match pattern: ``^[A-Z]{2}$`` (ISO 3166-1 alpha-2 format)
   - ``language_code`` (if present) must match pattern: ``^[a-z]{2}-[A-Z]{2}$`` (e.g., en-US, fr-CA)
   - Geographic codes must reference existing database records
   - Additional properties beyond the schema are not allowed

**Example**:

.. code-block:: json

    [
        {
            "name": "Luxury Experience Seeker",
            "description": "Affluent traveler prioritizing unique experiences over material possessions",
            "region_code": "NA",
            "country_code": "US",
            "language_code": "en-US",
            "is_active": true
        },
        {
            "name": "Budget-Conscious Student",
            "description": "Cost-sensitive younger demographic focused on value",
            "region_code": null,
            "country_code": null,
            "language_code": null,
            "is_active": true
        }
    ]

Persona-Segment Mappings Schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Location**: ``data/schemas/persona_segments.schema.json``

**Description**: Validates the many-to-many relationships between personas and segments in ``data/persona_segments.json``

**Schema Type**: Array of mapping objects

**Required Fields**:
   - ``persona_name`` - Name of persona (must match existing Persona.name)
   - ``segment_category`` - Segment category (DEMOGRAPHIC | BEHAVIORAL | PSYCHOGRAPHIC)
   - ``segment_vector`` - Segment dimension (must match existing Segment.vector)
   - ``segment_value`` - Segment value (must match existing Segment.value)
   - ``order_index`` - Display order (integer ≥ 0)

**Validation Rules**:
   - ``persona_name`` must match an existing persona's name exactly (1-200 characters)
   - ``segment_category`` must be an enum value (DEMOGRAPHIC | BEHAVIORAL | PSYCHOGRAPHIC)
   - ``segment_vector`` and ``segment_value`` must match an existing segment (1-100 characters each)
   - The combination (category, vector, value) must reference a valid segment
   - ``order_index`` must be a non-negative integer (controls display order within persona)
   - Additional properties beyond the schema are not allowed

**Example**:

.. code-block:: json

    [
        {
            "persona_name": "Luxury Experience Seeker",
            "segment_category": "DEMOGRAPHIC",
            "segment_vector": "Income Tier",
            "segment_value": "Affluent",
            "order_index": 0
        },
        {
            "persona_name": "Luxury Experience Seeker",
            "segment_category": "BEHAVIORAL",
            "segment_vector": "Purchase Behavior Type",
            "segment_value": "Experience Seeker",
            "order_index": 1
        },
        {
            "persona_name": "Luxury Experience Seeker",
            "segment_category": "PSYCHOGRAPHIC",
            "segment_vector": "Core Values",
            "segment_value": "Innovation & Progress",
            "order_index": 2
        }
    ]

Schema Validation
~~~~~~~~~~~~~~~~~

All import operations automatically validate data against these schemas. If validation fails, the import process will report specific errors indicating:

- Which file failed validation
- Which field violated the schema
- What the expected format/value should be
- The line/item number where the error occurred

To validate data files manually before import:

.. code-block:: bash

    # Install JSON schema validator (if not already installed)
    pip install jsonschema

    # Validate segments
    jsonschema -i data/segments.json data/schemas/segments.schema.json

    # Validate personas
    jsonschema -i data/personas.json data/schemas/personas.schema.json

    # Validate persona-segment mappings
    jsonschema -i data/persona_segments.json data/schemas/persona_segments.schema.json

Common Validation Errors
~~~~~~~~~~~~~~~~~~~~~~~~~

**Invalid category value**:

.. code-block:: text

    Error: 'GEOGRAPHIC' is not one of ['DEMOGRAPHIC', 'BEHAVIORAL', 'PSYCHOGRAPHIC']
    Solution: Use only DEMOGRAPHIC, BEHAVIORAL, or PSYCHOGRAPHIC

**Country code format**:

.. code-block:: text

    Error: 'USA' does not match pattern '^[A-Z]{2}$'
    Solution: Use ISO 3166-1 alpha-2 code (e.g., 'US' not 'USA')

**Language code format**:

.. code-block:: text

    Error: 'en' does not match pattern '^[a-z]{2}-[A-Z]{2}$'
    Solution: Include country variant (e.g., 'en-US' not 'en')

**Missing required field**:

.. code-block:: text

    Error: 'category' is a required property
    Solution: Add the missing required field to the object

**Invalid reference**:

.. code-block:: text

    Error: Segment not found for category=BEHAVIORAL, vector=Invalid, value=Test
    Solution: Ensure segment exists before referencing in persona_segments.json

JSON Structure Examples
-----------------------

**Complete Segment Example**:

.. code-block:: json

    {
        "category": "PSYCHOGRAPHIC",
        "vector": "VALS Framework",
        "value": "Innovators",
        "description": "Successful, sophisticated consumers with high self-esteem",
        "insights": [
            {
                "heading": "Characteristics",
                "points": [
                    "High income and resources",
                    "Active consumers",
                    "Image is important but as expression of taste"
                ]
            }
        ],
        "is_active": true
    }

**Complete Persona Example**:

.. code-block:: json

    {
        "name": "Luxury Experience Seeker",
        "description": "Affluent traveler prioritizing unique experiences",
        "region_code": "NA",
        "country_code": "US",
        "language_code": "en-US",
        "is_active": true
    }

**Complete PersonaSegment Example**:

.. code-block:: json

    {
        "persona_name": "Luxury Experience Seeker",
        "segment_category": "DEMOGRAPHIC",
        "segment_vector": "Income Tier",
        "segment_value": "Affluent",
        "order_index": 0
    }

Further Reading
===============

Marketing Framework Resources
------------------------------

- **VALS Framework**: Strategic Business Insights - `VALS Segmentation <https://www.strategicbusinessinsights.com/vals/>`_
- **Diffusion of Innovations**: Rogers, E. M. (2003). *Diffusion of Innovations* (5th ed.)
- **AIO Variables**: Plummer, J. T. (1974). "The Concept and Application of Life Style Segmentation"
- **Customer Journey**: Lemon & Verhoef (2016). "Understanding Customer Experience Throughout the Customer Journey"
- **Net Promoter Score**: Reichheld, F. (2003). "The One Number You Need to Grow"

Related Documentation
---------------------

- :doc:`/developer/data-schemas` - JSON schema definitions for all data files
- :doc:`/developer/architecture` - System architecture and design patterns
- :doc:`/developer/api/index` - API reference documentation
- :doc:`/user/quickstart` - Getting started guide
