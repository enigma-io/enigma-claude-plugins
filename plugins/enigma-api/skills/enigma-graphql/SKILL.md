---
name: enigma-graphql
description: Search and discover businesses using the Enigma GraphQL API. Use when the user wants to find/search/discover/list businesses (by name, industry, location, or characteristics), look up a specific company, search for people or business owners, analyze market segments (e.g., "coffee shops in California", "restaurants in New York"), find businesses by criteria (revenue, operating status, has/lacks phone/email, technology used), verify legal entities, check corporate structure, or explore the Enigma business intelligence graph. Handles both entity resolution (known business names like "Starbucks") and semantic discovery (industry/type-based search like "coffee shops" or "auto repair"). This is the primary skill for ALL Enigma business data lookups and market research queries.
---

# Enigma GraphQL API Skill

You are an expert at constructing and executing GraphQL queries against the Enigma business intelligence API.

## API Basics

- **Endpoint**: `https://api.enigma.com/graphql`
- **Auth**: `x-api-key` header — user must have `ENIGMA_API_KEY` set
- **Method**: POST with `Content-Type: application/json`
- **Docs**: https://documentation.enigma.com/
- **Playground**: https://console.enigma.com/explore/graphql
- **NEVER use curl** — the API key contains characters that break shell argument parsing. Always use Python `urllib`.
- **ALWAYS use heredoc** — `python3 << 'PYEOF'` (NOT `python3 -c`) to avoid `$` escaping issues.

## Entity Model

| EntityType | Description | Key Connections | Scalar Fields |
|---|---|---|---|
| `BRAND` | A business brand/company | `operatingLocations`, `legalEntities`, `industries`, `activities`, `cardTransactions` | `names`, `websites`, `revenueQualities`, `isMarketables`, `locationDescriptions` |
| `OPERATING_LOCATION` | A physical business location | `brands`, `cardTransactions`, `ranks`, `technologiesUseds`, `reviewSummaries` | `names`, `addresses`, `phoneNumbers`, `operatingStatuses`, `websites`, `locationTypes` |
| `LEGAL_ENTITY` | A registered legal entity | `operatingLocations`, `roles`, `persons`, `registeredEntities`, `isFlaggedByWatchlistEntries`, `appearsOnWatchlistEntries`, `bankruptcies`, `cannabisLicenses`, `negativeNewses` | `names`, `tins`, `addresses`, `types` |
| `PERSON` | A person (officer, owner, agent) | `legalEntities` (person-type LE nodes) → traverse `roles` → `registrations` → `registeredEntities` to get companies | `names` (firstName, lastName, fullName, dateOfBirth) |

## Choosing the Right Entity Type

| User Intent | Start With | Why |
|---|---|---|
| "Find info about [company]" | `BRAND` | Top-level business entity |
| "Find info about [company] — include people, revenue, HQ" | `BRAND` with `name` (+ optional `website`) | See Brand Profile recipe (`examples/brand/03_brand_profile.md`) |
| "Find locations of [brand] in [state]" | `BRAND` → filter `operatingLocations` | **NEVER** search `OPERATING_LOCATION` by brand name — returns empty |
| "Find a specific store at [address]" | `OPERATING_LOCATION` | Direct location lookup. **Must include `street1`** |
| "Revenue for a specific location" | `OPERATING_LOCATION` with street address → `cardTransactions` | Per-location revenue. Do NOT use Brand-level — it includes entire chain |
| "Revenue for each location of [brand]" | `BRAND` → `operatingLocations` → `cardTransactions` | Per-location without needing addresses |
| "Monthly/quarterly revenue trends" | `OPERATING_LOCATION` → `cardTransactions` with `period: "1m"` or `"3m"` | Time series data |
| "Find all [business type] in [area]" | `BRAND` with `prompt` + `conditions` | Discovery — use `prompt` not `name` |
| "Find all [type] locations in [area] (interactive)" | `OPERATING_LOCATION` with `brands.industries.industryDesc` | Precise industry matching at location level. See `examples/discovery/11_ol_industry_discovery.md` |
| "Get contacts for [brand]" | `BRAND` → `operatingLocations` → `roles` | `Brand.roles` is empty — must traverse through OLs |
| "Verify a business / check filings" | `LEGAL_ENTITY` | Registrations, officers, TINs, watchlists |
| "Get formation info for a legal entity" | `LEGAL_ENTITY` with `name` | See `examples/legal_entity/09_legal_entity_profile.md` |
| "Who owns [business]?" | `BRAND` → `legalEntities` | Corporate structure |
| "Who are the officers?" | `LEGAL_ENTITY` → `registeredEntities` → `registrations` → `roles` → `legalEntities` | People are on registrations, NOT `LegalEntity.persons` (usually empty) |
| "Find a person / companies they own" | `PERSON` with `person: { firstName, lastName }` | Person search |
| "Risk assessment / revenue quality" | `BRAND` with `revenueQualities` + `cardTransactions` | See `examples/risk/12_risk_signals.md` |
| "Full brand data dump" | `BRAND` comprehensive query | See `examples/brand/13_brand_dump.md` |
| "How many [businesses] in [area]?" | `aggregate` query with `count(field: ...)` | Much faster than paginating |
| "Export all [type] in [area]" | `OPERATING_LOCATION` with `output: { filename }` | Bulk export to S3 |
| "EIN/TIN for this location" | `OPERATING_LOCATION` with `@coalesce` | Resolves EIN via fallback paths |
| "When was this business formed?" | `OPERATING_LOCATION` with `@coalesce` | Resolves formation year via fallback |
| "Check compliance / KYB" | `LEGAL_ENTITY` | Watchlist entries, bankruptcies, registrations |

## Franchise & Chain Resolution

V2 GraphQL resolves locations to their **parent brand chain**, not individual franchisees.

**Example**: Searching `BRAND` for a Days Inn franchisee returns "Days Inn by Wyndham" with $646M revenue across 1,969 locations, not the ~$331K single-location revenue.

**How to detect**: Brand result has hundreds/thousands of locations but user asked about one specific business.

**How to get single-location data**:
1. Search `OPERATING_LOCATION` with name + full address (including `street1`)
2. Query that location's `cardTransactions` for per-location revenue
3. See `examples/revenue/06_brand_revenue.md` for the correct pattern

## SearchInput

```graphql
input SearchInput {
  name: String              # Entity resolution — match by known business name
  prompt: String            # Semantic discovery — match by type/industry (BRAND only)
  entityType: EntityType!   # BRAND | OPERATING_LOCATION | LEGAL_ENTITY | PERSON
  address: AddressInput     # { street1, city, state (2-letter), postalCode }
  person: PersonInput       # For PERSON: { firstName, lastName, dateOfBirth?, address? }
  website: String           # Optional: narrow brand matches
  output: OutputInput       # { filename } — triggers bulk export (see examples/export/)
  conditions: Conditions    # Optional: server-side filtering (filter, limit, orderBy)
  matchThreshold: Float     # 0-1, filter by match confidence
}
```

**`name` vs `prompt`** — two fundamentally different search modes:
- **`name`**: Entity resolution. You must know the business name (e.g., `"Starbucks"`, `"Enigma Technologies Inc"`). Works with all entity types.
- **`prompt`**: Semantic industry discovery. Finds businesses by type/description (e.g., `"coffee shop"`, `"italian restaurant"`, `"auto repair"`). **Only works with `entityType: BRAND`**. Combine with `conditions` for geographic and status filtering.

**CRITICAL**: When users ask to discover/find/list businesses by category or industry in an area, ALWAYS use `prompt` — not `name`. Using `name` with a generic term like "coffee" will fail or return irrelevant results.

**AGENT BEHAVIOR — street1 check**: When building an `OPERATING_LOCATION` search without a street address, notify the user: *"For reliable results, I recommend including a street address. Without it, the API may return no results. Do you have one?"*

### SearchInput Conditions (for Discovery)

When using `prompt`, attach `conditions` directly on the `SearchInput` to filter which brands are returned. This is different from connection-level `conditions` (which filter nested edges like `operatingLocations`).

```json
{
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "IN": ["operatingLocations.addresses.zip", ["12983", "12946"]] },
          { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
        ]
      },
      "limit": 10
    }
  }
}
```

**SearchInput condition field paths for `BRAND`**:

| Filter | Field Path |
|---|---|
| State | `operatingLocations.addresses.state` |
| City | `operatingLocations.addresses.city` (UPPERCASE) |
| Zip code | `operatingLocations.addresses.zip` |
| Operating status | `operatingLocations.operatingStatuses.operatingStatus` (`Open` / `Closed`) |
| Industry code (NAICS) | `industries.industryCode` (pair with `industries.industryType` = `naics_2022_code`) |
| Has phone | `operatingLocations.roles.phoneNumbers` (use `HAS` operator) |
| Has email | `operatingLocations.roles.emailAddresses` (use `HAS` operator) |
| Card revenue | `cardTransactions.projectedQuantity` (pair with `period` and `quantityType` filters) |

**SearchInput condition field paths for `OPERATING_LOCATION`**:

| Filter | Field Path |
|---|---|
| State | `addresses.state` |
| City | `addresses.city` (UPPERCASE) |
| Zip code | `addresses.zip` |
| Operating status | `operatingStatuses.operatingStatus` (`Open` / `Closed`) |
| Industry (Enigma label) | `brands.industries.industryDesc` (pair with `brands.industries.industryType` = `enigma_industry_description`) |
| Industry (NAICS code) | `brands.industries.industryCode` (pair with `brands.industries.industryType` = `naics_2022_code`) |

**Note**: The address field for zip codes is `zip` (NOT `postalCode`). The `postalCode` field only exists on `AddressInput`, not on the `Address` type used in conditions.

## Industry & NAICS Code Mapping

Brands in the Enigma API have two types of industry classification on the `industries` connection:
- **`naics_2022_code`** — official 2022 NAICS code (e.g., `722515` = "Snack and Nonalcoholic Beverage Bars")
- **`enigma_industry_description`** — Enigma's own semantic label (e.g., "coffee shop")

When a user provides an industry description, CRM industry label, or NAICS code as input, use this section to translate it into the correct NAICS 2022 code for `industries.industryCode` filtering.

### Mapping User Input to NAICS Codes

**Step 1: Parse input** — the user may provide a descriptive string (e.g., "HVAC"), a NAICS code (e.g., "238220"), or both.

**Step 2: Validate codes** — if a NAICS code is provided, confirm it's a valid 2022 code. Old 2017 codes may need remapping.

**Step 3: Choose the right granularity**:
- **2-digit** (Sector): Very broad (e.g., `23` = Construction). Use when the input spans multiple subsectors.
- **4-digit** (Industry Group): Moderate (e.g., `8111` = Automotive Repair and Maintenance). Use when the input is a broad category within a sector.
- **6-digit** (National Industry): Specific (e.g., `238220` = Plumbing, Heating, and Air-Conditioning Contractors). Use when the input maps cleanly to a single industry.
- **Skip 3-digit and 5-digit levels** — they don't align well with Enigma's data.

### Using NAICS Codes in Queries

**Filter brands by NAICS code** — use paired conditions on `industries.industryCode` and `industries.industryType`:

```json
{
  "searchInput": {
    "prompt": "plumber",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "EQ": ["industries.industryCode", "238220"] },
          { "IN": ["industries.industryType", "naics_2022_code"] },
          { "EQ": ["operatingLocations.addresses.state", "NY"] }
        ]
      },
      "limit": 10
    }
  }
}
```

**When to use `prompt` vs NAICS filtering**:
- **`prompt` alone**: Best for broad semantic discovery where you want the API to interpret intent (e.g., "coffee shop"). May return adjacent industries.
- **NAICS filter alone**: Best for precise industry segmentation when you know the exact code. Strict match.
- **`prompt` + NAICS filter**: Most precise — semantic relevance narrowed to a specific NAICS code. Use when the user provides both an industry description and wants tight classification.

For the full NAICS reference table, see `references/naics_2022_mapping.json`.

## Pagination

All connections use Relay-style cursor pagination. Max page size: `first: 100`.

**No `totalCount`**: Connections do NOT support `totalCount`. Requesting it causes HTTP 400. The only way to know the total number of items is to paginate through all pages and count, or use `hasNextPage` to detect whether more exist.

Arguments: `first`, `last`, `after`, `before`, `conditions`.

### Cursor Bug

The first page query must NOT declare `$cursor` as a variable. Subsequent pages must include it. Using two separate query strings avoids HTTP 400 errors.

See `references/pagination_template.py` for the standard pagination implementation (max 3 pages).

## Connection Filtering

Connections accept `conditions: { filter: JSON }` for server-side filtering. See `references/filter_syntax.md` for complete filter syntax and examples.

**Quick reference**:
- **Operators**: `EQ`, `NE`, `GT`, `GTE`, `LT`, `LTE`, `IN`, `LIKE`, `ILIKE`, `HAS`, `IS_NULL`, `IS_NOT_NULL`
- **Combine**: `AND`, `OR`, `NOT`
- **Syntax**: `{ "OPERATOR": ["field.path", value] }`
- **`IS_NULL`/`IS_NOT_NULL`** — single-element array (field path only): `{ "IS_NULL": ["platformBrandId"] }`
- **Field paths**: Use dot notation (e.g., `addresses.state`, `operatingLocations.addresses.zip`)

**Important**: Field values are typically UPPERCASE in the Enigma dataset (e.g., `"NY"` not `"ny"`, `"NEW YORK"` not `"New York"`). Use `ILIKE` for case-insensitive matching if unsure.

## Advanced Directives

### `@coalesce` — Return first non-null from multiple paths

`_fn @coalesce(refs: [...])` resolves the first non-null value from multiple graph traversal paths. Use with `@skip(if: true)` to declare paths without returning their data.

**Rules for `@coalesce`**:
- The field **must be aliased** (e.g., `legalName: _fn @coalesce(...)`)
- Array indices in path use `.0.` notation (e.g., `edges.0.node`)
- The referenced paths **must be declared** in the query body (even if hidden with `@skip(if: true)`)

See `examples/derived/07_coalesce_ein_formation.md` for EIN lookup and formation year patterns.

### `@skip` — Conditionally exclude from response

Use `@skip(if: true)` to include a field for `@coalesce` reference purposes without including it in the output. Every `@coalesce` block must have corresponding backing fields with `@skip(if: true)`.

## Background Tasks (Large Result Sets)

When `output: { filename: "..." }` is provided on `searchInput`, the API triggers a background export. The data response is `null`, but `extensions.backgroundTasks` contains a signed S3 URL to download the full result set.

```json
{
  "extensions": {
    "backgroundTasks": [
      {
        "id": "uuid",
        "status": "SUCCESS",
        "result": ["https://...s3.amazonaws.com/...signed-url..."]
      }
    ]
  },
  "data": { "search": null }
}
```

Use background tasks when a query might return thousands of locations (e.g., all nail salons in a state). The signed URL is valid for ~6 days. Download with `urllib.request.urlretrieve(url, "output.json")`.

See `examples/export/08_segment_export.md` for a complete working example.

## Execution Template

**Always check for the API key first**, then use this template:

```bash
python3 << 'PYEOF'
import json, urllib.request, os

query = '''YOUR_QUERY_HERE'''

variables = { 'searchInput': { 'name': 'BUSINESS_NAME', 'entityType': 'ENTITY_TYPE' } }

payload = json.dumps({'query': query, 'variables': variables})
req = urllib.request.Request(
    'https://api.enigma.com/graphql',
    data=payload.encode(),
    headers={'content-type': 'application/json', 'x-api-key': os.environ['ENIGMA_API_KEY']}
)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    if 'errors' in data:
        for err in data['errors']:
            print(f'GraphQL Error: {err.get("message", err)}')
    else:
        print(json.dumps(data, indent=2))
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()}')
except KeyError:
    print('ERROR: ENIGMA_API_KEY not set. Run: export ENIGMA_API_KEY=your_key')
PYEOF
```

## Query Patterns by Use Case

### Discovery: Find All Businesses of Type X in an Area

Use `prompt` for semantic industry discovery. This finds businesses you don't know by name. **Only works with `entityType: BRAND`**.

See `examples/discovery/01_coffee_shops_zip.md` for a complete working example.

**Key pattern**: Use `prompt` on `SearchInput` with `conditions.filter` to narrow by geography/status:

```json
{
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "IN": ["operatingLocations.addresses.zip", ["12983", "12946"]] },
          { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
        ]
      },
      "limit": 50
    }
  }
}
```

### Discovery: OPERATING_LOCATION by Industry Label

Alternative to BRAND+prompt. Use `OPERATING_LOCATION` with `brands.industries.industryDesc` for **precise** industry label matching.

See `examples/discovery/11_ol_industry_discovery.md` for a complete working example.

**BRAND+prompt vs OPERATING_LOCATION+industry filter**:
- Use `BRAND` + `prompt` for semantic discovery (e.g., "trendy coffee shop") — flexible but may include adjacent categories
- Use `OPERATING_LOCATION` + `brands.industries.industryDesc` for precise category matching when you know the Enigma industry label exactly (e.g., "nail salon", "auto repair")

### KYB: Corporate Structure & Officers

Search `BRAND`, traverse to `legalEntities`, then into `registeredEntities → registrations → roles` for officers.

See `examples/kyb/02_officers_lookup.md` for a complete working example.

**Key pattern**: Officers are on `Registration.roles`, NOT `LegalEntity.persons` (which is usually empty).

### KYB: Full Verification with TINs, Watchlists, Bankruptcies

Search `LEGAL_ENTITY` directly for compliance data including TIN validity, watchlist screening, and bankruptcy records.

See `examples/kyb/10_kyb_verify.md` for verification queries and registration interpretation guidance.

### Person Search: Find Someone's Companies

Use `PERSON` entity type with `person: { firstName, lastName }`, then traverse:
`Person → legalEntities → roles → registrations → registeredEntities`

See `examples/person_search/04_find_person_companies.md` for a complete working example.

### Revenue: Brand-Level Card Transactions

Card transactions are available on both `Brand` and `OperatingLocation` entities.

**ALWAYS filter `cardTransactions`** — never query unfiltered (returns hundreds of records).

**Standard filter** for most recent 12-month aggregate revenue:

```json
{
  "filter": { "AND": [
    { "EQ": ["period", "12m"] },
    { "EQ": ["quantityType", "card_revenue_amount"] },
    { "EQ": ["rank", 0] },
    { "IS_NULL": ["platformBrandId"] }
  ]}
}
```

**CRITICAL**: The `IS_NULL: ["platformBrandId"]` filter is **mandatory** at Brand level. Without it, revenue appears **2x-5x inflated** due to aggregate + per-platform records being summed. At OL level, do NOT use this filter — `platformBrandId` doesn't exist on OL transactions.

See `examples/revenue/06_brand_revenue.md` for a complete working example with multiple metrics.

### Locations: Filter by State/City

**NEVER search `OPERATING_LOCATION` by brand name** — it returns empty results.

Instead: Search `BRAND` by name, then filter `operatingLocations` connection server-side:

```graphql
operatingLocations(first: 100, conditions: $locConditions) {
  edges { node { ... } }
}
```

```json
{
  "locConditions": {
    "filter": { "EQ": ["addresses.state", "NY"] }
  }
}
```

See `examples/locations/05_brand_locations_by_state.md` for a complete working example.

## Field Name Corrections

The GraphQL schema has non-intuitive field names. When you encounter an error, consult `references/field_corrections.json` for the correct field name.

**Common mistakes**:
- `OperatingLocationOperatingStatus.status` → `operatingStatus`
- `Website.url` → `website`
- `Industry.description` → `industryDesc`
- `Role.title` → `jobTitle`
- `BrandCardTransaction.amount` → `projectedQuantity`
- `ReviewSummary.averageRating` → `reviewScoreAvg`
- `RegisteredEntity.formationDate` → `formationYear` (Int, NOT Date)

## Introspection (Troubleshooting)

When a field name causes an error, introspect the type:

```bash
python3 << 'PYEOF'
import json, urllib.request, os
query = '{ __type(name: "TYPE_NAME_HERE") { fields { name type { name kind ofType { name } } } } }'
payload = json.dumps({'query': query})
req = urllib.request.Request('https://api.enigma.com/graphql', data=payload.encode(),
    headers={'content-type': 'application/json', 'x-api-key': os.environ['ENIGMA_API_KEY']})
data = json.loads(urllib.request.urlopen(req).read())
for f in data['data']['__type']['fields']:
    print(f"{f['name']}: {f['type']['name'] or f['type']['kind']}")
PYEOF
```

## Aggregate Queries (Counts)

Use `aggregate` with `count(field: ...)` to get counts without paginating. **Much faster** than fetching all pages.

**Accepted `count` fields** (singular): `"brand"`, `"operatingLocation"`, `"legalEntity"`

```graphql
query Aggregate($searchInput: SearchInput!) {
  aggregate(searchInput: $searchInput) {
    brandsCount: count(field: "brand")
    locationsCount: count(field: "operatingLocation")
  }
}
```

`count()` also works on `search` results for brand-level counting. Field names are **plural** here (`"operatingLocations"`, `"legalEntities"`). Use aliases when calling `count()` multiple times.

For full examples including filtered counts, see `references/pagination_template.py`.

## Mandatory Guardrails

These prevent silent data quality issues. ALWAYS apply when constructing queries.

### 1. platformBrandId IS_NULL Filter (Brand Card Transactions)

When querying `cardTransactions` at **Brand level**, ALWAYS include:
```json
{ "IS_NULL": ["platformBrandId"] }
```

Without this, revenue appears **2x-5x inflated** due to aggregate + per-platform records being summed.

**At OL level**: Do NOT use this filter — `platformBrandId` doesn't exist on OL transactions.

### 2. Explicit periodEndDate (Multi-Metric Card Transactions)

For queries with 2+ card transaction metrics, use explicit `periodEndDate` instead of `rank=0`:
```json
{ "EQ": ["periodEndDate", "2024-12-31"] }
```

This prevents temporal misalignment if data updates between filter construction. Single-metric queries can safely use `rank=0`.

### 3. Temporal Consistency

Some `quantityType` values have limited history:
- **Limited**: `card_not_present_revenue_amount` (1-3 months, Brand-level only)
- **Full history**: All other metrics

Warn users if they request limited-availability metrics for dates >3 months ago.

## Workflow

```
Task Progress:
- [ ] Step 1: Identify search mode (name vs prompt)
- [ ] Step 2: Choose entity type using the decision matrix
- [ ] Step 3: If card transactions needed — ask user for periodEndDate
- [ ] Step 4: Check API key
- [ ] Step 5: Read the relevant example file and select/compose query
- [ ] Step 6: Execute via the execution template (NEVER curl, ALWAYS heredoc)
- [ ] Step 7: Check for errors — look for "errors" key before formatting
- [ ] Step 8: Format results — tables for lists, structured summaries for singles
- [ ] Step 9: Paginate if needed (max 3 pages)
```

## Formatting & Error Handling

**Formatting**:
- **Lists**: Markdown table. Show "Found X results."
- **Single entity**: Structured summary with labeled fields.
- **Empty results**: Suggest alternative entity type or `prompt`-based discovery.
- **Paginated**: "Showing X of Y+ results. Want me to fetch more?"

**Common errors**:

| Error | Cause | Fix |
|---|---|---|
| HTTP 401 | Bad/missing API key | Check `ENIGMA_API_KEY` |
| HTTP 400 | Malformed query | Check field names, cursor bug, variables. Do NOT use `totalCount`. |
| "Cannot query field" | Wrong field name | See `references/field_corrections.json` |
| Empty results | Wrong entity type or name | Try different entity type per decision matrix |
| Empty OPERATING_LOCATION results | Missing `street1` | Always include `street1` for OL searches |
| Null fields | Normal — not all fields populated | Report available data, skip nulls |

## Examples by Use Case

Read the relevant example file based on the user's request:

| Use Case | Example File |
|---|---|
| Find businesses by type/industry (BRAND+prompt) | `examples/discovery/01_coffee_shops_zip.md` |
| Find locations by industry label (OL+industryDesc) | `examples/discovery/11_ol_industry_discovery.md` |
| Brand profile, marketing, locations | `examples/brand/03_brand_profile.md` |
| Comprehensive brand data dump | `examples/brand/13_brand_dump.md` |
| Person search, brand contacts | `examples/person_search/04_find_person_companies.md` |
| KYB verification, officers, legal entity | `examples/kyb/02_officers_lookup.md` |
| KYB full verify (TINs, watchlists, bankruptcies, officers) | `examples/kyb/10_kyb_verify.md` |
| Legal entity profile (formation, registration) | `examples/legal_entity/09_legal_entity_profile.md` |
| Operating location profile | `examples/locations/05_brand_locations_by_state.md` |
| Revenue (brand, OL, per-location, time series) | `examples/revenue/06_brand_revenue.md` |
| Risk signals (revenue quality, transactions, status) | `examples/risk/12_risk_signals.md` |
| EIN/TIN lookup, formation year, @coalesce | `examples/derived/07_coalesce_ein_formation.md` |
| Segment / bulk export to S3 | `examples/export/08_segment_export.md` |
| Card transaction field reference | `references/card_transactions.md` |

## Additional Resources

- **Filter syntax**: `references/filter_syntax.md` — complete filter operators and examples
- **Field corrections**: `references/field_corrections.json` — correct field names for common errors
- **NAICS codes**: `references/naics_2022_mapping.json` — industry code mappings for discovery queries
- **Pagination template**: `references/pagination_template.py` — standard pagination implementation
- **Card transactions**: `references/card_transactions.md` — quantityType values, Brand vs OL differences
- **Query validator**: `scripts/validate_query.py` — static linter for common mistakes
- **Training examples**: `examples/` directory — complete working examples across all use cases
