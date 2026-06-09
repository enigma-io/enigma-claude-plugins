# Location Lookup Examples

## User Intent

Find a brand's locations filtered by geography (e.g., "every open Chipotle in Washington"), or look up a single operating location by name and address.

## Key Concepts

- `search` returns `[SearchUnion]` — match with `... on Brand` / `... on OperatingLocation` (never `edges { node }` on `search` itself)
- Every nested field is a Relay connection — always `(first: N) { edges { node { ... } } }`
- Filter a brand's `operatingLocations` with `ConnectionConditions` ({ filter, orderBy }) on OL-relative paths like `addresses.state`
- Address OUTPUT fields are `streetAddress1`, `city`, `state`, `zip`, `fullAddress` (`street1` is INPUT-only, on `AddressInput`)
- OPERATING_LOCATION searches take an `address` with `street1` for reliable results
- `@coalesce` can resolve a legal name from multiple traversal paths

---

## Brand Locations Filtered by State

Find a brand by name, then page its operating locations filtered by state. `count(field: "operatingLocations", ...)` returns an uncapped total for the same filter.

```graphql
query BrandLocationsByState($searchInput: SearchInput!, $locConditions: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      totalInState: count(field: "operatingLocations", conditions: { filter: { EQ: ["addresses.state", "WA"] } })
      operatingLocations(first: 5, conditions: $locConditions) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            names(first: 1) { edges { node { name } } }
            addresses(first: 1) { edges { node { streetAddress1 city state zip fullAddress } } }
            operatingStatuses(first: 1) { edges { node { operatingStatus } } }
          }
        }
      }
    }
  }
}
```

```json
{
  "searchInput": { "name": "Chipotle", "entityType": "BRAND", "conditions": { "limit": 1 } },
  "locConditions": { "filter": { "AND": [{ "EQ": ["addresses.state", "WA"] }, { "EQ": ["operatingStatuses.operatingStatus", "Open"] }] } }
}
```

Live result (Chipotle Mexican Grill): `count(operatingLocations in WA)` = `86`; first WA location `1827 15TH AVE W SEATTLE WA 98119`. Page with `pageInfo.endCursor` for the rest.

> The `$locConditions` variable is type `ConnectionConditions` (filter / orderBy only — NO limit). The `conditions` on `count(...)` is a node-aggregator `Conditions`.

---

## Operating Location Full Profile

Look up one location and pull its profile, dual revenue (per-store vs entire chain), and a coalesced legal name.

```graphql
query LocationProfile($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      locationName: names(first: 1) { edges { node { name } } }
      brandNames: brands(first: 1) {
        edges { node { names(first: 1) { edges { node { name } } } } }
      }
      locationAddress: addresses(first: 1) { edges { node { streetAddress1 city state zip fullAddress } } }
      legalName: _fn @coalesce(refs: [
        "legalEntities.edges.0.node.registeredEntities.edges.0.node.name"
        "brands.edges.0.node.legalEntities.edges.0.node.registeredEntities.edges.0.node.name"
      ])
      legalEntities(first: 1) @skip(if: true) {
        edges { node { registeredEntities(first: 1) { edges { node { name } } } } }
      }
      brands(first: 1) @skip(if: true) {
        edges { node { legalEntities(first: 1) { edges { node {
          registeredEntities(first: 1) { edges { node { name } } }
        } } } } }
      }
      locationCardRevenueAmount: cardTransactions(first: 1, conditions: {
        filter: { AND: [
          { EQ: ["period", "12m"] }
          { EQ: ["quantityType", "card_revenue_amount"] }
        ]}
      }) {
        edges { node { projectedQuantity rawQuantity periodEndDate } }
      }
      brandCardRevenueAmount: brands(first: 1) {
        edges { node {
          cardTransactions(first: 1, conditions: {
            filter: { AND: [
              { EQ: ["period", "12m"] }
              { EQ: ["quantityType", "card_revenue_amount"] }
              { IS_NULL: ["platformBrandId"] }
            ]}
          }) {
            edges { node { projectedQuantity periodEndDate } }
          }
        } }
      }
      locationOperatingStatus: operatingStatuses(first: 1) {
        edges { node { operatingStatus lastObservedDate } }
      }
      locationWebsites: websites(first: 1) { edges { node { website } } }
      locationPhones: phoneNumbers(first: 1) { edges { node { phoneNumber } } }
    }
  }
}
```

```json
{
  "searchInput": {
    "conditions": { "limit": 1 },
    "entityType": "OPERATING_LOCATION",
    "name": "D & D DRYWALL",
    "address": { "street1": "2071 WOOD RD", "city": "FULTON", "state": "CA" }
  }
}
```

Live result: `legalName` resolves to `D&D DRYWALL INC.` via the brand's legal entity (the location's own `legalEntities` is empty, so `@coalesce` falls through to the second ref).

> `@coalesce` ref paths use the FULL Relay form including `edges.0.node.` segments (e.g. `brands.edges.0.node.legalEntities.edges.0.node.registeredEntities.edges.0.node.name`), and each backing path is declared in the query with `@skip(if: true)` so it traverses without cluttering the response. Note: the OL-level `cardTransactions` exposes both `projectedQuantity` and `rawQuantity` and takes NO `platformBrandId`, while the brand-level one is `projectedQuantity` only and REQUIRES `IS_NULL: ["platformBrandId"]`.

---

## Simple Location Check

```graphql
query LocationCheck($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      id
      names(first: 1) { edges { node { name } } }
      addresses(first: 1) { edges { node { fullAddress } } }
      phoneNumbers(first: 1) { edges { node { phoneNumber } } }
      operatingStatuses(first: 1) { edges { node { operatingStatus } } }
      locationTypes(first: 3) { edges { node { locationType } } }
      reviewSummaries(first: 1) { edges { node { reviewScoreAvg reviewCount firstReviewDate lastReviewDate } } }
    }
  }
}
```

```json
{
  "searchInput": {
    "name": "Walmart",
    "entityType": "OPERATING_LOCATION",
    "address": { "street1": "406 S Walton Blvd", "city": "Bentonville", "state": "AR" }
  }
}
```

Live result: Walmart Supercenter, `406 S WALTON BLVD BENTONVILLE AR 72712`, status `Open`, `reviewScoreAvg` "4.10".

---

## Common Mistakes to Avoid

1. **Searching `OPERATING_LOCATION` by brand name without `address`** — returns empty; include `street1`
2. **Using `street1` as an OUTPUT field** — outputs are `streetAddress1` / `fullAddress`; `street1` is INPUT-only (`AddressInput`)
3. **Putting `limit` in a `ConnectionConditions`** — connection conditions are filter / orderBy only
4. **Using `platformBrandId` filter on OL card transactions** — that field is Brand-level only
5. **Using `postalCode` in filters** — the correct field is `zip`
