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
- **Playground**: https://console.enigma.com/explore/graphql
- **NEVER use curl** — the API key contains characters that break shell argument parsing. Always use Python `urllib`.
- **ALWAYS use heredoc** — `python3 << 'PYEOF'` (NOT `python3 -c`) to avoid `$` escaping issues.

## Two Rules That Make Every Query Compile

These two shape rules are the difference between a query that works first try and an HTTP 400. They apply to **every** query below.

### Rule 1 — `search` returns a union, NOT a connection

`Query.search` is typed `[SearchUnion]` where the union members are `Brand`, `OperatingLocation`, `LegalEntity`, `Person`, `Address`. It returns a **plain list of nodes** — there is **no `edges`/`node`/`pageController` on `search` itself**.

Select fields with `__typename` + inline fragments:

```graphql
query($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand { names(first: 1) { edges { node { name } } } }
    ... on OperatingLocation { names(first: 1) { edges { node { name } } } }
  }
}
```

❌ `search(searchInput: $s) { edges { node { ... } } }` → **HTTP 400** `Cannot query field 'edges' on type 'SearchUnion'`.

`search` takes **no** `first:`/`after:` — it returns the matched candidate set. Pagination happens on the connections **inside** each returned node.

### Rule 2 — every nested field is a Relay connection

`names`, `websites`, `addresses`, `operatingLocations`, `legalEntities`, `cardTransactions`, `industries`, `roles`, `tins`, `registeredEntities`, `registrations`, `persons`, … are **all `*Connection` types**. You must traverse `(first: N) { edges { node { ... } } }`:

```graphql
names(first: 1) { edges { node { name } } }          # ✓
addresses(first: 1) { edges { node { streetAddress1 city state zip } } }  # ✓
```

❌ `names { name }` → **HTTP 400** `Cannot query field 'name' on type 'BrandNameConnection'`.

**Connection args**: `first`, `last`, `after`, `before`, `conditions`. Max page size `first: 100`.

**Two different `conditions` types** — getting this wrong is a 400:

| Where | GraphQL type | Has `limit`? |
|---|---|---|
| `searchInput.conditions` (top-level discovery) | `Conditions` | ✅ `filter`, `orderBy`, `limit`, `pageToken` |
| node-level aggregators `count(...conditions:)` | `Conditions` | ✅ |
| connection args, e.g. `operatingLocations(conditions:)`, `cardTransactions(conditions:)` | `ConnectionConditions` | ❌ `filter`, `orderBy` only |

When you declare a query variable for a **connection** condition, type it `ConnectionConditions` (not `Conditions`):
`query($s: SearchInput!, $lc: ConnectionConditions) { ... operatingLocations(first: 100, conditions: $lc) ... }`

## Entity Model

Common fields/connections per type (non-exhaustive — introspect for the full list).

| EntityType | Description | Key Connections | Common scalar leaves (inside `node`) |
|---|---|---|---|
| `BRAND` | A business brand/company | `operatingLocations`, `legalEntities`, `industries`, `activities`, `cardTransactions`, `websites`, `revenueQualities`, `isMarketables`, `roles` | `names.node.name`, `websites.node.website`, `industries.node.{industryDesc,industryCode,industryType}` |
| `OPERATING_LOCATION` | A physical business location | `brands`, `addresses`, `phoneNumbers`, `operatingStatuses`, `cardTransactions`, `roles`, `technologiesUseds`, `reviewSummaries`, `websites`, `locationTypes`, `ranks` | `names.node.name`, `addresses.node.{streetAddress1,city,state,zip,fullAddress}`, `phoneNumbers.node.phoneNumber`, `operatingStatuses.node.operatingStatus` |
| `LEGAL_ENTITY` | A registered legal entity | `operatingLocations`, `roles`, `persons`, `registeredEntities`, `tins`, `isFlaggedByWatchlistEntries`, `appearsOnWatchlistEntries`, `bankruptcies`, `types`, `headcounts` | `names.node.name`, `tins.node.{tin,tinType,validity}`, `types.node.legalEntityType` |
| `PERSON` | A person (officer, owner, agent) | `legalEntities`, `websites` | `names.node.{firstName,lastName,fullName,dateOfBirth}` |
| `ADDRESS` | A physical address node | `operatingLocations`, `registrations`, `legalEntities`, `watchlistEntries` | `streetAddress1`, `city`, `state`, `zip`, `latitude`, `longitude` |

**Tech stack**: `OperatingLocation.technologiesUseds.node.{technology,category}` (per-location). Brand-wide web tech lives under `websites` (introspect `Website`).

## Choosing the Right Entity Type

| User Intent | Start With | Why |
|---|---|---|
| "Find info about [company]" | `BRAND` (`name`) | Top-level business entity |
| "Find locations of [brand] in [state]" | `BRAND` (`name`) → filter `operatingLocations` connection | **NEVER** search `OPERATING_LOCATION` by brand name — returns empty |
| "Find a specific store at [address]" | `OPERATING_LOCATION` with `address` (`street1`) | Direct location lookup |
| "Revenue for a specific location" | `OPERATING_LOCATION` with address → `cardTransactions` | Per-location revenue (not whole chain) |
| "Revenue for each location of [brand]" | `BRAND` → `operatingLocations` → `cardTransactions` | Per-location without addresses |
| "Monthly/quarterly revenue trends" | `OPERATING_LOCATION` → `cardTransactions` (`period: "1m"`/`"3m"`) | Time series |
| "Find all [business type] in [area]" | `BRAND` with `prompt` + `conditions` | Semantic discovery — `prompt` only on BRAND search |
| "Get contacts for [brand]" | `BRAND` → `operatingLocations` → `roles` → `legalEntities` → `persons` | People hang off OL roles |
| "Verify a business / KYB / filings" | `LEGAL_ENTITY` (`name`) | TINs, registrations, watchlists, bankruptcies |
| "Who owns [business]?" | `BRAND` → `legalEntities` | Corporate structure |
| "Who are the officers?" | `LEGAL_ENTITY` → `registeredEntities` → `registrations` → `roles` → `legalEntities` → `persons` | Officers live on registration roles, not `LegalEntity.persons` |
| "Find a person / companies they own" | `PERSON` with `person: { firstName, lastName }` | Person search |
| "Risk / revenue quality" | `BRAND` with `revenueQualities` + `cardTransactions` | See `examples/risk/12_risk_signals.md` |
| "How many [businesses] in [area]?" | `aggregate` (entityType `OPERATING_LOCATION`) with `conditions.filter` | Counts — see Aggregate section (caveats!) |
| "Export all [type] in [area]" | `OPERATING_LOCATION` + `output: { filename }` | Bulk export to S3 |
| "EIN/TIN or formation year for this location" | `OPERATING_LOCATION` with `@coalesce` | Resolves via fallback paths |

## Franchise & Chain Resolution

V2 GraphQL resolves locations to their **parent brand chain**, not individual franchisees. A Days Inn franchisee searched as a `BRAND` returns "Days Inn by Wyndham" ($646M across ~1,969 locations), not the single-location ~$331K.

**Detect**: brand result has hundreds/thousands of locations but the user asked about one shop. **Fix**: search `OPERATING_LOCATION` with name + full `address` (incl. `street1`), then read that location's `cardTransactions`. See `examples/revenue/06_brand_revenue.md`.

## SearchInput

```graphql
input SearchInput {
  name: String              # Entity resolution — known business name
  prompt: String            # Semantic discovery — by type/industry (see search-mode rule below)
  entityType: EntityType    # BRAND | OPERATING_LOCATION | LEGAL_ENTITY | PERSON | ADDRESS
  address: AddressInput     # { street1, city, state (2-letter), postalCode }   ← input uses street1
  person: PersonInput       # For PERSON: { firstName, lastName, dateOfBirth?, address? }
  website: String           # Optional: narrow brand matches
  output: OutputSpec        # { filename } — triggers bulk export (see Export section)
  conditions: Conditions    # Top-level filtering (filter, orderBy, limit)
  matchThreshold: Float     # 0-1, filter by match confidence
}
```

> The **input** type `AddressInput` uses `street1`/`postalCode`. The **output** `Address` type uses `streetAddress1`/`zip`. Don't cross them.

**`name` vs `prompt`**:
- **`name`**: entity resolution; you know the business/legal-entity/person name. Works with all entity types.
- **`prompt`**: semantic industry discovery (e.g. `"coffee shop"`, `"auto repair"`).
  - On a regular `search`, **`prompt` requires `entityType: BRAND`**. `prompt` + `OPERATING_LOCATION` on `search` → 400 `Use entity type BRAND instead`.
  - `prompt` + `OPERATING_LOCATION` **is** allowed for `aggregate` and for `output` exports (see those sections).

**CRITICAL**: To discover/list businesses by category/industry, use `prompt` with `entityType: BRAND` — not `name`. A generic `name` like "coffee" returns junk.

**street1 check**: when building an `OPERATING_LOCATION` search without a street address, tell the user: *"For reliable results I recommend a street address — without one the API often returns nothing. Do you have one?"*

### SearchInput Conditions (Discovery)

With `prompt`, attach `conditions` on the `SearchInput` to narrow which brands return. (This `conditions` is type `Conditions` and supports `limit`.)

```json
{
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": { "AND": [
        { "IN": ["operatingLocations.addresses.zip", ["12983", "12946"]] },
        { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
      ] },
      "limit": 10
    }
  }
}
```

**SearchInput filter field paths — `entityType: BRAND`** (paths are brand-relative):

| Filter | Field Path |
|---|---|
| State | `operatingLocations.addresses.state` |
| City | `operatingLocations.addresses.city` (UPPERCASE) |
| Zip | `operatingLocations.addresses.zip` |
| Operating status | `operatingLocations.operatingStatuses.operatingStatus` (`Open`/`Closed`) |
| NAICS code | `industries.industryCode` (pair with `industries.industryType` = `naics_2022_code`) |
| Enigma label | `industries.industryDesc` (pair with `industries.industryType` = `enigma_industry_description`) |
| Has phone | `{ "HAS": ["operatingLocations.phoneNumbers"] }` |
| Has email | `{ "HAS": ["operatingLocations.roles.emailAddresses"] }` |

> `HAS` takes a path to a **connection/type**, never a scalar leaf. `{HAS:["operatingLocations.phoneNumbers.phoneNumber"]}` → 400.

> **Brand-level filter semantics**: a `SearchInput` filter on `operatingLocations.*` selects a brand if **any** of its locations matches — so a returned brand may still contain non-matching locations. To display only the matching locations, mirror the same predicate onto the `operatingLocations(conditions:)` connection (`ConnectionConditions`, OL-relative paths).

## Industry & NAICS Codes

Brands carry two industry classifications on `industries`:
- **`naics_2022_code`** — official 2022 NAICS (e.g. `722515` = "Snack and Nonalcoholic Beverage Bars").
- **`enigma_industry_description`** — Enigma's semantic label (e.g. "coffee shop").

To filter by code, pair `industries.industryCode` with `industries.industryType`:

```json
{ "AND": [
  { "EQ": ["industries.industryCode", "238220"] },
  { "EQ": ["industries.industryType", "naics_2022_code"] },
  { "EQ": ["operatingLocations.addresses.state", "NY"] }
] }
```

**NAICS filtering is EXACT string match on the stored code — it does NOT roll up by prefix.** Codes are stored at the **6-digit leaf** in almost all records. So `industryCode = "7225"` matches only the handful of rows literally coded `"7225"` (e.g. RI: `7225`→58) — **not** the 6-digit children (`722511`→1795, `722513`→672, `722515`→1265). A truncated/sector code silently undercounts.

To cover a whole category, **enumerate the 6-digit leaves** with `IN`:

```json
{ "AND": [
  { "IN": ["industries.industryCode", ["722511", "722513", "722514", "722515"]] },
  { "EQ": ["industries.industryType", "naics_2022_code"] }
] }
```

(RI restaurants this way ≈ 3,732, vs 58 for the 4-digit `7225`.) For fuzzy "all restaurants" coverage without enumerating codes, use `prompt` (BRAND search) or `enigma_industry_description`. `prompt` = broad/semantic; NAICS leaf-`IN` = precise/strict; combine for semantic relevance narrowed to chosen codes. Full table: `references/naics_2022_mapping.json`.

## Filtering (Connection & SearchInput)

- **Operators**: `EQ`, `NE`, `GT`, `GTE`, `LT`, `LTE`, `IN`, `LIKE`, `ILIKE`, `HAS`, `IS_NULL`, `IS_NOT_NULL`.
- **Combine**: `AND`, `OR`, `NOT`.
- **Syntax**: `{ "OPERATOR": ["field.path", value] }`. `IN` value is an array.
- **`IS_NULL`/`IS_NOT_NULL`/`HAS`**: single-element array (path only) — `{ "IS_NULL": ["platformBrandId"] }`, `{ "HAS": ["operatingLocations.phoneNumbers"] }`.
- **Field paths**: dot notation; for connection-level conditions the path is **relative to the node the connection hangs on** (e.g. on `operatingLocations(conditions:)` use `addresses.state`, not `operatingLocations.addresses.state`).
- **Values are UPPERCASE** in the dataset (`"NY"`, `"NEW YORK"`). Use `ILIKE` when unsure of case.

Full reference: `references/filter_syntax.md`.

## Pagination

Relay cursor pagination; max `first: 100`. **No `totalCount`** — requesting it is HTTP 400. Use `pageInfo { hasNextPage endCursor }` to walk pages, or `aggregate`/node-level `count` for totals. See `references/pagination_template.py` (max 3 pages by default).

## Execution Template

```bash
python3 << 'PYEOF'
import json, urllib.request, os

query = '''YOUR_QUERY_HERE'''
variables = { 'searchInput': { 'name': 'BUSINESS_NAME', 'entityType': 'BRAND' } }

payload = json.dumps({'query': query, 'variables': variables})
req = urllib.request.Request(
    'https://api.enigma.com/graphql',
    data=payload.encode(),
    headers={'content-type': 'application/json', 'x-api-key': os.environ['ENIGMA_API_KEY']})
try:
    data = json.loads(urllib.request.urlopen(req).read())
    if 'errors' in data:
        for err in data['errors']:
            print('GraphQL Error:', err.get('message', err) if isinstance(err, dict) else err)
    else:
        print(json.dumps(data, indent=2))
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()}')
except KeyError:
    print('ERROR: ENIGMA_API_KEY not set. Run: export ENIGMA_API_KEY=your_key')
PYEOF
```

Always check `data['errors']` (and HTTP status) before formatting results.

## Query Patterns by Use Case

Each pattern below is **verified against the live API**. Read the matching example file for a complete runnable version.

### Discovery: businesses of type X in an area (BRAND + prompt)

```graphql
query Discover($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      names(first: 1) { edges { node { name } } }
      operatingLocations(first: 5) {
        edges { node {
          names(first: 1) { edges { node { name } } }
          addresses(first: 1) { edges { node { streetAddress1 city state zip } } }
          phoneNumbers(first: 1) { edges { node { phoneNumber } } }
        } }
      }
    }
  }
}
```

```json
{ "searchInput": { "prompt": "coffee shop", "entityType": "BRAND",
  "conditions": { "filter": { "AND": [
    { "IN": ["operatingLocations.addresses.zip", ["12983", "12946"]] },
    { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
  ] }, "limit": 10 } } }
```

See `examples/discovery/01_coffee_shops_zip.md`. To **list raw locations** of an industry across an area (not grouped by brand), use the Export pattern or `aggregate` for counts — a regular `OPERATING_LOCATION` search does not accept `prompt`. See `examples/discovery/11_ol_industry_discovery.md`.

### KYB: corporate structure & officers

Officers live on `Registration.roles`, and a role's person is reached via `roles → legalEntities → persons → names`. `Role` has **no** `names`/`roleType` of its own (use `jobTitle`, `jobFunction`, `managementLevel`).

```graphql
query Officers($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      names(first: 1) { edges { node { name } } }
      legalEntities(first: 5) { edges { node {
        names(first: 1) { edges { node { name } } }
        registeredEntities(first: 5) { edges { node {
          registrations(first: 5) { edges { node {
            roles(first: 20) { edges { node {
              jobTitle jobFunction managementLevel
              legalEntities(first: 1) { edges { node {
                persons(first: 1) { edges { node {
                  names(first: 1) { edges { node { firstName lastName fullName } } }
                } } }
              } } }
            } } }
          } } }
        } } }
      } } }
    }
  }
}
```

See `examples/kyb/02_officers_lookup.md`.

### KYB: full verification (TINs, watchlists, bankruptcies, registrations)

```graphql
query KYBVerify($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on LegalEntity {
      names(first: 1) { edges { node { name } } }
      tins(first: 5) { edges { node { tin tinType validity } } }
      isFlaggedByWatchlistEntries(first: 5) { edges { node { watchlistName } } }
      bankruptcies(first: 5) { edges { node { caseNumber filingDate chapterType } } }
      registeredEntities(first: 5) { edges { node {
        formationYear formationDate
        registrations(first: 5) { edges { node {
          status registrationType registrationState jurisdictionType registeredName fileNumber
        } } }
      } } }
    }
  }
}
```

Field reality (do not guess): `Tin.validity` (not `tinStatus`); `Registration.status` (not `registrationStatus`); jurisdiction is `registrationState` / `jurisdictionType` / `homeJurisdictionState` (no field literally called `jurisdiction`); `WatchlistEntry.watchlistName` only (no `entityName`); `RegisteredEntity` has **both** `formationYear` (Int) and `formationDate` (Date). See `examples/kyb/10_kyb_verify.md`.

### Person search: a person's companies

```graphql
query PersonCompanies($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Person {
      names(first: 1) { edges { node { firstName lastName fullName } } }
      legalEntities(first: 10) { edges { node {
        names(first: 1) { edges { node { name } } }
        roles(first: 5) { edges { node {
          jobTitle managementLevel
          registrations(first: 3) { edges { node {
            registeredEntities(first: 3) { edges { node { name formationYear } } }
          } } }
        } } }
      } } }
    }
  }
}
```

```json
{ "searchInput": { "person": { "firstName": "Daniel", "lastName": "Ek" }, "entityType": "PERSON" } }
```

See `examples/person_search/04_find_person_companies.md`.

### Revenue: brand-level card transactions

`cardTransactions` is a connection; pass its filter as a `ConnectionConditions` variable.

```graphql
query BrandRevenue($searchInput: SearchInput!, $txnConditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      names(first: 1) { edges { node { name } } }
      cardTransactions(first: 12, conditions: $txnConditions) {
        edges { node { projectedQuantity quantityType period periodEndDate } }
      }
    }
  }
}
```

```json
{ "txnConditions": { "filter": { "AND": [
  { "EQ": ["period", "12m"] },
  { "EQ": ["quantityType", "card_revenue_amount"] },
  { "IS_NULL": ["platformBrandId"] }
] } } }
```

**MANDATORY at brand level**: `{ "IS_NULL": ["platformBrandId"] }`. Without it revenue is 2–5× inflated (aggregate + per-platform rows summed). Records come back in `periodEndDate`-descending order — `first: 1` = latest, `first: 12` = last 12 periods. `BrandCardTransaction` exposes `projectedQuantity` (no `rawQuantity`). See `examples/revenue/06_brand_revenue.md` and `references/card_transactions.md`.

### Revenue: per-location (OPERATING_LOCATION)

Same query against `... on OperatingLocation`, searched with a street `address`. **Do not** filter `platformBrandId` here (it doesn't exist on OL transactions). OL transactions expose both `rawQuantity` and `projectedQuantity`. `period` `"1m"`/`"3m"`/`"12m"` all valid for trends.

> A name+address `OPERATING_LOCATION` search can still return **several candidate nodes** — match the one whose `addresses` equals the address you searched before reading its transactions.

### Locations: filter a brand's locations by state/city

Search `BRAND` by name, filter the `operatingLocations` connection (`ConnectionConditions` — paths relative to the OL node):

```graphql
query BrandLocations($searchInput: SearchInput!, $locConditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      names(first: 1) { edges { node { name } } }
      operatingLocations(first: 100, conditions: $locConditions) {
        edges { node {
          names(first: 1) { edges { node { name } } }
          addresses(first: 1) { edges { node { streetAddress1 city state zip } } }
          phoneNumbers(first: 1) { edges { node { phoneNumber } } }
          operatingStatuses(first: 1) { edges { node { operatingStatus } } }
        } }
      }
    }
  }
}
```

```json
{ "locConditions": { "filter": { "EQ": ["addresses.state", "NY"] } } }
```

See `examples/locations/05_brand_locations_by_state.md`.

## Aggregate Queries (Counts)

`aggregate` returns counts without paginating. Important constraints (all verified):

- **`entityType` must be `OPERATING_LOCATION`.** Any other value → 400 `Entity type must be OPERATING_LOCATION`.
- **Count fields** (singular): `count(field: "brand" | "operatingLocation" | "legalEntity")`. Multiple aliases per query OK.
- **For accurate counts, use `conditions.filter` and NO `prompt`.** Filter paths are OL-relative (`addresses.state`, `addresses.zip`, `brands.industries.industryCode` + `brands.industries.industryType`).
- **`prompt`-based aggregate caps at 500** (semantic candidate limit) and `count(field:"brand")` + `prompt` → 400. So don't use `prompt` for counts — use a NAICS/geography filter.
- **`name` is ignored** by aggregate (it counts the whole corpus). Use filters, not names.

```graphql
query Counts($searchInput: SearchInput!) {
  aggregate(searchInput: $searchInput) {
    brands: count(field: "brand")
    locations: count(field: "operatingLocation")
    legalEntities: count(field: "legalEntity")
  }
}
```

```json
{ "searchInput": { "entityType": "OPERATING_LOCATION",
  "conditions": { "filter": { "AND": [
    { "EQ": ["addresses.state", "RI"] },
    { "EQ": ["brands.industries.industryCode", "722515"] },
    { "EQ": ["brands.industries.industryType", "naics_2022_code"] }
  ] } } } }
```

## Node-Level Aggregators

Every node (`Brand`, `OperatingLocation`, `LegalEntity`, `Person`, `Address`) exposes `count`, `countDistinct`, `has`, `sum`, `min`, `max`, `avg`, `minDateTime`, `maxDateTime`, each `(field: String!, conditions: Conditions)`. These compute **within a resolved entity** and are **uncapped** — use them for per-entity rollups (e.g. "how many NY locations does Starbucks have?").

```graphql
... on Brand {
  names(first: 1) { edges { node { name } } }
  totalLocations: count(field: "operatingLocations")
  nyLocations:    count(field: "operatingLocations",
    conditions: { filter: { EQ: ["operatingLocations.addresses.state", "NY"] } })
  hasNY: has(field: "operatingLocations",
    conditions: { filter: { EQ: ["operatingLocations.addresses.state", "NY"] } })
}
```

Note: node-level aggregator `field` paths are **plural connection names** and full-path filters (`operatingLocations.addresses.state`). `collect()` is **not** supported on a normal query (only with `output.file`) → 400; avoid it.

## Export (Large Result Sets)

Set `output: { filename: "..." }` on the `searchInput` to trigger a background S3 export. **Use `entityType: OPERATING_LOCATION`** (BRAND + output → 400). `prompt` is allowed here. The data response is `null`; the signed URL is in `extensions.backgroundTasks[0].result[0]`.

```json
{ "searchInput": { "prompt": "nail salon", "entityType": "OPERATING_LOCATION",
  "conditions": { "filter": { "EQ": ["addresses.state", "RI"] } },
  "output": { "filename": "nail_ri" } } }
```

```json
{ "extensions": { "backgroundTasks": [ { "id": "uuid", "status": "SUCCESS",
  "result": ["https://...s3.amazonaws.com/...signed-url..."] } ] }, "data": { "search": null } }
```

Download with `urllib.request.urlretrieve(url, "out.json")`. Signed URL valid ~6 days. See `examples/export/08_segment_export.md`.

## Advanced: `@coalesce` + `@skip`

`alias: _fn @coalesce(refs: [...])` returns the first non-null value across traversal paths. Rules (live-verified):
- The field **must be aliased**.
- Each ref uses the **full Relay path including `edges.0.node.` segments** — e.g. `legalEntities.edges.0.node.tins.edges.0.node.tin`. List multiple refs (whitespace-separated) to fall through in order.
- Every referenced path **must also be declared** in the query body — hide it with `@skip(if: true)`. `conditions`/`orderBy` on those backing fields *do* affect what `@coalesce` resolves.

```graphql
... on OperatingLocation {
  names(first: 1) { edges { node { name } } }
  EIN: _fn @coalesce(refs: [
    "legalEntities.edges.0.node.tins.edges.0.node.tin"
    "brands.edges.0.node.legalEntities.edges.0.node.tins.edges.0.node.tin"
  ])
  legalEntities(first: 1, conditions: { filter: { HAS: ["tins"] } }) @skip(if: true) {
    edges { node { tins(first: 1) { edges { node { tin } } } } }
  }
  brands(first: 1) @skip(if: true) {
    edges { node { legalEntities(first: 1, conditions: { filter: { HAS: ["tins"] } }) {
      edges { node { tins(first: 1) { edges { node { tin } } } } } } } }
}
```

See `examples/derived/07_coalesce_ein_formation.md`.

## Introspection (default verification step)

Before trusting any field name not shown above, introspect the type. Treat the tables here as **common fields, not exhaustive**.

```bash
python3 << 'PYEOF'
import json, urllib.request, os
query = '{ __type(name: "TYPE_NAME") { fields { name type { name kind ofType { name kind } } } } }'
req = urllib.request.Request('https://api.enigma.com/graphql',
    data=json.dumps({'query': query}).encode(),
    headers={'content-type': 'application/json', 'x-api-key': os.environ['ENIGMA_API_KEY']})
for f in json.loads(urllib.request.urlopen(req).read())['data']['__type']['fields']:
    print(f"{f['name']}: {f['type']['name'] or f['type']['kind']}")
PYEOF
```

## Field Name Corrections

Non-intuitive but verified field names:

- Output address fields: `streetAddress1` / `streetAddress2` / `zip` (NOT `street1`/`postalCode` — those are input-only).
- `OperatingLocationOperatingStatus.operatingStatus` (NOT `status`)
- `Website.website` (NOT `url`)
- `Industry.industryDesc` (NOT `description`)
- `Role.jobTitle` (NOT `title`); `Role` has no `names`/`roleType`
- `BrandCardTransaction.projectedQuantity` (NOT `amount`); no `rawQuantity` at brand level
- `ReviewSummary.reviewScoreAvg` (NOT `averageRating`)
- `Tin.validity` (NOT `tinStatus`)
- `Registration.status` (NOT `registrationStatus`); `registrationState`/`jurisdictionType` (NOT `jurisdiction`)
- `WatchlistEntry.watchlistName` (NOT `entityName`/`listName`)
- `RegisteredEntity`: both `formationYear` (Int) and `formationDate` (Date)

See `references/field_corrections.json`.

## Workflow

```
- [ ] 1. Search mode: name vs prompt (prompt ⇒ entityType BRAND on a search)
- [ ] 2. Entity type via the decision matrix
- [ ] 3. Build query using Rule 1 (union/inline fragments) + Rule 2 (Relay connections)
- [ ] 4. Pick the right conditions type: Conditions (searchInput / aggregators) vs ConnectionConditions (connection args)
- [ ] 5. Card transactions? brand ⇒ IS_NULL platformBrandId; OL ⇒ omit it
- [ ] 6. Check ENIGMA_API_KEY, execute via the heredoc template (NEVER curl)
- [ ] 7. Inspect data['errors'] / HTTP status before formatting
- [ ] 8. Format: tables for lists, structured summary for singles; skip null fields
- [ ] 9. Paginate via pageInfo if needed (max 3 pages)
```

## Formatting & Error Handling

- **Lists** → markdown table, "Found X results." **Single entity** → labeled summary. **Empty** → suggest a different entity type or `prompt` discovery. **Paginated** → "Showing X; want more?"

| Error | Cause | Fix |
|---|---|---|
| `Cannot query field 'edges' on type 'SearchUnion'` | `edges/node` on `search` | Use `__typename ... on Brand {}` (Rule 1) |
| `Cannot query field 'X' on type '...Connection'` | plain field on a connection | Wrap in `(first:N){edges{node{...}}}` (Rule 2) |
| `Variable ... of type Conditions ... expected ConnectionConditions` | wrong conditions type | Connection args use `ConnectionConditions` |
| `Use entity type BRAND instead` | `prompt` + OL on `search` | Use BRAND for prompt search |
| `Entity type must be OPERATING_LOCATION` | aggregate with wrong entityType | Set `entityType: OPERATING_LOCATION` |
| `Operator 'getitem' is not supported` | `count(field:"brand")` + prompt, or BRAND export | Use filter (not prompt) for counts; OL for export |
| HTTP 400 on `totalCount` | unsupported | Use `aggregate`/node `count` or `pageInfo.hasNextPage` |
| HTTP 401 | bad/missing key | Check `ENIGMA_API_KEY` |
| Empty OL results | missing `street1` | Include `address.street1` |

## Examples by Use Case

| Use Case | Example File |
|---|---|
| Discovery by type/industry (BRAND + prompt) | `examples/discovery/01_coffee_shops_zip.md` |
| List/count locations by industry (export / aggregate) | `examples/discovery/11_ol_industry_discovery.md` |
| Brand profile, marketing, locations | `examples/brand/03_brand_profile.md` |
| Comprehensive brand data dump | `examples/brand/13_brand_dump.md` |
| Person search, brand contacts | `examples/person_search/04_find_person_companies.md` |
| KYB officers / corporate structure | `examples/kyb/02_officers_lookup.md` |
| KYB full verify (TINs, watchlists, bankruptcies) | `examples/kyb/10_kyb_verify.md` |
| Legal entity profile (formation, registration) | `examples/legal_entity/09_legal_entity_profile.md` |
| Brand locations by state/city | `examples/locations/05_brand_locations_by_state.md` |
| Revenue (brand, OL, per-location, time series) | `examples/revenue/06_brand_revenue.md` |
| Risk signals (revenue quality, status) | `examples/risk/12_risk_signals.md` |
| EIN/TIN, formation year, `@coalesce` | `examples/derived/07_coalesce_ein_formation.md` |
| Bulk export to S3 | `examples/export/08_segment_export.md` |

## Additional Resources

- `references/filter_syntax.md` — filter operators and examples
- `references/field_corrections.json` — verified field names
- `references/naics_2022_mapping.json` — industry code mappings
- `references/pagination_template.py` — pagination implementation
- `references/card_transactions.md` — quantityType values, brand vs OL differences
- `scripts/validate_query.py` — static linter for the two shape rules + field names
