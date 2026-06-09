# Discovery: Find Locations by Industry (the correct patterns)

## User Intent

Find business locations of a specific industry in a city/state — either a usable list of locations, or a count.

## ⚠️ The old approach is now invalid

`prompt` + `entityType: OPERATING_LOCATION` on `search` **400s** ("Use entity type BRAND instead"). `prompt` on a regular `search` requires `entityType: BRAND`. Use one of the three verified patterns below instead.

| Pattern | Use when you want | entityType |
|---|---|---|
| (a) BRAND + prompt, traverse `operatingLocations` | An inline list of locations with brand context | `BRAND` |
| (b) `aggregate` + `conditions.filter` | A real, uncapped **count** of locations/brands | `OPERATING_LOCATION` |
| (c) Export with `output.filename` | A raw bulk list of locations (S3 file) | `OPERATING_LOCATION` |

Key shape rules: `search` returns `[SearchUnion]` — select with `__typename` + inline fragments, never `edges { node }` on `search` itself. Every nested field is a Relay connection (`field(first: N) { edges { node { ... } } }`). `SearchInput.conditions` is type `Conditions` (supports `limit`); nested-connection `conditions` is type `ConnectionConditions` (filter/orderBy only).

---

## (a) BRAND + prompt, then traverse `operatingLocations`

Semantic industry discovery interprets the `prompt`, then filters the brand's locations by geography. The `SearchInput.conditions.filter` uses `operatingLocations.`-prefixed paths; the nested `operatingLocations(conditions:)` uses location-relative paths (`addresses.state`).

```graphql
query NailSalons($searchInput: SearchInput!, $locConditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      operatingLocations(first: 10, conditions: $locConditions) {
        edges {
          node {
            names(first: 1) { edges { node { name } } }
            addresses(first: 1) { edges { node { fullAddress city state zip } } }
            operatingStatuses(first: 1) { edges { node { operatingStatus } } }
            phoneNumbers(first: 1) { edges { node { phoneNumber } } }
          }
        }
      }
    }
  }
}
```

```json
{
  "searchInput": {
    "prompt": "nail salon",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "EQ": ["operatingLocations.addresses.state", "CO"] },
          { "EQ": ["operatingLocations.addresses.city", "DENVER"] }
        ]
      },
      "limit": 15
    }
  },
  "locConditions": {
    "filter": {
      "AND": [
        { "EQ": ["addresses.state", "CO"] },
        { "EQ": ["addresses.city", "DENVER"] }
      ]
    }
  }
}
```

---

## (b) Counts with `aggregate` (real, uncapped)

For "how many", use `aggregate` with `entityType: OPERATING_LOCATION` and a pure `conditions.filter`. Use OL-relative paths: `addresses.state`, `addresses.zip`, and `brands.industries.industryCode` / `industryType` / `industryDesc`. `count(field: ...)` accepts `"operatingLocation"`, `"brand"`, or `"legalEntity"` and you can alias multiple counts.

> Do NOT use `prompt` for counts — prompt-based aggregate caps at 500, and `count(field:"brand")` + `prompt` → 400. Pure `conditions.filter` returns the real number.

```graphql
query Counts($searchInput: SearchInput!) {
  aggregate(searchInput: $searchInput) {
    locations: count(field: "operatingLocation")
    brands: count(field: "brand")
  }
}
```

```json
{
  "searchInput": {
    "entityType": "OPERATING_LOCATION",
    "conditions": {
      "filter": {
        "AND": [
          { "EQ": ["brands.industries.industryType", "enigma_industry_description"] },
          { "IN": ["brands.industries.industryDesc", ["nail salon"]] },
          { "IN": ["addresses.state", ["CO"]] }
        ]
      }
    }
  }
}
```

Example response: `{ "data": { "aggregate": { "locations": 1923, "brands": 1752 } } }`.

Filter by industry code instead of description:

```json
{ "AND": [
  { "EQ": ["brands.industries.industryType", "naics_2022_code"] },
  { "IN": ["brands.industries.industryCode", ["812113"]] },
  { "IN": ["addresses.state", ["CO"]] }
] }
```

---

## (c) Export a raw location list with `output.filename`

For a full, bulk list of locations (not just a page), add `output: { filename }` to an `OPERATING_LOCATION` search. The response returns `data.search: null` and the file URL arrives in `extensions.backgroundTasks[0].result[0]` (a signed S3 URL). `entityType: BRAND` + `output` → 400.

```graphql
query ExportLocations($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on OperatingLocation {
      names(first: 1) { edges { node { name } } }
      addresses(first: 1) { edges { node { fullAddress } } }
    }
  }
}
```

```json
{
  "searchInput": {
    "entityType": "OPERATING_LOCATION",
    "output": { "filename": "nail_salons_denver_co" },
    "conditions": {
      "limit": 50,
      "filter": {
        "AND": [
          { "EQ": ["brands.industries.industryType", "enigma_industry_description"] },
          { "IN": ["brands.industries.industryDesc", ["nail salon"]] },
          { "IN": ["addresses.state", ["CO"]] },
          { "IN": ["addresses.city", ["DENVER"]] },
          { "IN": ["operatingStatuses.operatingStatus", ["Open"]] }
        ]
      }
    }
  }
}
```

**Response shape (export):**
```json
{
  "data": { "search": null },
  "extensions": {
    "backgroundTasks": [
      { "status": "SUCCESS", "result": ["https://...signed-s3-url..."] }
    ]
  }
}
```
Download the result file from the S3 URL.

---

## Common Mistakes to Avoid

1. ❌ **`prompt` + `OPERATING_LOCATION`** on `search` → 400. `prompt` requires `entityType: BRAND`. For OL-typed results use a `conditions.filter` (no prompt), as in (b)/(c).
2. ❌ **Using `prompt` for counts** — caps at 500, and `count(field:"brand")` + `prompt` → 400. Use pure `conditions.filter` in `aggregate`.
3. ❌ **`entityType: BRAND` with `output`** → 400. Export requires `OPERATING_LOCATION`.
4. ❌ **Forgetting `industryType`** — always pair `industryDesc` with `industryType: "enigma_industry_description"` (or pair `industryCode` with the matching code type).
5. ❌ **Lowercase city names** — cities must be UPPERCASE (`"DENVER"`, not `"Denver"`).

---

## Python Execution Template (count + export)

```bash
python3 << 'PYEOF'
import json, urllib.request, os

def run(query, variables):
    payload = json.dumps({'query': query, 'variables': variables})
    req = urllib.request.Request(
        'https://api.enigma.com/graphql',
        data=payload.encode(),
        headers={'content-type': 'application/json', 'x-api-key': os.environ['ENIGMA_API_KEY']}
    )
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {'http_error': e.code, 'body': e.read().decode()}

count_q = '''query Counts($searchInput: SearchInput!) {
  aggregate(searchInput: $searchInput) {
    locations: count(field: "operatingLocation")
    brands: count(field: "brand")
  }
}'''
count_v = {"searchInput": {"entityType": "OPERATING_LOCATION", "conditions": {"filter": {"AND": [
    {"EQ": ["brands.industries.industryType", "enigma_industry_description"]},
    {"IN": ["brands.industries.industryDesc", ["nail salon"]]},
    {"IN": ["addresses.state", ["CO"]]}
]}}}}

data = run(count_q, count_v)
if 'errors' in data:
    print('GraphQL Error:', data['errors'])
else:
    print('Counts:', data['data']['aggregate'])
PYEOF
```
